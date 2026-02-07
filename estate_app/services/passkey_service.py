import json
import uuid
from base64 import b64decode, urlsafe_b64decode

import jwt
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers.structs import (
    AuthenticationCredential,
    AuthenticatorSelectionCriteria,
    RegistrationCredential,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from core.base_code import base64url_encode
from core.breaker import breaker
from core.cache import Cache
from core.check_permission import CheckRolePermission
from core.mapper import ORMMapper
from core.paginate import PaginatePage
from core.settings import settings
from repos.auth_repo import AuthRepo
from repos.passkey_repo import PasskeyRepo
from schemas.schema import CredentialAttestationOut

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_EXPIRE_MINUTES = settings.ACCESS_EXPIRE_MINUTES
REFRESH_EXPIRE_DAYS = settings.REFRESH_EXPIRE_DAYS
SECURE_COOKIES = settings.SECURE_COOKIES
access_exp = settings.access_key_jwt_expiration
refresh_exp = settings.refresh_expiration_jwt_expiration


class PasskeyService:
    def __init__(self, db):
        self.repo = PasskeyRepo(db)
        self.auth_repo: AuthRepo = AuthRepo(db)
        self.mapper: ORMMapper = ORMMapper()
        self.cache: Cache = Cache()
        self.paginate: PaginatePage = PaginatePage()
        self.permission: CheckRolePermission = CheckRolePermission()

    async def complete_passkey_registration(
        self, registration_response: dict, current_user
    ):
        async def handler():
            user_id = current_user.id

            credential = RegistrationCredential(**registration_response)

            client_data_json = credential.response.client_data_json
            client_data = json.loads(urlsafe_b64decode(client_data_json))

            if client_data.get("type") != "webauthn.create":
                raise HTTPException(400, "Invalid client data type")

            received_challenge_b64 = client_data.get("challenge")
            if not received_challenge_b64:
                raise HTTPException(400, "Missing challenge")

            challenge_key = f"webauthn:register:challenge:{received_challenge_b64}"
            expected_challenge_bytes = await self.cache.get_raw(challenge_key)
            if not expected_challenge_bytes:
                raise HTTPException(400, "Invalid, expired, or replayed challenge")

            # Delete challenge to prevent replay
            await self.cache.delete_raw(challenge_key)

            try:
                verification = verify_registration_response(
                    credential=credential,
                    expected_challenge=expected_challenge_bytes,
                    expected_origin=settings.WEBAUTHN_ORIGIN,
                    expected_rp_id=settings.RP_ID,
                    require_user_verification=True,  # Enforces biometric/PIN
                )
            except Exception as exc:
                raise HTTPException(401, "Registration verification failed") from exc

            credential_id = verification.credential_id
            public_key = verification.credential_public_key
            sign_count = verification.sign_count
            device_fingerprint = registration_response.get("device_fingerprint")

            if device_fingerprint:
                try:
                    b64decode(device_fingerprint)
                except Exception:
                    raise HTTPException(400, "Invalid device fingerprint format")

            existing_device = await self.repo.get_device_fingerprint(
                user_id=user_id,
                device_fingerprint=device_fingerprint,
            )
            if existing_device:
                raise HTTPException(400, "A passkey already exists for this device")
            existing_cred = await self.repo.get_credential_id(
                credential_id=credential_id, user_id=user_id
            )
            if existing_cred:
                raise HTTPException(400, "This credential is already registered")

            existing_pubkey = await self.repo.get_public_key(
                user_id=user_id, public_key=public_key
            )
            if existing_pubkey:
                raise HTTPException(400, "This public key is already registered")

            passkey = await self.repo.create_passkey(
                credential_id=credential_id,
                public_key=public_key,
                user_id=user_id,
                sign_count=sign_count,
                device_fingerprint=device_fingerprint,
            )

            await self.cache.delete_cache_keys_async(
                f"passkey::{user_id}:{passkey.id}", f"passkey::{user_id}"
            )

            return JSONResponse(
                {"message": "Passkey registration successful"}, status_code=201
            )

        return await breaker.call(handler)

    async def start_passkey_registration(self, current_user):
        async def handler():
            await self.permission.check_authenticated(current_user=current_user)
            options = generate_registration_options(
                rp_id=settings.RP_ID,
                rp_name=settings.PROJECT_NAME,
                user_id=str(current_user.id).encode(),
                user_name=current_user.username,
                authenticator_selection=AuthenticatorSelectionCriteria(
                    resident_key=ResidentKeyRequirement.REQUIRED,
                    user_verification=UserVerificationRequirement.REQUIRED,
                ),
                timeout=60000,
            )

            encoded_challenge = base64url_encode(options.challenge)
            challenge_key = f"webauthn:register:challenge:{encoded_challenge}"

            await self.cache.set_raw(
                challenge_key,
                options.challenge,
                ttl=300,
            )

            return {
                "publicKey": {
                    "challenge": encoded_challenge,
                    "rp": {
                        "id": options.rp.id,
                        "name": options.rp.name,
                    },
                    "user": {
                        "id": base64url_encode(options.user.id),
                        "name": options.user.name,
                        "displayName": options.user.display_name or options.user.name,
                    },
                    "pubKeyCredParams": [
                        {"type": "public-key", "alg": -7},
                        {"type": "public-key", "alg": -8},
                        {"type": "public-key", "alg": -257},
                    ],
                    "timeout": options.timeout,
                    "authenticatorSelection": {
                        "residentKey": "required",
                        "requireResidentKey": True,
                        "userVerification": "required",
                    },
                    "attestation": "direct",
                }
            }

        return await breaker.call(handler)

    async def get_registered_passkeys(self, current_user):
        async def handler():
            user_id = current_user.id
            await self.permission.check_authenticated(current_user=current_user)
            credentials = await self.repo.get_registered_passkeys(user_id=user_id)
            return [
                {
                    "id": cred.id,
                    "label": "Device 1",
                    # "created_at": cred.created_at,
                }
                for cred in credentials
            ]

        return await breaker.call(handler)

    async def start_passkey_login(self):
        async def handler():
            options = generate_authentication_options(
                rp_id=settings.RP_ID,
                timeout=60000,
                user_verification=UserVerificationRequirement.REQUIRED,
            )
            encoded_challenge = base64url_encode(options.challenge)
            challenge_key = f"webauthn:login:challenge:{encoded_challenge}"

            await self.cache.set_raw(
                challenge_key,
                options.challenge,
                ttl=300,
            )

            return {
                "publicKey": {
                    "challenge": base64url_encode(options.challenge),
                    "rpId": options.rp_id,
                    "timeout": options.timeout,
                    "userVerification": options.user_verification,
                },
            }

        return await breaker.call(handler)

    async def verify_passkey_login(self, assertion: dict):
        async def handler():
            credential = AuthenticationCredential(**assertion)
            if not credential:
                raise HTTPException(400, "Invalid assertion payload")
            user_handle = credential.response.user_handle
            if not user_handle:
                raise HTTPException(400, "User handle required")
            user_id = uuid.UUID(urlsafe_b64decode(user_handle).decode())
            if not user_id:
                raise HTTPException(400, "Invalid User")
            db_credential = await self.repo.get_credential_id(
                credential_id=credential.raw_id, user_id=user_id
            )
            if not db_credential or db_credential.user_id != user_id:
                raise HTTPException(
                    404, "Credential not found or Credential/User Mismatch"
                )

            client_data = json.loads(
                urlsafe_b64decode(credential.response.client_data_json)
            )
            if client_data.get("type") != "webauthn.get":
                raise HTTPException(400, "Invalid client data type")
            challenge_key = f"webauthn:login:challenge:{client_data['challenge']}"
            expected_challenge = await self.cache.get_raw(challenge_key)
            if not expected_challenge:
                raise HTTPException(400, "Challenge expired")
            try:
                verification = verify_authentication_response(
                    credential=credential,
                    expected_challenge=expected_challenge,
                    expected_rp_id=settings.RP_ID,
                    expected_origin=settings.WEBAUTHN_ORIGIN,
                    credential_public_key=db_credential.public_key,
                    credential_current_sign_count=db_credential.sign_count or 0,
                    require_user_verification=True,
                )
            except Exception:
                raise HTTPException(401, "Authentication failed")

            await self.repo.update_sign_count(
                credential_id=db_credential.id,
                new_sign_count=verification.new_sign_count,
            )

            user = await self.repo.get_user_passkey_by_id(user_id)
            if not user:
                raise HTTPException(404, "User not found")

            access_token = jwt.encode(
                {"sub": str(user.id), "type": "access", "exp": access_exp},
                SECRET_KEY,
                algorithm=ALGORITHM,
            )

            refresh_token = jwt.encode(
                {"sub": str(user.id), "type": "refresh", "exp": refresh_exp},
                SECRET_KEY,
                algorithm=ALGORITHM,
            )

            response = JSONResponse(
                {
                    "message": "Login successful",
                    "id": user.id,
                    "username": user.username,
                    "role": user.role.name,
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                }
            )
            await self.cache.delete_raw(challenge_key)

            response.set_cookie(
                "access_token",
                access_token,
                httponly=True,
                secure=SECURE_COOKIES,
                samesite="lax",
                max_age=ACCESS_EXPIRE_MINUTES * 60,
            )

            response.set_cookie(
                "refresh_token",
                refresh_token,
                httponly=True,
                secure=SECURE_COOKIES,
                samesite="lax",
                max_age=REFRESH_EXPIRE_DAYS * 86400,
            )

            return response

        return await breaker.call(handler)

    async def delete(self, current_user, passkey_id: uuid.UUID):
        async def handler():
            user_id = current_user.id
            await self.permission.check_authenticated(current_user=current_user)
            passkey = await self.repo.get_passkey_by_id_for_user(
                user_id=user_id, passkey_id=passkey_id
            )
            if not passkey:
                raise HTTPException(
                    status_code=404,
                    detail="Passkey not found for this user",
                )
            await self.repo.delete_passkey_by_id(user_id=user_id, passkey_id=passkey_id)
            await self.cache.delete_cache_keys_async(
                f"passkey::{user_id}:{passkey_id}", f"passkey::{user_id}"
            )
            return {"message": "Deleted"}

        return await breaker.call(handler)

    async def get_passkey_by_id(self, current_user, passkey_id: uuid.UUID):
        async def handler():
            await self.permission.check_authenticated(current_user=current_user)
            cache_key = f"passkey::{current_user.id}:{passkey_id}"
            cached = await self.cache.get_json(cache_key)
            if cached is not None:
                return self.mapper.one(item=cached, schema=CredentialAttestationOut)
            passkey = await self.repo.get_passkey_by_id_for_user(
                user_id=current_user.id, passkey_id=passkey_id
            )
            if not passkey:
                raise HTTPException(
                    status_code=404,
                    detail="Passkey not found for this user",
                )
            passkey_dict = self.mapper.one(passkey, CredentialAttestationOut)
            await self.cache.set_json(
                cache_key,
                self.paginate.get_single_json_dumps(prop_dict=passkey_dict),
                ttl=300,
            )
            return passkey_dict

        return await breaker.call(handler)

    async def get_passkeys(self, current_user, page: int = 1, per_page: int = 20):
        async def handler():
            await self.permission.check_authenticated(current_user=current_user)
            cache_key = f"passkey::{current_user.id}:page:{page}:per:{per_page}"
            cached = await self.cache.get_json(cache_key)
            if cached is not None:
                return self.mapper.many(items=cached, schema=CredentialAttestationOut)
            passkey = await self.repo.get_all_passkeys_for_user(user_id=current_user.id)
            if not passkey:
                return []
            passkey_dict = self.mapper.many(passkey, CredentialAttestationOut)
            paginated_props = self.paginate.paginate(passkey_dict, page, per_page)
            await self.cache.set_json(
                cache_key,
                self.paginate.get_list_json_dumps(paginated_props=paginated_props),
                ttl=300,
            )
            return {
                "page": page,
                "per_page": per_page,
                "total": len(passkey),
                "items": paginated_props,
            }

        return await breaker.call(handler)
