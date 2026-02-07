from decimal import Decimal

from fastapi import HTTPException

from core.date_helper import calculate_expiry
from models.models import RentReceipt, Tenant
from repos.rent_ledger_repo import RentLedgerRepository
from repos.tenant_repo import TenantRepo


class RentAmountAndRenewalService:
    def __init__(self, db):
        self.tenant_repo: TenantRepo = TenantRepo(db)
        self.ledger_repo: RentLedgerRepository = RentLedgerRepository(db)

    async def renew_from_receipt(self, receipt: RentReceipt):
        tenant = await self.tenant_repo.get_by_id(receipt.tenant_id)

        if not tenant or tenant.matched_user_id is None:
            raise HTTPException(404, "Not Found")

        old_expiry = tenant.rent_expiry_date
        rent_cycle = tenant.rent_cycle

        new_start = tenant.rent_expiry_date
        new_expiry = calculate_expiry(new_start, rent_cycle)

        await self.tenant_repo.update(
            user_id=tenant.matched_user_id,
            tenant_id=tenant.id,
            new_rent_start_date=new_start,
            new_rent_expiry_date=new_expiry,
            new_rent_cycle=rent_cycle,
        )

        await self.ledger_repo.create(
            tenant.id,
            "RENT_RENEWED",
            old_value={"rent_expiry_date": str(old_expiry)},
            new_value={"rent_expiry_date": str(new_expiry)},
        )

    async def update_rent_amount(self, tenant: Tenant, new_amount: Decimal):
        old = {
            "rent_amount": str(tenant.rent_amount),
            "rent_cycle": tenant.rent_cycle,
        }
        tenant.rent_amount = new_amount
        await self.ledger_repo.create(
            tenant_id=tenant.id,
            old_value=old,
            new_value={
                "rent_amount": str(new_amount),
                "rent_cycle": tenant.rent_cycle,
            },
            event="RENT_AMOUNT_CHANGED",
        )
