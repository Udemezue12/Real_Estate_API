from celery import Celery
from celery.schedules import crontab
from core.settings import settings
from tasks.expire_pending_rental_viewings import create_rental_viewing_expiry_task
from tasks.expire_pending_sales_viewings import create_sales_viewing_expiry_task
from tasks.prembly_bvn_tasks import create_prembly_bvn_task
from tasks.prembly_nin_tasks import create_prembly_nin_task
from tasks.qoreid_nin_task import create_qoreid_nin_task
from tasks.receipt_tasks import create_receipt_task
from tasks.rent_notifications import create_rent_notification_task
from tasks.youverify_nin_tasks import create_youverify_nin_task


class CeleryManager:
    def __init__(self):
        self.REDIS_URL = settings.CELERY_REDIS_URL

        self.app = Celery(
            "real_estate_tasks",
            broker=self.REDIS_URL,
            backend=self.REDIS_URL,
            include=[
                "tasks.receipt_tasks",
                "tasks.expire_pending_rental_viewings",
                "tasks.rent_notifications",
                "tasks.expire_pending_sales_viewings",
                "tasks.qoreid_nin_task",
                "tasks.youverify_nin_tasks",
                "tasks.prembly_nin_tasks",
                "tasks.prembly_bvn_tasks",
            ],
        )

        self.app.conf.update(
            task_serializer="json",
            task_track_started=True,
            accept_content=["json"],
            result_serializer="json",
            timezone="UTC",
            enable_utc=True,
            broker_connection_retry=True,
            broker_connection_retry_on_startup=True,
            broker_connection_max_retries=None,
            task_acks_late=False,
            worker_cancel_long_running_tasks_on_connection_loss=False,
            broker_use_ssl={"ssl_cert_reqs": "required"},
            redis_backend_use_ssl={"ssl_cert_reqs": "required"},
            redis_socket_keepalive=True,
            redis_socket_timeout=30,
            broker_transport_options={
                "visibility_timeout": 3600,
                "socket_keepalive": True,
                "socket_keepalive_options": {
                    1: 1,
                    2: 3,
                    3: 5,
                },
            },
            worker_hijack_root_logger=False,
        )

        ReceiptTask = create_receipt_task(self.app)
        self.app.register_task(ReceiptTask())

        RentalViewingExpiryTask = create_rental_viewing_expiry_task(self.app)
        self.app.register_task(RentalViewingExpiryTask())

        SalesViewingExpiryTask = create_sales_viewing_expiry_task(self.app)
        self.app.register_task(SalesViewingExpiryTask())

        RentNotificationsTask = create_rent_notification_task(self.app)
        self.app.register_task(RentNotificationsTask())

        YouVerifyNinTask = create_youverify_nin_task(self.app)
        self.app.register_task(YouVerifyNinTask())

        QoreIDVerifyNinTask = create_qoreid_nin_task(self.app)
        self.app.register_task(QoreIDVerifyNinTask())

        PremblyVerifyNinTask = create_prembly_nin_task(self.app)
        self.app.register_task(PremblyVerifyNinTask)
        PremblyVerifyBVNTask = create_prembly_bvn_task(self.app)
        self.app.register_task(PremblyVerifyBVNTask)

        self.app.conf.beat_schedule = {
            "expire-pending-viewings-hourly": {
                "task": "expire_pending_viewings",
                "schedule": crontab(minute=0),
            },
            "process-rent-notifications-daily": {
                "task": "process_rent_notifications",
                "schedule": crontab(hour=1, minute=0),
            },
        }

    async def connect(self):
        print(f"Connecting to Celery broker: {self.REDIS_URL}")
        try:
            inspect = self.app.control.inspect()
            if inspect.ping():
                print("Celery connected successfully.")
            else:
                print("Celery connected but no workers found.")
        except Exception as e:
            print("Celery connection failed:", e)

    def delay(self, func_name: str, *args, **kwargs):
        return self.app.send_task(func_name, args=args, kwargs=kwargs)


celery_app = CeleryManager()
app = celery_app.app
