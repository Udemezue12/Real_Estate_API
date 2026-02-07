import uuid

from repos.bank_repo import BankRepo
from repos.profile_repo import UserProfileRepo


class UpdateBankCodes:
    def __init__(self, db):
        self.repo = UserProfileRepo(db)
        self.bank_repo = BankRepo(db)

    async def update_code(self, profile_id: uuid.UUID, user_input: str):
        bank_name = await self.bank_repo.get_name(name=user_input)

        if not bank_name:
            return
        profile = await self.repo.get_profile(profile_id)

        if not profile:
            return
        if bank_name.paystack_bank_code:
            await self.repo.update_paystack_bank_code(
                profile_id, bank_name.paystack_bank_code
            )
        if bank_name.flutterwave_bank_code:
            await self.repo.update_flutterwave_bank_code(
                profile_id, bank_name.flutterwave_bank_code
            )
