import uuid

from fastapi import APIRouter, Depends
from fastapi_utils.cbv import cbv
from sqlalchemy.ext.asyncio import AsyncSession

from core.get_current_user import get_current_user
from core.get_db import get_db_async
from core.safe_handler import safe_handler
from core.throttling import rate_limit
from core.validators import validate_csrf_dependency
from models.models import User
from services.lga_service import LGAService

router = APIRouter(tags=["LGA"])


@cbv(router)
class LGARoutes:
    @router.post("/create", dependencies=[rate_limit])
    @safe_handler
    async def create_state(
        self,
        name: str,
        state_id: uuid.UUID,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await LGAService(db).create(
            name=name, state_id=state_id, current_user=current_user
        )

    @router.post("/{state_id}/update", dependencies=[rate_limit])
    @safe_handler
    async def update_state(
        self,
        lga_id: uuid.UUID,
        name: str,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await LGAService(db).update_lga(
            name=name, lga_id=lga_id, current_user=current_user
        )

    @router.delete("/{name}/delete", dependencies=[rate_limit])
    @safe_handler
    async def delete(
        self,
        name: str,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await LGAService(db).delete_lga(name=name, current_user=current_user)

    @router.get("/get", dependencies=[rate_limit])
    @safe_handler
    async def get_lga(
        self,
        name: str,
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
        current_user: User = Depends(get_current_user),
    ):
        return await LGAService(db).get_lga_by_name(
            name=name, current_user=current_user
        )

    @router.get("/all", dependencies=[rate_limit])
    @safe_handler
    async def get_all_lgas(
        self,
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
        current_user: User = Depends(get_current_user),
        page: int = 1,
        per_page: int = 20,
    ):
        return await LGAService(db).get_all_lgas_with_states(
            current_user=current_user, page=page, per_page=per_page
        )
