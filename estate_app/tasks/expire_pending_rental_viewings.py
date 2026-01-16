import asyncio
from datetime import datetime, timedelta, timezone
from typing import List

from core.get_db import AsyncSessionLocal
from models.enums import ViewingStatus
from models.models import RentalConversation
from repos.rental_conversation_repo import RentalConversationRepo
from repos.rental_log_history_repo import RentalViewHistoryRepo
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


def create_rental_viewing_expiry_task(app):
    class ViewingRentalExpiryTask(app.Task):
        name = "expire_pending_rental_viewings"

        autoretry_for = (RuntimeError, ConnectionError)
        retry_backoff = True
        retry_jitter = True
        max_retries = 3
        default_retry_delay = 30

        def _run_async(self, coro):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(coro)
            finally:
                loop.close()

        async def _expire_pending(
            self,
            session: AsyncSession,
        ) -> int:
            repo = RentalConversationRepo(session)
            log_repo = RentalViewHistoryRepo(session)

            cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

            stmt = select(RentalConversation).where(
                RentalConversation.viewing_status == ViewingStatus.PENDING,
                RentalConversation.updated_at < cutoff,
            )
            result = await session.execute(stmt)
            convos: List[RentalConversation] = result.scalars().all()

            expired_count = 0

            for convo in convos:
                if convo.viewing_status != ViewingStatus.PENDING:
                    continue

                await repo.set_viewing(
                    convo=convo,
                    viewing_date=None,
                    status=ViewingStatus.DECLINED,
                    set_by=None,
                )
                await log_repo.log_viewing_change(
                    convo_id=convo.id,
                    old_status=ViewingStatus.PENDING,
                    new_status=ViewingStatus.DECLINED,
                    user_id=None,
                )
                expired_count += 1

            return expired_count

        def run(self):
            async def _runner():
                async with AsyncSessionLocal() as session:
                    return await self._expire_pending(session)

            return self._run_async(_runner())

    return ViewingRentalExpiryTask
