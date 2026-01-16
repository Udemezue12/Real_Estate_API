import asyncio
import logging
import uuid

import httpx
from core.get_db import AsyncSessionLocal
from core.name_matcher import NameMatcher
from models.enums import NINVerificationStatus, NINVerificationProviders
from repos.profile_repo import UserProfileRepo
from sqlalchemy.ext.asyncio import AsyncSession
from verify_nin.verify_nin_youVerify import YouVerifyNin

logger = logging.getLogger("nin.youverify")


def create_youverify_nin_task(app):
    class YouVerifyNINTask(app.Task):
        name = "verify_nin_youverify"

        autoretry_for = (RuntimeError, ConnectionError, httpx.HTTPError)
        retry_backoff = True
        retry_jitter = True
        max_retries = 3
        default_retry_delay = 10

        def _run_async(self, coro):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(coro)
            finally:
                loop.close()

        async def _verify_nin(
            self, session: AsyncSession, profile_id: uuid.UUID, nin: str
        ):
            repo = UserProfileRepo(session)

            call_youverify = YouVerifyNin()
            name_matcher = NameMatcher()
            try:
                profile = await repo.get_profile(profile_id=profile_id)
                if profile.nin_verification_status == NINVerificationStatus.VERIFIED:
                    logger.info("Profile %s already verified")
                    return
                result = await call_youverify.verify_nin(nin)

                if not result.get("verified"):
                    await repo.mark_nin_verification_failed(
                        profile_id=profile_id, nin_error="NIN verification failed"
                    )
                    return

                if not await name_matcher.names_match(
                    user=profile.user,
                    first_name=result["first_name"],
                    last_name=result["last_name"],
                ):
                    await repo.mark_nin_verification_failed(
                        profile_id=profile_id,
                        nin_error="NIN verification failed due to name mismatch",
                    )
                    return

                await repo.mark_nin_verified(
                    profile_id=profile_id,
                    nin_verification_provider=NINVerificationProviders.YOU_VERIFY,
                )
                logger.info("NIN verified successfully for profile %s")

            except Exception as e:
                logger.exception("NIN verification error for %s", str(e))
                await repo.mark_nin_verification_failed(
                    profile_id=profile_id,
                    nin_error="NIN verification Error",
                )
                raise

        def run(self, profile_id: uuid.UUID, nin: str):
            async def _runner():
                async with AsyncSessionLocal() as session:
                    await self._verify_nin(
                        session=session,
                        profile_id=profile_id,
                        nin=nin,
                    )

            return self._run_async(_runner())

    return YouVerifyNINTask
