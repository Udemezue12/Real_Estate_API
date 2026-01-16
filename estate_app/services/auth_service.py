from datetime import datetime, timedelta, timezone

from core.breaker import breaker
from core.settings import settings
from email_notify.email_service import send_password_reset_link, send_verification_email
from fastapi import BackgroundTasks, HTTPException, Request
from fastapi.responses import JSONResponse
from jose import ExpiredSignatureError, JWTError, jwt
from models.models import User
from repos.auth_repo import AuthRepo
from repos.tenant_repo import TenantRepo
from security.security_generate import user_generate
from security.security_verification import (
    UserVerification,
)
from sms_notify.sms_service import send_sms

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_EXPIRE_MINUTES = settings.ACCESS_EXPIRE_MINUTES
REFRESH_EXPIRE_DAYS = settings.REFRESH_EXPIRE_DAYS
SECURE_COOKIES = settings.SECURE_COOKIES
access_exp = datetime.now(timezone.utc) + timedelta(
    minutes=settings.ACCESS_EXPIRE_MINUTES
)

refresh_exp = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_EXPIRE_DAYS)


class AuthService:
    def __init__(self, db):
        self.repo: AuthRepo = AuthRepo(db)
        self.tenant_repo: TenantRepo = TenantRepo(db)
        self.user_verification: UserVerification = UserVerification(db)

    async def register(self, data, background_tasks: BackgroundTasks):
        async def handler():
            name = f"{data.first_name} {data.middle_name} {data.last_name}"
            if await self.repo.get_by_email(email=data.email):
                raise HTTPException(status_code=400, detail="Email already registered")
            if await self.repo.get_by_username(username=data.username):
                raise HTTPException(status_code=400, detail="Username already taken")
            if await self.repo.find_users_by_name_strict(name=name):
                raise HTTPException(
                    status_code=400, detail="User with the same name already exists"
                )
            if await self.repo.get_by_phoneNumber(phone_number=data.phone_number):
                raise HTTPException(
                    status_code=400, detail="Phone number already taken"
                )
            user = User(
                username=data.username,
                email=data.email.strip().lower(),
                phone_number=data.phone_number,
                first_name=data.first_name,
                middle_name=data.middle_name,
                last_name=data.last_name,
                role=data.role,
                email_verified=False,
            )

            user.set_password(raw_password=data.password)
            await self.repo.create(user)
            tenants = await self.tenant_repo.find_unmatched_by_name(
                data.first_name,
                data.last_name,
                data.middle_name,
            )

            if len(tenants) == 1:
                await self.tenant_repo.attach_user(tenants[0], user)

            otp = await user_generate.generate_otp(user.email)
            token = await user_generate.generate_verify_token(user.email)
            background_tasks.add_task(
                send_verification_email, user.email, otp, token, name
            )
            if hasattr(data, "phone_number") and data.phone_number:
                background_tasks.add_task(
                    send_sms.send_sms, data.phone_number, otp, name
                )

            return JSONResponse(
                {
                    "message": "Registration successful! Please check your email and sms to verify your account."
                },
                status_code=201,
            )

        return await breaker.call(handler)

    async def login(self, data):
        async def handler():
            user = await self.repo.get_by_email(data.email)
            if not user or not user.check_password(raw_password=data.password):
                raise HTTPException(status_code=401, detail="Invalid credentials")

            # if not user.email_verified:
            #     raise HTTPException(
            #         status_code=403,
            #         detail="Email not verified. Please verify your account to login.",
            #     )

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
                    "id": str(user.id),
                    "username": user.username,
                    "role": user.role.name,
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                },
                status_code=200,
            )

            response.set_cookie(
                key="access_token",
                value=access_token,
                httponly=True,
                secure=False,  # localhost only
                samesite="lax",
                max_age=ACCESS_EXPIRE_MINUTES * 60,
            )
            response.set_cookie(
                key="refresh_token",
                value=refresh_token,
                httponly=True,
                secure=False,  # localhost only
                samesite="lax",
                max_age=REFRESH_EXPIRE_DAYS * 86400,
            )
            return response

        return await breaker.call(handler)

    async def logout(self, request: Request):
        async def handler():
            access_token = request.cookies.get("access_token")

            refresh_token = request.cookies.get("refresh_token")
            if access_token:
                await self.repo.blacklist_token(access_token)
            if refresh_token:
                await self.repo.blacklist_token(refresh_token)
            if hasattr(request, "session"):
                request.session.clear()
                request.session["logged_out"] = True
            response = JSONResponse({"message": "Logged out successfully"})
            cookies_to_delete = [
                "access_token",
                "refresh_token",
                "csrf_token",
                "session",
            ]

            for cookie in cookies_to_delete:
                response.delete_cookie(
                    key=cookie,
                    path="/",
                    secure=False,  # localhost only
                    httponly=True,
                    samesite="lax",
                )

            return response

        return await breaker.call(handler)

    async def refresh(self, request: Request):
        async def handler():
            refresh_token = request.cookies.get("refresh_token")
            if not refresh_token:
                raise HTTPException(status_code=401, detail="No refresh token")
            if await self.repo.is_token_blacklisted(refresh_token):
                raise HTTPException(status_code=401, detail="Refresh token revoked")

            try:
                payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
                if payload["type"] != "refresh":
                    raise HTTPException(status_code=401, detail="Invalid token type")

                new_access_token = jwt.encode(
                    {
                        "sub": payload["sub"],
                        "type": "access",
                        "exp": datetime.now(timezone.utc)
                        + timedelta(minutes=ACCESS_EXPIRE_MINUTES),
                    },
                    SECRET_KEY,
                    algorithm=ALGORITHM,
                )

                response = JSONResponse({"access_token": new_access_token})
                response.set_cookie(
                    "access_token",
                    new_access_token,
                    httponly=True,
                    secure=SECURE_COOKIES,
                    max_age=ACCESS_EXPIRE_MINUTES * 60,
                )
                return response

            except ExpiredSignatureError:
                raise HTTPException(status_code=401, detail="Refresh token expired")
            except JWTError:
                raise HTTPException(status_code=401, detail="Invalid refresh token")

        return await breaker.call(handler)

    async def forgot_password(self, payload, background_tasks: BackgroundTasks):
        async def handler():
            user = await self.repo.get_by_email(payload.email)
            if not user:
                raise HTTPException(status_code=404, detail="Email not found")
            name = f"{user.first_name} {user.last_name}"
            token = await user_generate.generate_reset_token(user.email)
            otp = await user_generate.generate_otp(user.email)
            background_tasks.add_task(send_password_reset_link, user.email, otp, token)
            if user.phone_number:
                background_tasks.add_task(
                    send_sms.send_sms, user.phone_number, otp, name
                )
            return {"message": "Password reset email sent."}

        return await breaker.call(handler)

    async def reset_password(self, payload):
        async def handler():
            email = None
            if payload.token and payload.token.strip():
                try:
                    email = await self.user_verification.verify_reset_token(
                        payload.token
                    )
                except HTTPException:
                    email = None
            if not email and payload.otp and payload.otp.strip():
                try:
                    email = await self.user_verification.verify_otp(payload.otp)
                except HTTPException:
                    email = None
            if not email:
                raise HTTPException(status_code=400, detail="Invalid or expired token")
            user = await self.repo.get_by_email(email)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            user.set_password(payload.new_password)
            await self.repo.update(user)
            return {"message": "Password reset successfully"}

        return await breaker.call(handler)
