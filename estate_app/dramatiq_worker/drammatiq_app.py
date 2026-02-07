import dramatiq
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from dramatiq.brokers.redis import RedisBroker
from dramatiq.middleware import (
    AgeLimit,
    AsyncIO,
    Callbacks,
    Pipelines,
    Retries,
    TimeLimit,
)

from core.settings import settings
from drammtiq_tasks.account_name_match_tasks import create_verify_account_task
from drammtiq_tasks.expire_pending_rental_viewings import (
    create_rental_viewing_expiry_task,
)
from drammtiq_tasks.expire_pending_sales_viewings import (
    create_sales_viewing_expiry_task,
)
from drammtiq_tasks.get_bank_name_tasks import create_bank_name_tasks
from drammtiq_tasks.get_receipient_code_tasks import create_receipient_code_task
from drammtiq_tasks.prembly_bvn_tasks import create_prembly_bvn_task
from drammtiq_tasks.prembly_nin_tasks import create_prembly_nin_task
from drammtiq_tasks.process_payment_transfer_tasks import create_auto_payout_task
from drammtiq_tasks.qoreid_nin_tasks import create_qoreid_nin_task
from drammtiq_tasks.receipt_tasks import create_receipt_task
from drammtiq_tasks.rent_notifications import create_rent_notification_task
from drammtiq_tasks.update_bank_codes_tasks import update_bank_code_task
from drammtiq_tasks.youverify_nin_tasks import create_youverify_nin_task


class DramatiqManager:
    def __init__(self):
        self.REDIS_URL = settings.CELERY_REDIS_URL  # reuse same env

        # -------------------------------
        # Redis Broker
        # -------------------------------
        self.broker = RedisBroker(url=self.REDIS_URL)

        self.broker.add_middleware(AgeLimit(max_age=3600000))
        self.broker.add_middleware(TimeLimit(time_limit=600000))
        self.broker.add_middleware(Retries(max_retries=5))
        self.broker.add_middleware(Pipelines())
        self.broker.add_middleware(Callbacks())
        self.broker.add_middleware(AsyncIO())

        dramatiq.set_broker(self.broker)

        self._register_tasks()

        self.scheduler = BackgroundScheduler(timezone="UTC")
        self._register_cron_jobs()
        self.scheduler.start()

    def _register_tasks(self):
        """
        Task factory pattern identical to your Celery version
        """

        create_receipt_task()
        create_rental_viewing_expiry_task()
        create_sales_viewing_expiry_task()
        create_rent_notification_task()
        create_youverify_nin_task()
        create_qoreid_nin_task()
        create_prembly_nin_task()
        create_prembly_bvn_task()
        create_verify_account_task()
        create_receipient_code_task()
        create_auto_payout_task()
        update_bank_code_task()
        create_bank_name_tasks()

    def _register_cron_jobs(self):
        """
        Celery Beat → APScheduler
        """

        self.scheduler.add_job(
            func=lambda: self.broker.get_actor("expire_pending_viewings").send(),
            trigger=CronTrigger(minute=0),
            id="expire-pending-viewings-hourly",
            replace_existing=True,
        )

        self.scheduler.add_job(
            func=lambda: self.broker.get_actor("process_rent_notifications").send(),
            trigger=CronTrigger(hour=1, minute=0),
            id="process-rent-notifications-daily",
            replace_existing=True,
        )

    async def connect(self):
        print(f"Connecting to Dramatiq broker: {self.REDIS_URL}")
        try:
            self.broker.client.ping()
            print("Dramatiq connected successfully.")
        except Exception as e:
            print("Dramatiq connection failed:", e)

    def delay(self, actor_name: str, *args, **kwargs):
        actor = self.broker.get_actor(actor_name)
        return actor.send(*args, **kwargs)


dramatiq_app = DramatiqManager()
