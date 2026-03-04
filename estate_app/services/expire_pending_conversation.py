from models.enums import ViewingStatus
from repos.rental_conversation_repo import RentalConversationRepo
from repos.rental_log_history_repo import RentalViewHistoryRepo
from repos.sales_conversation_repo import SaleConversationRepo
from repos.sales_log_history_repo import SaleViewHistoryRepo


class ExpirePendingConverstaion:
    def __init__(self, db):
        self.sale_repo = SaleConversationRepo(db)
        self.sale_log_repo = SaleViewHistoryRepo(db)
        self.rental_repo = RentalConversationRepo(db)
        self.rental_log_repo = RentalViewHistoryRepo(db)

    def expire_pending_sales(self):
        convos = self.sale_repo.sync_get_pending_conversations()
        expired_count = 0

        for convo in convos:
            if convo.viewing_status != ViewingStatus.PENDING:
                continue

            self.sale_repo.sync_set_viewing(
                convo=convo,
                viewing_date=None,
                status=ViewingStatus.DECLINED,
                set_by=None,
            )
            self.sale_log_repo.sync_log_viewing_change(
                convo_id=convo.id,
                old_status=ViewingStatus.PENDING,
                new_status=ViewingStatus.DECLINED,
                user_id=None,
            )
            expired_count += 1

        return expired_count

    def expire_pending_rentals(self):
        convos = self.rental_repo.sync_get_pending_conversations()
        expired_count = 0

        for convo in convos:
            if convo.viewing_status != ViewingStatus.PENDING:
                continue

            self.rental_repo.sync_set_viewing(
                convo=convo,
                viewing_date=None,
                status=ViewingStatus.DECLINED,
                set_by=None,
            )
            self.rental_log_repo.sync_log_viewing_change(
                convo_id=convo.id,
                old_status=ViewingStatus.PENDING,
                new_status=ViewingStatus.DECLINED,
                user_id=None,
            )
            expired_count += 1

        return expired_count
