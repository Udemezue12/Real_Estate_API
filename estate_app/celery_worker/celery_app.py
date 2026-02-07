from celery import Celery
from celery.schedules import crontab

from core.settings import settings

REDIS_URL = settings.CELERY_REDIS_URL

celery_app = Celery(
    "real_estate_tasks",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    task_track_started=True,
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "expire_pending_rentals": {
            "task": "expire_pending_rental_viewings",
            "schedule": crontab(minute=0),
        },
        "expire_pending_sales": {
            "task": "expire_pending_sales_viewings",
            "schedule": crontab(minute=0),
        },
        "process-rent-notifications-daily": {
            "task": "process_rent_notifications",
            "schedule": crontab(hour=1, minute=0),
        },
    },
    broker_connection_retry=True,
    broker_connection_retry_on_startup=True,
    broker_connection_max_retries=None,
    task_acks_late=False,
    worker_cancel_long_running_tasks_on_connection_loss=False,
    # broker_use_ssl={"ssl_cert_reqs": "required"},
    # redis_backend_use_ssl={"ssl_cert_reqs": "required"},
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


async def connect():
    print(f"Connecting to Celery broker: {self.REDIS_URL}")
    try:
        inspect = celery_app.control.inspect()
        if inspect.ping():
            print("Celery connected successfully.")
        else:
            print("Celery connected but no workers found.")
    except Exception as e:
        print("Celery connection failed:", e)


def delay(func_name: str, *args, **kwargs):
    return celery_app.send_task(func_name, args=args, kwargs=kwargs)


import tasks.account_name_match_tasks
import tasks.expire_pending_rental_viewings
import tasks.expire_pending_sales_viewings
import tasks.get_bank_name_tasks
import tasks.get_receipient_code_tasks
import tasks.prembly_bvn_tasks
import tasks.prembly_nin_tasks
import tasks.process_payment_transfer_tasks
import tasks.qoreid_nin_task
import tasks.receipt_tasks
import tasks.rent_notifications
import tasks.send_letter_tasks
import tasks.update_bank_codes_tasks
import tasks.youverify_nin_tasks

app = celery_app
