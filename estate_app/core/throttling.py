from redis.asyncio import from_url
from .settings import settings
from fastapi import Depends, Request
from fastapi.responses import JSONResponse
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter


class RateLimitManager:
    def __init__(self):
        self.redis = None

    async def connect(self):
        try:
            self.redis = from_url(
                settings.RATE_LIMIT_REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
            )
            await FastAPILimiter.init(self.redis)
            print("Rate limiter initialized successfully (Redis Cloud).")
        except Exception as e:
            print(f"Rate limiter initialization failed: {e}")

    @staticmethod
    async def limit_exceeded_handler(request: Request, exc):
        try:
            return JSONResponse(
                status_code=429,
                content={"detail": "Limit exceeded. Please try again later."},
            )
        except Exception as e:
            print(f"Error in limit_exceeded_handler: {e}")
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error."},
            )

    async def user_or_ip(self, request: Request) -> str:
        try:
            user = getattr(request.state, "user", None)
            user_id = getattr(user, "id", None)

            if user_id is not None:
                return f"user:{str(user_id)}"
        except Exception:
            pass

        try:
            if request.client and request.client.host:
                return f"ip:{request.client.host}"
        except Exception:
            pass

        return "anonymous"


rate_limiter_manager = RateLimitManager()
rate_limiter = RateLimiter
rate_limit = Depends(
    rate_limiter(times=5, seconds=10, identifier=rate_limiter_manager.user_or_ip)
)
