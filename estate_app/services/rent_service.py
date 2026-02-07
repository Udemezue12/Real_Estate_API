from fastapi import BackgroundTasks

from email_notify.email_service import EmailService
from repos.rent_ledger_repo import RentLedgerRepository
from repos.tenant_repo import TenantRepo
from sms_notify.sms_service import send_sms


class RentService:
    def __init__(self, db):
        self.db = db
        self.tenant_repo = TenantRepo(db)
        self.ledger_repo = RentLedgerRepository(db)
        self.email_service: EmailService = EmailService()

    async def process_rent_notifications(self, background_tasks: BackgroundTasks):
        tenants_7 = await self.tenant_repo.get_tenants_expiring_in(7)

        for tenant in tenants_7:
            name = " ".join(
                filter(
                    None,
                    [tenant.first_name, tenant.middle_name, tenant.last_name],
                )
            )

            if not await self.ledger_repo.exists(tenant.id, "RENT_REMINDER_7_DAYS"):
                await self.ledger_repo.create(
                    tenant.id,
                    "RENT_REMINDER_7_DAYS",
                    new_value={"expires_on": str(tenant.rent_expiry_date)},
                )

            await self.email_service.send_rent_reminder_email(tenant.email, 7, name)
            await send_sms.send_rent_reminder_sms(tenant.phone, 7, name)

        tenants_3 = await self.tenant_repo.get_tenants_expiring_in(3)

        for tenant in tenants_3:
            latter_name = " ".join(
                filter(
                    None,
                    [tenant.first_name, tenant.middle_name, tenant.last_name],
                )
            )
            if not await self.ledger_repo.exists(tenant.id, "RENT_REMINDER_3_DAYS"):
                await self.ledger_repo.create(
                    tenant.id,
                    "RENT_REMINDER_3_DAYS",
                    new_value={"expires_on": str(tenant.rent_expiry_date)},
                )

                background_tasks.add_task(
                    send_sms.send_rent_reminder_sms,
                    tenant.email,
                    3,
                    latter_name,
                )
                background_tasks.add_task(
                    self.email_service.send_rent_reminder_email,
                    tenant.email,
                    3,
                    latter_name,
                )

        expired = await self.tenant_repo.get_expired_active_tenants()

        for tenant in expired:
            get_name = " ".join(
                filter(
                    None,
                    [tenant.first_name, tenant.middle_name, tenant.last_name],
                )
            )
            if not await self.ledger_repo.exists(tenant.id, "RENT_EXPIRED"):
                await self.tenant_repo.activate_or_deactivate(
                    tenant_id=tenant.id, is_active=False
                )

                await self.ledger_repo.create(
                    tenant.id,
                    "RENT_EXPIRED",
                    old_value={"is_active": True},
                    new_value={"is_active": False},
                )

                background_tasks.add_task(
                    send_sms.send_rent_expired_sms, tenant.phone, get_name
                )
                background_tasks.add_task(
                    self.email_service.send_rent_expired_email, tenant.email, get_name
                )

        await self.tenant_repo.db_commit()
        return {"status": "Processed"}

    async def process_rent_notifications_using_celery(self):
        tenants_7 = await self.tenant_repo.get_tenants_expiring_in(7)

        for tenant in tenants_7:
            name = " ".join(
                filter(
                    None,
                    [tenant.first_name, tenant.middle_name, tenant.last_name],
                )
            )

            if not await self.ledger_repo.exists(tenant.id, "RENT_REMINDER_7_DAYS"):
                await self.ledger_repo.create(
                    tenant.id,
                    "RENT_REMINDER_7_DAYS",
                    new_value={"expires_on": str(tenant.rent_expiry_date)},
                )

            await self.email_service.send_rent_reminder_email(tenant.email, 7, name)
            await send_sms.send_rent_reminder_sms(tenant.phone, 7, name)

        tenants_3 = await self.tenant_repo.get_tenants_expiring_in(3)

        for tenant in tenants_3:
            latter_name = " ".join(
                filter(
                    None,
                    [tenant.first_name, tenant.middle_name, tenant.last_name],
                )
            )
            if not await self.ledger_repo.exists(tenant.id, "RENT_REMINDER_3_DAYS"):
                await self.ledger_repo.create(
                    tenant.id,
                    "RENT_REMINDER_3_DAYS",
                    new_value={"expires_on": str(tenant.rent_expiry_date)},
                )

                await self.email_service.send_rent_reminder_email(tenant.email, 3, latter_name)
                await send_sms.send_rent_reminder_sms(tenant.phone, 3, latter_name)

        expired = await self.tenant_repo.get_expired_active_tenants()

        for tenant in expired:
            get_name = " ".join(
                filter(
                    None,
                    [tenant.first_name, tenant.middle_name, tenant.last_name],
                )
            )
            if not await self.ledger_repo.exists(tenant.id, "RENT_EXPIRED"):
                await self.tenant_repo.activate_or_deactivate(
                    tenant_id=tenant.id, is_active=False
                )

                await self.ledger_repo.create(
                    tenant.id,
                    "RENT_EXPIRED",
                    old_value={"is_active": True},
                    new_value={"is_active": False},
                )

                await self.email_service.send_rent_expired_email(tenant.email, get_name)
                await send_sms.send_rent_expired_sms(tenant.phone, get_name)

        await self.tenant_repo.db_commit()
        return {"status": "Processed"}
