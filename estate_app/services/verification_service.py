import logging
import uuid



from core.get_provider import ProviderResolver
from core.name_matcher import NameMatcher
from models.enums import (
    BVNStatus,
    BVNVerificationProviders,
    NINVerificationProviders,
    NINVerificationStatus,
)
from repos.profile_repo import UserProfileRepo

logger = logging.getLogger("bvn.prembly")


class VerificationService:
    def __init__(self, db):
        self.profile_repo = UserProfileRepo(db)
        self.provider = ProviderResolver()
        self.name_matcher = NameMatcher()

    async def verify_bvn(
        self,
        profile_id: uuid.UUID,
        bvn: str,
        bvn_verification_provider: BVNVerificationProviders,
    ):
        try:
            profile = await self.profile_repo.get_profile(profile_id=profile_id)

            if profile.bvn_status == BVNStatus.VERIFIED:
                logger.info(
                    "Profile %s already verified",
                    profile_id,
                )
                return
            verifier = self.provider.get_bvn(bvn_verification_provider)

            result = await verifier.verify_nin(bvn)

            if not result.get("verified"):
                await self.profile_repo.mark_bvn_verification_failed(
                    profile_id=profile_id,
                    bvn_error="BVN verification failed",
                )
                return

            if not await self.name_matcher.names_match(
                user=profile.user,
                first_name=result["first_name"],
                last_name=result["last_name"],
            ):
                await self.profile_repo.mark_bvn_verification_failed(
                    profile_id=profile_id,
                    bvn_error="BVN verification failed due to name mismatch",
                )
                return

            await self.profile_repo.mark_bvn_verified(
                profile_id=profile_id,
                bvn_verification_provider=bvn_verification_provider,
            )

            logger.info(
                "BVN verified successfully for profile %s",
                profile_id,
            )

        except Exception:
            logger.exception(
                "NIN verification error for profile %s",
                profile_id,
            )

            await self.profile_repo.mark_bvn_verification_failed(
                profile_id=profile_id,
                bvn_error="BVN verification Error",
            )

            raise

    async def verify_nin(
        self,
        profile_id: uuid.UUID,
        nin: str,
        nin_verification_provider: NINVerificationProviders,
    ):
        try:
            profile = await self.profile_repo.get_profile(profile_id=profile_id)
            if profile.nin_verification_status == NINVerificationStatus.VERIFIED:
                logger.info("Profile %s already verified", profile_id)
                return
            verifier = self.provider.get_nin(nin_verification_provider)

            result = await verifier.verify_nin(nin)

            if not result.get("verified"):
                await self.profile_repo.mark_nin_verification_failed(
                    profile_id=profile_id, nin_error="NIN verification failed"
                )
                return

            if not await self.name_matcher.names_match(
                user=profile.user,
                first_name=result["first_name"],
                last_name=result["last_name"],
            ):
                await self.profile_repo.mark_nin_verification_failed(
                    profile_id=profile_id,
                    nin_error="NIN verification failed due to name mismatch",
                )
                return
            await self.profile_repo.mark_nin_verified(
                profile_id=profile_id,
                nin_verification_provider=nin_verification_provider,
            )
            logger.info("NIN verified successfully for profile %s")

        except Exception as e:
            logger.exception("NIN verification error for %s", str(e))
            await self.profile_repo.mark_nin_verification_failed(
                profile_id=profile_id,
                nin_error="NIN verification Error",
            )
            raise
