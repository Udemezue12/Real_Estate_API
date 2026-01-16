from datetime import datetime

from fastapi import HTTPException

from .settings import settings

resend_tracker: dict[str, dict] = {}


class CheckIncrementTimer:
    async def check_and_increment_resend(self, email: str) -> None:
        now = datetime.now(timezone.utc)

        info = resend_tracker.get(email, {"count": 0, "lock_until": None})

        if info["lock_until"] and info["lock_until"] > now:
            remaining = (info["lock_until"] - now).seconds
            raise HTTPException(
                status_code=429,
                detail=f"Maximum resend attempts reached. Try again in {remaining} seconds.",
            )

        info["count"] = info.get("count", 0) + 1
        if info["count"] >= settings.MAX_RESENDS:
            info["lock_until"] = now + settings.LOCK_DURATION
            info["count"] = 0
        else:
            info["lock_until"] = None

        resend_tracker[email] = info
