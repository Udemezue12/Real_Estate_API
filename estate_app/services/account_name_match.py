import uuid

from core.name_matcher import NameMatcher
from fintechs.syncFlutterwave import FlutterwaveClient
from fintechs.syncPaystack import PaystackClient
from models.enums import AccountVerificationProviders
from repos.profile_repo import UserProfileRepo


class AccountNameMatch:
    def __init__(self, db):
        self.repo = UserProfileRepo(db)
        self.paystack = PaystackClient()
        self.flutterwave = FlutterwaveClient()
        self.matcher = NameMatcher()

    def match_name(self, profile_id: uuid.UUID, account_number: str):
        profile = self.repo.sync_get_profile(profile_id)
        if not profile:
            return

        user = profile.user

        if profile.paystack_bank_code:
            try:
                paystack_account =self.paystack.resolve_account(
                    account_number=account_number,
                    bank_code=profile.paystack_bank_code,
                )

                if not self.matcher.sync_bank_name_match(
                    user, paystack_account["account_name"]
                ):
                    self.repo.mark_paystack_account_number_verification_failed(
                        profile_id,
                        "Name mismatch",
                    )
                else:
                    self.repo.mark_paystack_account_number_verified(
                        profile_id=profile_id,
                        account_verification_provider=AccountVerificationProviders.PAYSTACK,
                        account_number=account_number,
                        bank_code=profile.paystack_bank_code,
                        account_name=paystack_account["account_name"],
                    )

            except Exception as exc:
                self.repo.mark_paystack_account_number_verification_failed(
                    profile_id,
                    str(exc),
                )

        if profile.flutterwave_bank_code:
            try:
                flutterwave_account = self.flutterwave.resolve_account(
                    account_number=account_number,
                    bank_code=profile.flutterwave_bank_code,
                )

                if not self.matcher.bank_name_match(
                    user, flutterwave_account["account_name"]
                ):
                    self.repo.mark_flutterwave_account_number_verification_failed(
                        profile_id,
                        "Name mismatch",
                    )
                else:
                    self.repo.mark_flutterwave_account_number_verified(
                        profile_id=profile_id,
                        account_verification_provider=AccountVerificationProviders.FLUTTERWAVE,
                        account_number=account_number,
                        bank_code=profile.flutterwave_bank_code,
                        account_name=flutterwave_account["account_name"],
                    )

            except Exception as exc:
                self.repo.mark_flutterwave_account_number_verification_failed(
                    profile_id,
                    str(exc),
                )
