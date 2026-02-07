
from typing import List


from core.get_db import get_db_async
from core.safe_handler import safe_handler
from core.throttling import rate_limit
from core.validators import validate_csrf_dependency
from fastapi import APIRouter, Depends
from fastapi_utils.cbv import cbv

from schemas.schema import (
   BankOut
)
from services.bank_service import BankService
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["Banks"])


@cbv(router=router)
class BanksRoutes:
    @router.get(
        "/banks/all",
        dependencies=[rate_limit],
        response_model=List[BankOut],
    )
    @safe_handler
    async def get_all(
        self,
        page: int = 1,
        per_page: int = 20,
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await BankService(db).get_banks(page, per_page)
    @router.get(
        "/banks",
        dependencies=[rate_limit],
        response_model=List[BankOut],
    )
    @safe_handler
    async def get_all_banks(
        self,
        
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await BankService(db).get_all_banks()
