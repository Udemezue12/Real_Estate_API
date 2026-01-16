import secrets

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from .settings import settings

csrf_router = APIRouter(tags=["CSRF TOKEN"])


@csrf_router.get("/csrf_token")
async def get_csrf_token(request: Request):
    try:
        csrf_token = secrets.token_hex(32)
        
        request.session["csrf_token"] = csrf_token

        response = JSONResponse(
            content={"csrf_token": csrf_token},
            headers={
                "Access-Control-Allow-Origin": settings.FRONTEND_URL,
                "Access-Control-Allow-Credentials": "true",
                "Cache-Control": "no-store",
            },
        )

        response.set_cookie(
            key="csrf_token",
            value=csrf_token,
            httponly=False,
            secure=settings.SECURE_COOKIES,
            samesite="lax",
            max_age=settings.CSRF_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        )
        


        return response

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"detail": f"Failed to generate CSRF token: {str(e)}"},
        )