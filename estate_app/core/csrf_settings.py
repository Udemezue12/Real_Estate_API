from fastapi_csrf_protect import CsrfProtect
from pydantic import BaseModel
from .settings import settings


class CsrfSettings(BaseModel):
    secret_key: str | None = settings.SECRET_KEY
    cookie_secure: bool = True
    cookie_samesite: str = "lax"
    cookie_http_only: bool = True
    csrf_token_name: str = "csrf_token"


@CsrfProtect.load_config
def get_csrf_config():
    return CsrfSettings()
