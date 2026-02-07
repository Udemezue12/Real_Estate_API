from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class ValidationErrorHandler:
    async def __call__(self, request: Request, exc: RequestValidationError):

        errors = []

        for err in exc.errors():
            errors.append({
                "loc": err.get("loc"),
                "msg": str(err.get("msg")),   
                "type": err.get("type"),
            })

        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "error": "Validation failed",
                "details": errors,
            },
        )
