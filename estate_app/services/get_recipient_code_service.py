import uuid

from fintechs.paystack import PaystackClient
from models.enums import AccountNumberVerificationStatus
from repos.profile_repo import UserProfileRepo


class GetRecipientCode:
    def __init__(self, db):
        self.repo = UserProfileRepo(db)
        self.paystack = PaystackClient()

    async def get_code(self, profile_id: uuid.UUID):
        profile = await self.repo.get_profile(profile_id)

        if not profile:
            return

        if (
            profile.paystack_account_verification_status
            == AccountNumberVerificationStatus.FAILED
        ):
            return

        if profile.paystack_recipient_code:
            return

        if (
            profile.paystack_account_verification_status
            != AccountNumberVerificationStatus.VERIFIED
        ):
            return

        if not all(
            [
                profile.paystack_account_name,
                profile.account_number,
                profile.paystack_bank_code,
            ]
        ):
            return
        try:
            recipient_code = await self.paystack.create_transfer_recipient(
                name=profile.paystack_account_name,
                account_number=profile.account_number,
                bank_code=profile.paystack_bank_code,
            )
        except Exception as e:
            print(f"Paystack recipient error: {e}")
            raise

        await self.repo.set_paystack_code(profile_id, recipient_code)
        return {"message": "Success"}
