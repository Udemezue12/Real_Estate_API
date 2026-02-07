from uuid import UUID

from sqlalchemy.exc import IntegrityError

from models.enums import ViewingStatus
from models.models import RentalViewingHistory


class RentalViewHistoryRepo:
    def __init__(self, db):
        self.db = db

    async def log_viewing_change(
        self,
        *,
        convo_id: UUID,
        old_status: ViewingStatus,
        new_status: ViewingStatus,
        user_id: UUID | None = None,
    ):
        try:
            log = RentalViewingHistory(
                convo_id=convo_id,
                old_status=old_status,
                new_status=new_status,
                changed_by=user_id,
            )
            self.db.add(log)
            await self.db.commit()
            await self.db.refresh(log)
            return log
        except IntegrityError:
            await self.db.rollback()
            raise
