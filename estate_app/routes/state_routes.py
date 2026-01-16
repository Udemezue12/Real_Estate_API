import uuid

from core.get_current_user import get_current_user
from core.get_db import get_db_async
from core.safe_handler import safe_handler
from core.throttling import rate_limit
from core.validators import validate_csrf_dependency
from fastapi import APIRouter, Depends
from fastapi_utils.cbv import cbv
from models.models import User
from services.state_services import StateService
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["States"])


@cbv(router)
class StateRoutes:
    @router.post("/create", dependencies=[rate_limit])
    @safe_handler
    async def create_state(
        self,
        name: str,
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await StateService(db).create_state(name=name)

    @router.post("/{state_id}/update", dependencies=[rate_limit])
    @safe_handler
    async def update_state(
        self,
        state_id: uuid.UUID,
        name: str,
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
        current_user: User = Depends(get_current_user)
    ):
        return await StateService(db).update_state(name=name, state_id=state_id, current_user=current_user)
    @router.get("/all", dependencies=[rate_limit])
    @safe_handler
    async def get_states(
        self,
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await StateService(db).get_state()
    @router.get("/all/states", dependencies=[rate_limit])
    @safe_handler
    async def get_all_states(
        self,
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await StateService(db).get_states()
    @router.delete("/{name}/delete", dependencies=[rate_limit])
    @safe_handler
    async def delete(
        self,
        name:str,
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
        current_user: User = Depends(get_current_user)
    ):
        return await StateService(db).delete_state(name=name, current_user=current_user)
