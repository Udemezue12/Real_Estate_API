import uuid

from core.name_matcher import NameMatcher
from fintechs.flutterwave import FlutterwaveClient
from fintechs.paystack import PaystackClient
from models.enums import AccountVerificationProviders
from repos.profile_repo import UserProfileRepo


class AccountNameMatch:
    def __init__(self, db):
        self.repo = UserProfileRepo(db)
        self.paystack = PaystackClient()
        self.flutterwave = FlutterwaveClient()
        self.matcher = NameMatcher()

    async def match_name(self, profile_id: uuid.UUID, account_number: str):
        profile = await self.repo.get_profile(profile_id)
        if not profile:
            return

        user = profile.user

        if profile.paystack_bank_code:
            try:
                paystack_account = await self.paystack.resolve_account(
                    account_number=account_number,
                    bank_code=profile.paystack_bank_code,
                )

                if not await self.matcher.bank_name_match(
                    user, paystack_account["account_name"]
                ):
                    await self.repo.mark_paystack_account_number_verification_failed(
                        profile_id,
                        "Name mismatch",
                    )
                else:
                    await self.repo.mark_paystack_account_number_verified(
                        profile_id=profile_id,
                        account_verification_provider=AccountVerificationProviders.PAYSTACK,
                        account_number=account_number,
                        bank_code=profile.paystack_bank_code,
                        account_name=paystack_account["account_name"],
                    )

            except Exception as exc:
                await self.repo.mark_paystack_account_number_verification_failed(
                    profile_id,
                    str(exc),
                )

        if profile.flutterwave_bank_code:
            try:
                flutterwave_account = await self.flutterwave.resolve_account(
                    account_number=account_number,
                    bank_code=profile.flutterwave_bank_code,
                )

                if not await self.matcher.bank_name_match(
                    user, flutterwave_account["account_name"]
                ):
                    await self.repo.mark_flutterwave_account_number_verification_failed(
                        profile_id,
                        "Name mismatch",
                    )
                else:
                    await self.repo.mark_flutterwave_account_number_verified(
                        profile_id=profile_id,
                        account_verification_provider=AccountVerificationProviders.FLUTTERWAVE,
                        account_number=account_number,
                        bank_code=profile.flutterwave_bank_code,
                        account_name=flutterwave_account["account_name"],
                    )

            except Exception as exc:
                await self.repo.mark_flutterwave_account_number_verification_failed(
                    profile_id,
                    str(exc),
                )
