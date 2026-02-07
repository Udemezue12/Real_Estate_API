
import logging
import uuid

from fastapi import BackgroundTasks, HTTPException
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from redis.asyncio import Redis

from core.breaker import breaker
from core.check_increment import CheckIncrementTimer
from core.name_matcher import NameMatcher
from core.settings import settings
from email_notify.email_service import EmailService
from models.enums import (
    AccountNumberVerificationStatus,
    BVNVerificationProviders,
    NINVerificationProviders,
)
from repos.auth_repo import AuthRepo
from repos.profile_repo import UserProfileRepo
from services.verification_dispatch import VerificationDispatch
from services.verification_service import VerificationService
from sms_notify.sms_service import send_sms
from tasks.get_account_name_provider_tasks import GetAccountNameVerificationProvider
from tasks.get_receipient_code_tasks import create_receipient_code_task
from verify_nin.verify_nin_permbly import PremblyNINVerifier

from .security_generate import user_generate

reset_serializer = URLSafeTimedSerializer(settings.RESET_SECRET_KEY)
verify_serializer = URLSafeTimedSerializer(settings.VERIFY_EMAIL_SECRET_KEY)
redis = Redis.from_url(settings.CELERY_REDIS_URL, decode_responses=True)
resend_tracker: dict[str, dict] = {}
logger = logging.getLogger("bvn.prembly")


class UserVerification:
    def __init__(self, db):
        self.repo = AuthRepo(db)
        self.profile_repo: UserProfileRepo = UserProfileRepo(db)
        self.check = CheckIncrementTimer()

        self.call_prembly = PremblyNINVerifier()
        self.name_matcher = NameMatcher()
        self.select_account_name_provider: GetAccountNameVerificationProvider = (
            GetAccountNameVerificationProvider()
        )
        self.email_service: EmailService = EmailService()
        self.verification_dispatch: VerificationDispatch = VerificationDispatch(db)
        self.verification_service:VerificationService=VerificationService(db)
    
    async def verify_reset_token(
        self, token: str, expiration: int = 3600
    ) -> str | None:
        try:
            email = reset_serializer.loads(
                token, salt=settings.RESET_PASSWORD_SALT, max_age=expiration
            )
            return email
        except (SignatureExpired, BadSignature):
            return None

    async def verify_verify_token(
        self, token: str, expiration: int = 3600
    ) -> str | None:
        try:
            email = verify_serializer.loads(
                token, salt=settings.VERIFY_EMAIL_SALT, max_age=expiration
            )
            return email
        except (SignatureExpired, BadSignature):
            return None

    async def verify_otp(self, otp: str) -> str:
        async def handler():
            async for key in redis.scan_iter(match="otp:*"):
                stored = await redis.get(key)
                if stored == otp:
                    await redis.delete(key)
                    return key.split(":")[1]
            return None

        return await breaker.call(handler)

    async def resend_verification_email(
        self, email: str, background_tasks: BackgroundTasks
    ):
        async def handler():
            user = await self.repo.get_by_email(email)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            if user.is_verified:
                return {"message": "Email already verified."}
            name = f"{user.first_name} {user.last_name}"

            otp = await user_generate.generate_otp(email)
            token = await user_generate.generate_verify_token(email)
            background_tasks.add_task(
                self.email_service.send_verification_email, email, otp, token, name
            )
            if hasattr(user, "phone_number") and user.phone_number:
                background_tasks.add_task(
                    send_sms.send_sms,
                    user.phone_number,
                    otp,
                    name,
                )
            return {"message": "Email Verification sent to your mailbox and sms"}

        return await breaker.call(handler)

    async def resend_password_reset_link(
        self, email: str, background_tasks: BackgroundTasks
    ):
        # self.check.check_and_increment_resend(email=email)

        async def handler():
            user = await self.repo.get_by_email(email)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            name = f"{user.first_name} {user.last_name}"
            otp = await user_generate.generate_otp(email)
            token = await user_generate.generate_reset_token(email)
            background_tasks.add_task(
                self.email_service.send_password_reset_link, email, otp, token
            )
            if hasattr(user, "phone_number") and user.phone_number:
                background_tasks.add_task(
                    send_sms.send_sms,
                    user.phone_number,
                    otp,
                    name,
                )
            return {
                "message": "Password reset link via your email resent successfully."
            }

        return await breaker.call(handler)

    async def verify_email(self, otp: str | None = None, token: str | None = None):
        async def handler():
            if otp:
                email = await self.verify_otp(otp)
            elif token:
                email = await self.verify_reset_token(token)
            else:
                raise HTTPException(
                    status_code=400, detail="No verification data provided"
                )
            if not email:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid or expired verification email",
                )
            user = await self.repo.get_by_email(email)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            user.email_verified = True
            await self.repo.save(user)
            return {"Message": "Email verified successfully"}

        return await breaker.call(handler)

    
    async def verify_bvn(
        self,
        profile_id: uuid.UUID,
        bvn: str,
        bvn_verification_provider: BVNVerificationProviders,
    ):
        return await self.verification_service.verify_bvn(
            profile_id=profile_id,
            bvn=bvn,
            bvn_verification_provider=bvn_verification_provider,
        )
    async def verify_nin(
        self,
        profile_id: uuid.UUID,
        nin: str,
        nin_verification_provider: NINVerificationProviders,
    ):
        return await self.verification_service.verify_nin(
            profile_id=profile_id,
            nin=nin,
            nin_verification_provider=nin_verification_provider,
        )

    async def reverify_nin(self, profile_id: uuid.UUID, data):
        await self.verification_dispatch.reverify_nin(profile_id=profile_id, data=data)
        return {"status": "verification_started"}

    async def reverify_bvn(self, profile_id: uuid.UUID, data):
        await self.verification_dispatch.reverify_bvn(profile_id=profile_id, data=data)

        return {"status": "verification_started"}

    async def reverify_account_number(self, profile_id: uuid.UUID, data):
        async def handler():
            profile = await self.profile_repo.get_profile(profile_id)
            if (
                profile.account_verification_status
                == AccountNumberVerificationStatus.VERIFIED
            ):
                raise HTTPException(
                    status_code=409, detail="Account number already verified"
                )

            self.select_account_name_provider.get_provider(
                data=data,
                profile_id=profile_id,
            )

            return {"status": "verification_started"}

        return await breaker.call(handler)

    async def get_paystack_code(self, profile_id: uuid.UUID):
        async def handler():
            profile = await self.profile_repo.get_profile(profile_id)
            if (
                profile.account_verification_status
                != AccountNumberVerificationStatus.VERIFIED
            ):
                raise HTTPException(
                    status_code=409, detail="Account number not verified"
                )
            create_receipient_code_task.delay(
                (str(profile.id)),
            )

            return {"message": "Starting.."}

        return await breaker.call(handler)
