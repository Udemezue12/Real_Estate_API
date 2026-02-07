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
from schemas.schema import RentPoofSchema, RentProofOut
from services.rent_proofs_service import RentProofService

router = APIRouter(tags=["Rent Payment Proofs"])


@cbv(router)
class RentProofRoutes:
    @router.post("/upload", dependencies=[rate_limit], response_model=RentProofOut)
    @safe_handler
    async def upload(
        self,
        data: RentPoofSchema,
        db: AsyncSession = Depends(get_db_async),
        current_user: User = Depends(get_current_user),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await RentProofService(db).upload_file(
            file_url=data.secure_url,
            public_id=data.public_id,
            current_user=current_user,
            property_id=data.property_id,
            amount_got=data.amount_paid
        )

    @router.delete("/{proof_id}/delete", dependencies=[rate_limit])
    @safe_handler
    async def delete_image(
        self,
        proof_id: uuid.UUID,
        current_user=Depends(get_current_user),
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await RentProofService(db).delete_file(
            proof_id=proof_id,
            current_user=current_user,
        )

    @router.get(
        "/{proof_id}/get", dependencies=[rate_limit], response_model=RentProofOut
    )
    @safe_handler
    async def get_my_proof(
        self,
        proof_id: uuid.UUID,
        current_user=Depends(get_current_user),
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await RentProofService(db).get_my_proof(
            proof_id=proof_id,
            current_user=current_user,
        )

    @router.get(
        "/landlord/get/proofs", dependencies=[rate_limit], response_model=list[RentProofOut]
    )
    @safe_handler
    async def get__all_for_landlord(
        self,
        page: int = 1,
        per_page: int = 20,
        current_user=Depends(get_current_user),
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await RentProofService(db).get_all_for_landlord(
            current_user=current_user, page=page, per_page=per_page
        )

    @router.get(
        "/{proof_id}/landlord/get",
        dependencies=[rate_limit],
        response_model=RentProofOut,
    )
    @safe_handler
    async def get_one_for_landlord(
        self,
        proof_id: uuid.UUID,
        current_user=Depends(get_current_user),
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await RentProofService(db).get_one_for_landlord(
            proof_id=proof_id,
            current_user=current_user,
        )

    @router.get(
        "/landlord/property/{property_id}/get",
        dependencies=[rate_limit],
        response_model=list[RentProofOut],
    )
    @safe_handler
    async def get_all_proofs_for_property(
        self,
        property_id: uuid.UUID,
        page: int = 1,
        per_page: int = 20,
        current_user=Depends(get_current_user),
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await RentProofService(db).get_all_for_property(
            page=page,
            per_page=per_page,
            current_user=current_user,
            property_id=property_id,
        )

    @router.get(
        "/files/get/all", dependencies=[rate_limit], response_model=list[RentProofOut]
    )
    @safe_handler
    async def get_all_files(
        self,
        page: int = 1,
        per_page: int = 20,
        current_user=Depends(get_current_user),
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await RentProofService(db).get_all_files(
            current_user=current_user, page=page, per_page=per_page
        )

    # @router.get("/file/get", dependencies=[rate_limit], response_model=RentProofOut)
    # @safe_handler
    # async def get_file(
    #     self,
    #     page: int = 1,
    #     per_page: int = 20,
    #     current_user=Depends(get_current_user),
    #     db: AsyncSession = Depends(get_db_async),
    #     _: None = Depends(validate_csrf_dependency),
    # ):
    #     return await RentProofService(db).get_single_file(
    #         current_user=current_user, page=page, per_page=per_page
    #     )
