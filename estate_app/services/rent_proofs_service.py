import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import HTTPException

from core.breaker import breaker
from core.cache import cache
from core.check_permission import CheckRolePermission
from core.cloudinary_setup import CloudinaryClient
from core.delete_token import DeleteTokenGenerator
from core.event_publish import publish_event
from core.file_hash import ComputeFileHash
from core.mapper import ORMMapper
from core.paginate import PaginatePage
from models.enums import RENT_PAYMENT_STATUS
from repos.property_repo import PropertyRepo
from repos.rent_payment_repo import RentReceiptRepo
from repos.rent_proofs_repo import PaymentProofRepo
from repos.tenant_repo import TenantRepo
from schemas.schema import RentProofOut

MAX_DAILY_UPLOADS = 1


class RentProofService:
    MINIMUM_RENT_RATIO = 0.5

    def __init__(self, db):
        self.repo: PaymentProofRepo = PaymentProofRepo(db)
        self.property_repo = PropertyRepo(db)
        self.cloudinary: CloudinaryClient = CloudinaryClient()
        self.paginate: PaginatePage = PaginatePage()
        self.compute: ComputeFileHash = ComputeFileHash()
        self.token_delete: DeleteTokenGenerator = DeleteTokenGenerator()
        self.tenant_repo: TenantRepo = TenantRepo(db)
        self.mapper: ORMMapper = ORMMapper()
        self.permission: CheckRolePermission = CheckRolePermission()
        self.rent_receipt_repo:RentReceiptRepo=RentReceiptRepo(db)

    def validate_amount(self, existing_receipt, tenant, amount):
        if not existing_receipt:
            min_amount =tenant.rent_amount * self.MINIMUM_RENT_RATIO
            if amount <= min_amount:
                raise HTTPException(
                    400,
                    "First payment must be more than half of rent amount",
                )

           
            if amount > tenant.rent_amount:
                raise HTTPException(
                    400,
                    "Amount cannot exceed total rent",
                )

        else:
            balance = (existing_receipt.expected_amount - existing_receipt.amount_paid)

            if amount > balance:
                raise HTTPException(
                    400,
                    "Amount cannot exceed outstanding balance",
                )

            if amount <= 0:
                raise HTTPException(400, "Invalid amount")
        return amount

    async def enforce_daily_quota(self, user_id: uuid.UUID):
        today_start = (
            datetime.now(timezone.utc)
            .replace(hour=0, minute=0, second=0, microsecond=0)
            .replace(tzinfo=None)
        )
        tomorrow = today_start + timedelta(days=1)

        count = await self.repo.count_user_uploads_between(
            user_id=user_id,
            start=today_start,
            end=tomorrow,
        )

        if count >= MAX_DAILY_UPLOADS:
            raise HTTPException(status_code=429, detail="Daily upload limit reached")

    async def get_my_proof(self, current_user, proof_id: uuid.UUID):
        async def handler():
            user_id = current_user.id
            await self.permission.check_authenticated(current_user=current_user)
            cache_key = f"rent_proof:{user_id}:{proof_id}"
            cached = await cache.get_json(cache_key)
            if cached:
                return cached
            proof = await self.repo.get_one_by_user(proof_id=proof_id, user_id=user_id)

            if not proof:
                raise HTTPException(
                    status_code=404,
                    detail="Payment proof not found",
                )
            proof_dict = self.mapper.one(proof, RentProofOut)
            await cache.set_json(
                cache_key,
                self.paginate.get_single_json_dumps(proof_dict),
                ttl=300,
            )
            return proof_dict

        return await breaker.call(handler)

    async def get_all_for_landlord(
        self, current_user, page: int = 1, per_page: int = 20
    ):
        async def handler():
            user_id = current_user.id
            await self.permission.check_authenticated(current_user=current_user)
            cache_key = f"rent_proofs:landlord:{user_id}:page{page}:per_page{per_page}"
            cached = await cache.get_json(cache_key)
            if cached:
                return cached
            proofs = await self.repo.get_all_for_landlord(user_id)
            proofs_dicts = self.mapper.many(items=proofs, schema=RentProofOut)
            paginated_files = self.paginate.paginate(proofs_dicts, page, per_page)
            await cache.set_json(
                cache_key,
                self.paginate.get_list_json_dumps(paginated_props=paginated_files),
                ttl=300,
            )
            return paginated_files

        return await breaker.call(handler)

    async def get_all_for_property(
        self, current_user, property_id: uuid.UUID, page: int = 1, per_page: int = 20
    ):
        async def handler():
            user_id = current_user.id
            await self.permission.check_authenticated(current_user=current_user)
            cache_key = f"rent_proofs:landlord:{user_id}:{property_id}:page{page}:per_page{per_page}"
            cached = await cache.get_json(cache_key)
            if cached:
                return cached
            proofs = await self.repo.get_all_for_property(
                property_id=property_id, landlord_id=user_id
            )
            proofs_dicts = self.mapper.many(items=proofs, schema=RentProofOut)
            paginated_files = self.paginate.paginate(proofs_dicts, page, per_page)
            await cache.set_json(
                cache_key,
                self.paginate.get_list_json_dumps(paginated_props=paginated_files),
                ttl=300,
            )
            return paginated_files

        return await breaker.call(handler)

    async def get_one_for_landlord(self, current_user, proof_id: uuid.UUID):
        async def handler():
            user_id = current_user.id
            await self.permission.check_authenticated(current_user=current_user)
            cache_key = f"rent_proofs:landlord:{user_id}:{proof_id}"
            cached = await cache.get_json(cache_key)
            if cached:
                return cached
            proof = await self.repo.get_one_for_landlord(
                proof_id=proof_id,
                landlord_id=user_id,
            )
            if not proof:
                raise HTTPException(
                    status_code=404,
                    detail="Payment proof not found or access denied",
                )
            proof_dict = self.mapper.one(proof, RentProofOut)
            await cache.set_json(
                cache_key,
                self.paginate.get_single_json_dumps(proof_dict),
                ttl=300,
            )
            return proof_dict

        return await breaker.call(handler)

    async def get_all_files(self, current_user, page: int = 1, per_page: int = 20):
        async def handler():
            user_id = current_user.id
            await self.permission.check_authenticated(current_user=current_user)
            cache_key = f"rent_proofs:all:{user_id}:files::page:{page}:per:{per_page}"
            cached = await cache.get_json(cache_key)
            if cached:
                return cached
            files = await self.repo.get_all(user_id)
            file_dicts = self.mapper.many(items=files, schema=RentProofOut)
            paginated_files = self.paginate.paginate(file_dicts, page, per_page)
            await cache.set_json(
                cache_key,
                self.paginate.get_list_json_dumps(paginated_props=paginated_files),
                ttl=300,
            )
            return paginated_files

        return await breaker.call(handler)

    async def get_single_file(
        self,
        current_user,
    ):
        async def handler():
            user_id = current_user.id
            await self.permission.check_authenticated(current_user=current_user)
            cache_key = f"rent_proofs:{user_id}:files"
            cached = await cache.get_json(cache_key)
            if cached:
                return self.mapper.one(item=cached, schema=RentProofOut)
            files = await self.repo.get_single(user_id)
            if not files:
                raise HTTPException(404, detail="File not Found")
            file_base = self.mapper.one(item=files, schema=RentProofOut)

            await cache.set_json(
                cache_key,
                self.paginate.get_single_json_dumps(file_base),
                ttl=300,
            )
            return file_base

        return await breaker.call(handler)

    async def upload_file(
        self,
        *,
        public_id: str,
        file_url: str,
        property_id: uuid.UUID,
        current_user,
        amount_got,
    ):
        async def handler():
            user_id = current_user.id
            amount=amount_got
            await self.permission.check_authenticated(current_user=current_user)
            tenant = await self.tenant_repo.get_by_user(user_id)

            if not tenant:
                raise HTTPException(
                    status_code=403,
                    detail="Only tenants can upload rent payment proof",
                )

            tenant_id = tenant.id
            # property = await self.property_repo.get_by_id(property_id=property_id)
            property = await self.tenant_repo.check_tenant_property(
                tenant_id=tenant_id, property_id=property_id
            )
            if not property:
                raise HTTPException(400, "Tenant is not assigned to this property")
            existing_receipt = await self.rent_receipt_repo.get_unpaid_receipt_for_tenant(tenant_id)
            await self.enforce_daily_quota(user_id=user_id)
            count = await self.repo.count_for_listing(property_id)

            if count >= 3:
                raise HTTPException(
                    status_code=400, detail="Maximum of 3 files allowed."
                )

            file_hash = await self.compute.compute_file_hash(file_url=file_url)
            existing = await self.repo.get_by_hash(property_id, file_hash)
            if existing:
                raise HTTPException(400, "This File has already been uploaded")
            
            if amount > tenant.rent_amount:
                raise HTTPException(400, "Amount can't be higher than rent amount")
            validated_amount =self.validate_amount(
                existing_receipt=existing_receipt, amount=amount, tenant=tenant
            )
            rent_created = await self.repo.create(
                tenant_id=tenant_id,
                property_id=property_id,
                public_id=public_id,
                file_hash=file_hash,
                file_url=file_url,
                created_by_id=user_id,
                status=RENT_PAYMENT_STATUS.PENDING,
                amount=Decimal(str(validated_amount)),
            )
            proof_id = rent_created.id
            created = await self.repo.get_one(rent_created.id)

            await self._cache_delete(
                proof_id=proof_id, user_id=user_id, property_id=property_id
            )
            await publish_event(
                "rent_proofs_images.created",
                {
                    "property_id": str(property_id),
                    "file_id": str(proof_id),
                    "url": created.file_path,
                },
            )

            return self.mapper.one(created, RentProofOut)

        return await breaker.call(handler)

    async def delete_file(
        self, proof_id: uuid.UUID, current_user, resource_type: str = "raw"
    ):
        async def handler():
            user_id = current_user.id
            await self.permission.check_authenticated(current_user=current_user)
            file = await self.repo.get_one(proof_id)
            property_id = file.property_id
            if not file:
                raise HTTPException(status_code=404, detail="File not found")
            if file.created_by_id != current_user.id:
                raise HTTPException(
                    status_code=403,
                    detail="You cannot delete an file you didn't create",
                )
            token = await self.token_delete.generate_token(image_id=str(file.id))

            validated_token = await self.token_delete.validate_token(
                image_id=str(file.id), token=token
            )

            if not validated_token:
                raise HTTPException(403, detail="Invalid delete token")

            await self.cloudinary.safe_delete_cloudinary(
                public_id=file.public_id, resource_type=resource_type
            )
            await self.repo.delete_one(proof_id)
            await self._cache_delete(
                proof_id=proof_id, user_id=user_id, property_id=property_id
            )

            return {"deleted": True, "id": str(file.id)}

        return await breaker.call(handler)

    async def _cache_delete(
        self, user_id: uuid.UUID, proof_id: uuid.UUID, property_id: uuid.UUID
    ):
        await cache.delete_cache_keys_async(
            f"rent_proofs:{property_id}:files",
            f"rent_proofs:all:{user_id}:files",
            f"rent_proofs:{user_id}:files",
            f"rent_proof:{user_id}:{proof_id}",
            f"rent_proofs:landlord:{user_id}",
            f"rent_proofs:landlord:{user_id}:{proof_id}",
            f"rent_proofs:landlord:{user_id}:{property_id}",
        )
