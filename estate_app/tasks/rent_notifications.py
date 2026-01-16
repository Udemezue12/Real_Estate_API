import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from core.get_db import AsyncSessionLocal
from email_notify.email_service import (
    send_rent_expired_email,
    send_rent_reminder_email,
)
from repos.rent_ledger_repo import RentLedgerRepository
from repos.tenant_repo import TenantRepo
from sms_notify.sms_service import send_sms

logger = logging.getLogger("rent.notifications")


def create_rent_notification_task(app):
    class RentNotificationTasks(app.Task):
        name = "process_rent_notifications"

        autoretry_for = (RuntimeError, ConnectionError)
        retry_backoff = True
        retry_jitter = True
        max_retries = 3
        default_retry_delay = 10

        def _run_async(self, coro):
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            return loop.run_until_complete(coro)

        async def _process(self, session: AsyncSession):
            tenant_repo = TenantRepo(session)
            ledger_repo = RentLedgerRepository(session)

            
            tenants_7 = await tenant_repo.get_tenants_expiring_in(7)
            for tenant in tenants_7:
                name = " ".join(
                    filter(
                        None, [tenant.first_name, tenant.middle_name, tenant.last_name]
                    )
                )

                if not await ledger_repo.exists(tenant.id, "RENT_REMINDER_7_DAYS"):
                    await ledger_repo.create(
                        tenant.id,
                        "RENT_REMINDER_7_DAYS",
                        new_value={"expires_on": str(tenant.rent_expiry_date)},
                    )

                    await send_rent_reminder_email(tenant.email, 7, name)
                    await send_sms.send_rent_reminder_sms(tenant.phone, 7, name)

            tenants_3 = await tenant_repo.get_tenants_expiring_in(3)
            for tenant in tenants_3:
                name = " ".join(
                    filter(
                        None, [tenant.first_name, tenant.middle_name, tenant.last_name]
                    )
                )

                if not await ledger_repo.exists(tenant.id, "RENT_REMINDER_3_DAYS"):
                    await ledger_repo.create(
                        tenant.id,
                        "RENT_REMINDER_3_DAYS",
                        new_value={"expires_on": str(tenant.rent_expiry_date)},
                    )

                    await send_rent_reminder_email(tenant.email, 3, name)
                    await send_sms.send_rent_reminder_sms(tenant.phone, 3, name)

            expired = await tenant_repo.get_expired_active_tenants()
            for tenant in expired:
                name = " ".join(
                    filter(
                        None, [tenant.first_name, tenant.middle_name, tenant.last_name]
                    )
                )

                if not await ledger_repo.exists(tenant.id, "RENT_EXPIRED"):
                    await tenant_repo.deactivate(tenant)

                    await ledger_repo.create(
                        tenant.id,
                        "RENT_EXPIRED",
                        old_value={"is_active": True},
                        new_value={"is_active": False},
                    )

                    await send_rent_expired_email(tenant.email, name)
                    await send_sms.send_rent_expired_sms(tenant.phone, name)

            await session.commit()

        def run(self):
            async def runner():
                async with AsyncSessionLocal() as session:
                    try:
                        await self._process(session)
                    except Exception:
                        logger.exception("Rent notification task failed")
                        raise

            return self._run_async(runner())

    return RentNotificationTasks
