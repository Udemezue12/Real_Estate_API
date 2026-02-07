import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI

from admin.admin_init import admin_manager
from core.rabbitmq import rabbitmq
from core.throttling import rate_limiter_manager
from repos.auth_repo import AuthRepo
from services.bank_service import BankService
from services.lga_service import LGAService
from services.state_services import StateService
from sms_notify.sms_service import send_sms

from .cache import cache
from .cloudinary_setup import cloudinary_client
from .get_db import AsyncSessionLocal

logger = logging.getLogger("startup")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Waiting for application startup...")

    try:
        await admin_manager.connect_redis()
    except Exception:
        logger.exception("Admin Redis connection failed")

    try:
        print("Connecting to Cloudinary")
        await cloudinary_client.connect()
    except Exception as e:
        print(f"Cannot connect to Cloudinary: {e}")

    try:
        async with AsyncSessionLocal() as db:
            cutoff = datetime.now(timezone.utc) - timedelta(days=7)
            await AuthRepo(db).delete_expired_blacklisted_tokens(cutoff)
            logger.info("Blacklisted tokens cleanup completed.")
    except Exception:
        logger.exception("Failed to clean up blacklisted tokens")

    try:
        await send_sms.connect()
        await send_sms.ping()
        logger.info("SMS service connected.")
    except Exception:
        logger.exception("Failed to connect to SMS service")

    try:
        await rabbitmq.connect()
        await rabbitmq.declare_queue_with_dlq("location_events")
        logger.info("RabbitMQ connected.")
    except Exception:
        logger.exception("RabbitMQ connection failed")

    try:
        await cache.connect()
        logger.info("Upstash Redis connected.")
    except Exception:
        logger.exception("Upstash Redis connection failed")
    

    try:
        await rate_limiter_manager.connect()
        logger.info("Rate limiter connected.")
    except Exception:
        logger.exception("Rate limiter connection failed")

    # try:
    #     if os.getenv("RUN_LOCAL_PINGER", "false").lower() == "true":
    #         urls = settings.CRITICAL_SERVICE_URLS
    #         if urls and any(url.strip() for url in urls):
    #             logger.info("Starting lightweight periodic pinger...")
    #             await pinger.start())
    # except Exception:
    #     logger.exception("Failed to start lightweight periodic pinger")
    # try:
    #     async with AsyncSessionLocal() as db:
    #         await BankService(db).create()
    # except Exception:
    #     logger.exception("Failed to update banks ")

    # try:
    #     async with AsyncSessionLocal() as db:
    #         await StateService(db).create_state()
    # except Exception:
    #     logger.exception("Failed to create or update states ")
    # try:
    #     async with AsyncSessionLocal() as db:
    #         await LGAService(db).create_lga()
    # except Exception:
    #     logger.exception("Failed to create or update LGA ")
    logger.info("Application startup complete.")

    yield

    try:
        if rabbitmq.connection and not rabbitmq.connection.is_closed:
            await rabbitmq.connection.close()
    except Exception:
        logger.exception("Failed to close RabbitMQ connection")
