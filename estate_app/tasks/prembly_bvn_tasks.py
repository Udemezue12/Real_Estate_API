import asyncio
import logging
import uuid

import httpx
from core.get_db import AsyncSessionLocal
from core.name_matcher import NameMatcher
from models.enums import BVNStatus, BVNVerificationProviders
from repos.profile_repo import UserProfileRepo
from sqlalchemy.ext.asyncio import AsyncSession
from verify_nin.verify_nin_permbly import PremblyNINVerifier

logger = logging.getLogger("bvn.prembly")


def create_prembly_bvn_task(app):
    class PremblyBVNTask(app.Task):
        name = "verify_bvn_prembly"

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
            self, session: AsyncSession, profile_id: uuid.UUID, bvn: str
        ):
            repo = UserProfileRepo(session)
            
            call_prembly = PremblyNINVerifier()
            name_matcher = NameMatcher()
            try:
                profile = await repo.get_profile(profile_id=profile_id)
                if profile.bvn_status == BVNStatus.VERIFIED:
                    logger.info("Profile %s already verified")
                    return
                result = await call_prembly.verify_nin(bvn)

                if not result.get("verified"):
                    await repo.mark_bvn_failed(
                        profile_id=profile_id, bvn_error="BVN verification failed"
                    )
                    return

                if not await name_matcher.names_match(
                    user=profile.user,
                    first_name=result["first_name"],
                    last_name=result["last_name"],
                ):
                    await repo.mark_bvn_failed(
                        profile_id=profile_id,
                        bvn_error="BVN verification failed due to name mismatch",
                    )
                    return

                await repo.mark_bvn_verified(
                    profile_id=profile_id,
                    bvn_verification_provider=BVNVerificationProviders.PREMBLY,
                )
                logger.info("BVN verified successfully for profile %s")

            except Exception as e:
                logger.exception("NIN verification error for %s", str(e))
                await repo.mark_bvn_failed(
                    profile_id=profile_id,
                    bvn_error="BVN verification Error",
                )
                raise

        def run(self, profile_id: uuid.UUID, bvn: str):
            async def _runner():
                async with AsyncSessionLocal() as session:
                    await self._verify_nin(
                        session=session,
                        profile_id=profile_id,
                        bvn=bvn,
                    )

            return self._run_async(_runner())

    return PremblyBVNTask
