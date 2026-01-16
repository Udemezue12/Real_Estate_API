import redis.asyncio as redis
from fastapi_admin.providers.login import UsernamePasswordProvider
from .admin_models import AdminUser
from .admin_resources import UserResource
from core.get_db import Base, async_engine
from core.settings import settings

class AdminManager:
    """FastAPI-Admin setup compatible with redis.asyncio and Python 3.11+."""

    def __init__(self):
        self.redis_client = None
        self.admin_app = None

    async def load_fastapi_admin(self):
        """Lazy import to avoid startup crashes."""
        if self.admin_app is None:
            from fastapi_admin.app import app as admin_app

            self.admin_app = admin_app

    async def connect_redis(self):
        """Connect to Redis Cloud."""
        self.redis_client = redis.from_url(
            settings.ADMIN_REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
        await self.load_fastapi_admin()
        print("✅ Redis client ready.")

    async def init_db(self):
        """Create all admin-related tables."""
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✅ Database initialized.")

    async def configure_admin(self):
        """Configure FastAPI-Admin with redis, login, and resources."""
        await self.load_fastapi_admin()

        await self.admin_app.configure(
            redis=self.redis_client,
            login_provider=UsernamePasswordProvider(admin_model=AdminUser),
            resources=[UserResource],
        )
        print("✅ FastAPI-Admin configured.")

    async def setup(self):
        """Full admin setup."""
        await self.connect_redis()
        await self.init_db()
        await self.configure_admin()


# Global instance
admin_manager = AdminManager()
