import logging
from traceback import print_exception

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as e:
            logger.exception(f"Unhandled server error:{e}")

            print_exception(type(e), e, e.__traceback__)
            return Response(
                "Something went wrong on our end. Please try again.",
                status_code=500,
            )
