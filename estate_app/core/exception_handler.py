from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class ValidationErrorHandler:
    async def __call__(self, request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={
                "error": "Validation did not work",
                "details": exc.errors(),
            },
        )
