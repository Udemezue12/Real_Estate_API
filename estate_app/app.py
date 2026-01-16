from core.setup_gdal import setup_gdal

setup_gdal()  # Only use it in development

import logging
from pathlib import Path

import uvicorn
from admin_piccolo_folder.admin_app import AdminApp
from core.catch_error_middleware import ErrorHandlerMiddleware
from core.exception_handler import ValidationErrorHandler
from fastapi.exceptions import RequestValidationError
from core.csrf_middleware import AutoRefreshAccessTokenMiddleware
from core.get_csrfToken import csrf_router
from core.lifespan import lifespan
from core.settings import settings
from core.throttling import rate_limiter_manager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi_admin.app import app as admin_app
from realtime.chat_routes import router as sales_chat_router
from routes.auth_routes import router as user_router
from routes.cloudinary_routes import router as cloudinary_router
from routes.lga_routes import router as lga_router
from routes.passkey_routes import router as passkey_router
from routes.profile_routes import router as profile_router
from routes.property_image_routes import router as property_image_router
from routes.property_routes import router as property_router
from routes.rent_proof_routes import router as proofs_router
from routes.rent_receipt_routes import router as rent_receipts_router
from routes.rental_images import router as rental_upload_router
from routes.rental_listing_routes import router as rental_router
from routes.rental_message_routes import router as rental_message_router
from routes.sales_images import router as sale_image_router
from routes.sales_message_routes import router as sales_message_router
from routes.sales_routes import router as sales_router
from routes.state_routes import router as state_router
from routes.tenant_routes import router as tenant_router
from starlette.middleware.sessions import SessionMiddleware
from core.auto_logout_middleware import AutoLogoutMiddleware

app = FastAPI()


logging.basicConfig(level=logging.INFO)
app = FastAPI(
    lifespan=lifespan,
    title=settings.PROJECT_NAME,
    exception_handlers={429: rate_limiter_manager.limit_exceeded_handler},
    version="2.0.0",
)

BASE_DIR = Path(__file__).resolve().parent

app.mount("/fastapi/admin", admin_app)  # FastApi_Admin with Tortoise
app.mount("/admin", AdminApp)  # FastApi_Admin with SQLAlchemy
app.include_router(csrf_router, prefix="/v2")
app.include_router(user_router, prefix="/v2")
app.include_router(profile_router, prefix="/v2/profile")
app.include_router(passkey_router, prefix="/v2/passkey")
app.include_router(state_router, prefix="/v2/state")
app.include_router(lga_router, prefix="/v2/lga")
app.include_router(sale_image_router, prefix="/v2/sales/images")
app.include_router(rental_upload_router, prefix="/v2/rentals/images")
app.include_router(property_image_router, prefix="/v2/properties/images")
app.include_router(property_router, prefix="/v2")
app.include_router(tenant_router, prefix="/v2/tenants")
app.include_router(sales_router, prefix="/v2/property_sales")
app.include_router(rental_router, prefix="/v2/rentals")
app.include_router(proofs_router, prefix="/v2/rent_proofs")
app.include_router(rent_receipts_router, prefix="/v2/rent_receipts")
app.include_router(cloudinary_router, prefix="/v2")
app.include_router(sales_chat_router, prefix="/v2")
app.include_router(sales_message_router, prefix="/v2/sales")
app.include_router(rental_message_router, prefix="/v2/rental")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
async def index():
    with open("templates/index.html", "r", encoding="utf-8") as f:
        return f.read()


app.add_exception_handler(
    RequestValidationError,
    ValidationErrorHandler(),
)

app.add_middleware(ErrorHandlerMiddleware)

app.add_middleware(
    AutoLogoutMiddleware,
)

app.add_middleware(
    AutoRefreshAccessTokenMiddleware,
    secret_key=settings.SECRET_KEY,
    algorithm=settings.ALGORITHM,
    access_exp_minutes=settings.ACCESS_EXPIRE_MINUTES,
    secure_cookies=settings.SECURE_COOKIES,
    skip_paths={
        "/docs",
        "/redoc",
        "/openapi.json",
        "/logout",
        "/api/auth/logout",
        "/health",
        "/static",
    },
)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001, reload=True)
