import logging
from functools import wraps

from fastapi import HTTPException, Request
from .friendly_msg import get_friendly_message

logger = logging.getLogger(__name__)





def safe_handler(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        request: Request | None = None
        for arg in list(args) + list(kwargs.values()):
            if isinstance(arg, Request):
                request = arg
                break

        try:
            return await func(*args, **kwargs)
        except HTTPException as e:
            if request:
                client_ip = request.client.host if request.client else "unknown"
                path = request.url.path
                trace_id = request.headers.get("X-Request-ID", "none")
                logger.warning(
                    f"[HTTPException] TraceID={trace_id} | {e.status_code} - {path} "
                    f"from {client_ip}: {e.detail}"
                )
            raise
        except Exception as e:
            if request:
                client_ip = request.client.host if request.client else "unknown"
                path = request.url.path
                trace_id = request.headers.get("X-Request-ID", "none")
                logger.error(
                    f"[Unhandled Error] TraceID={trace_id} | in {func.__name__} | Path: {path} | "
                    f"Client: {client_ip} | Error: {e}",
                    exc_info=True,
                )
            else:
                logger.error(
                    f"[Unhandled Error] in {func.__name__}: {e}", exc_info=True
                )
            raise HTTPException(status_code=500, detail=get_friendly_message(e))

    return wrapper