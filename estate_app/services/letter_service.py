import uuid
from typing import Optional

from fastapi import HTTPException
from celery_worker.celery_app import app as task_app
from core.breaker import CircuitBreaker
from core.cache import Cache
from core.event_publish import publish_event
from core.file_hash import ComputeFileHash
from core.mapper import ORMMapper
from core.paginate import PaginatePage
from core.redis_idempotency import RedisIdempotency
from repos.letters_repo import LetterRepo
from repos.property_repo import PropertyRepo
from repos.tenant_repo import TenantRepo
from schemas.schema import (
    LetterRecipientOut,
    LetterSchemaOut,
)
from services.property_service import PropertyService


class LetterService:
    BULK_PDF_LOCK = "bulk-pdf-letter-lock-v2"
    PDF_LOCK = "pdf-letter-lock-v2"
    TEXT_LOCK = "txt-letter-lock-v2"
    BULK_TEXT_LOCK = "bulk-txt-letter-lock-v2"

    def __init__(self, db):
        self.repo: LetterRepo = LetterRepo(db)
        self.tenant_repo: TenantRepo = TenantRepo(db)
        self.property_repo: PropertyRepo = PropertyRepo(db)
        self.cache: Cache = Cache()
        self.mapper: ORMMapper = ORMMapper()
        self.redis_idempotency: RedisIdempotency = RedisIdempotency(
            namespace="letter-service-v2"
        )
        self.paginate: PaginatePage = PaginatePage()
        self.compute: ComputeFileHash = ComputeFileHash()
        self.property_service: PropertyService = PropertyService(db)
        self.breaker = CircuitBreaker()

    async def get_managed_by_id(self, property):
        managed_by_id = (
            property.managed_by_id if property.managed_by_id is not None else property.owner_id
        )
        return managed_by_id

    async def send_letter_without_pdf_upload(
        self, current_user, tenant_id: uuid.UUID, property_id: uuid.UUID, data
    ):
        async def _sync():
            user_id = current_user.id
            property = await self.property_repo.get_property_with_id(
                property_id=property_id
            )
            if not property:
                raise HTTPException(400, "Property does not exist")

            tenant = await self.tenant_repo.check_tenant_property(
                property_id=property_id, tenant_id=tenant_id
            )
            if not tenant:
                raise HTTPException(400, "Tenant is not assigned to this property")
            if not tenant.matched_user_verified:
                raise HTTPException(400, "Tenant not matched yet")

            managed_by_id = await self.get_managed_by_id(property=property)
            letter = await self.repo.create_without_upload(
                sender_id=user_id,
                property_id=property_id,
                caretaker_id=managed_by_id,
                owner_id=property.owner_id,
                letter_type=data.letter_type,
                title=data.title,
                body=data.body,
            )
            await self.repo.db_commit()
            task_app.send_task(
                name="send_single_letter",
                args=[
                    str(tenant_id),
                    str(letter.id),
                    str(property_id),
                ],
            )
            await publish_event(
                "letter.created",
                {
                    "tenant_id": str(tenant_id),
                    "property_id": str(property_id),
                },
            )

            return {"status": "OK", "message": "Letter sent successfully"}

        return await self.redis_idempotency.run_once(
            key=self.TEXT_LOCK, coro=_sync, ttl=120
        )

    async def send_letter_with_pdf(
        self, current_user, tenant_id: uuid.UUID, property_id: uuid.UUID, data
    ):
        async def _sync():
            user_id = current_user.id
            property = await self.property_repo.get_property_with_id(
                property_id=property_id
            )
            if not property:
                raise HTTPException(400, "Property does not exist")

            tenant = await self.tenant_repo.check_tenant_property(
                property_id=property_id, tenant_id=tenant_id
            )
            if not tenant:
                raise HTTPException(400, "Tenant is not assigned to this property")
            if not tenant.matched_user_verified:
                raise HTTPException(400, "Tenant not matched yet")

            file_hash = await self.compute.compute_file_hash(file_url=data.file_url)
            existing = await self.repo.get_by_hash(
                property_id=property_id, file_hash=file_hash
            )
            if existing:
                raise HTTPException(400, "This file has already been uploaded")
            managed_by_id = await self.get_managed_by_id(property=property)
            letter = await self.repo.create_with_upload(
                sender_id=user_id,
                property_id=property_id,
                caretaker_id=managed_by_id,
                owner_id=property.owner_id,
                letter_type=data.letter_type,
                title=data.title,
                file_path=data.file_path,
                file_hash=file_hash,
                public_id=data.public_id,
            )
            await self.repo.db_commit()

            
            task_app.send_task(
                name="send_single_letter",
                args=[
                    str(tenant_id),
                    str(letter.id),
                    str(property_id),
                ],
            )

            await publish_event(
                "letter.created",
                {
                    "tenant_id": str(tenant_id),
                    "property_id": str(property_id),
                },
            )

            return {"status": "OK", "message": "Letter sent successfully"}

        return await self.redis_idempotency.run_once(
            key=self.PDF_LOCK, coro=_sync, ttl=120
        )

    async def send_bulk_letters_with_pdf(
        self, current_user, property_id: uuid.UUID, data
    ):
        async def _sync():
            user_id = current_user.id
            property = await self.property_repo.get_property_with_id(
                property_id=property_id
            )
            if not property:
                raise HTTPException(400, "Property does not exist")
            tenant_ids = await self.tenant_repo.get_all_tenants_ids(property_id=property_id)
            print(f"Tenant IDS:{tenant_ids}")
            if not tenant_ids:
                return []

            managed_by_id = await self.get_managed_by_id(property=property)
            file_hash = await self.compute.compute_file_hash(file_url=data.file_url)
            existing = await self.repo.get_by_hash(
                property_id=property_id, file_hash=file_hash
            )
            if existing:
                raise HTTPException(400, "This file has already been uploaded")
            letter = await self.repo.create_with_upload(
                sender_id=user_id,
                property_id=property_id,
                caretaker_id=managed_by_id,
                owner_id=property.owner_id,
                letter_type=data.letter_type,
                title=data.title,
                file_path=data.file_path,
                file_hash=file_hash,
                public_id=data.public_id,
            )
            await self.repo.db_commit()

            task_app.send_task(
                name="send_bulk_letters",
                args=[
                    str(property_id),
                    str(letter.id),
                    tenant_ids,
                ],
            )
            await publish_event(
                "bulk_letters_with_pdf.created",
                {
                    "property_id": str(property_id),
                },
            )

            return {"status": "OK", "message": "Letter sent successfully"}

        return await self.redis_idempotency.run_once(
            key=self.BULK_PDF_LOCK, coro=_sync, ttl=120
        )

    async def send_bulk_letters_without_pdf(
        self, current_user, property_id: uuid.UUID, data
    ):
        async def _sync():
            user_id = current_user.id
            tenant_ids = await self.tenant_repo.get_all_tenants_ids(property_id=property_id)
            print(f"Tenant IDS:{tenant_ids}")
            if not tenant_ids:
                return []
            property = await self.property_repo.get_property_with_id(
                property_id=property_id
            )
            if not property:
                raise HTTPException(400, "Property does not exist")
            managed_by_id = await self.get_managed_by_id(property=property)

            letter = await self.repo.create_without_upload(
                sender_id=user_id,
                property_id=property_id,
                caretaker_id=managed_by_id,
                owner_id=property.owner_id,
                letter_type=data.letter_type,
                title=data.title,
                body=data.body,
            )
            await self.repo.db_commit()

            task_app.send_task(
                name="send_bulk_letters",
                args=[str(property_id), str(letter.id), tenant_ids],
            )
            await publish_event(
                "bulk_letters.created",
                {
                    "property_id": str(property_id),
                },
            )

            return {"status": "OK", "message": "Letter sent successfully"}

        return await self.redis_idempotency.run_once(
            key=self.BULK_TEXT_LOCK, coro=_sync, ttl=120
        )

    async def get_all_letters_for_landlord(
        self, current_user, page: int = 1, per_page=20
    ) -> list[LetterSchemaOut]:
        async def handler():
            user_id = current_user.id
            cache_key = f"letters:{user_id}::page:{page}:per:{per_page}"
            cached = await self.cache.get_json(cache_key)
            print(f"Cached:::{cached}")
            if cached:
                return self.mapper.many(items=cached, schema=LetterSchemaOut)
            props = await self.repo.get_all_landlord_letters(user_id=user_id)
            if not props:
                return []
            props_dicts = self.mapper.many(items=props, schema=LetterSchemaOut)
            paginated_props = self.paginate.paginate(props_dicts, page, per_page)
            await self.cache.set_json(
                cache_key,
                self.paginate.get_list_json_dumps(paginated_props=paginated_props),
                ttl=300,
            )
            return paginated_props

        return await self.breaker.call(handler)

    async def get_all_properties_letters(
        self, current_user, property_id: uuid.UUID, page: int = 1, per_page=20
    ) -> list[LetterSchemaOut]:
        async def handler():
            user_id = current_user.id
            await self.property_service.check_owner(
                property_id=property_id, user_id=user_id
            )

            cache_key = (
                f"properties:{user_id}:{property_id}::page:{page}:per:{per_page}"
            )
            cached = await self.cache.get_json(cache_key)

            if cached:
                return self.mapper.many(items=cached, schema=LetterSchemaOut)
            props = await self.repo.get_all_properties_letters(
                user_id=user_id, property_id=property_id
            )
            if not props:
                return []
            props_dicts = self.mapper.many(items=props, schema=LetterSchemaOut)
            paginated_props = self.paginate.paginate(props_dicts, page, per_page)
            await self.cache.set_json(
                cache_key,
                self.paginate.get_list_json_dumps(paginated_props=paginated_props),
                ttl=300,
            )
            return paginated_props

        return await self.breaker.call(handler)

    async def get_single_letter_landlord(
        self, current_user, letter_id: uuid.UUID
    ) -> Optional[LetterSchemaOut]:
        async def handler():
            user_id = current_user.id
            if not await self.repo.get_owner_id(owner_id=user_id):
                raise HTTPException(400, "Not Allowed")
            cache_key = f"letters:{user_id}:{letter_id}"
            cached = await self.cache.get_json(cache_key)

            if cached:
                return self.mapper.one(item=cached, schema=LetterSchemaOut)
            props = await self.repo.get_single_letter_landlord(
                user_id=user_id, letter_id=letter_id
            )
            if not props:
                raise HTTPException(404, "Not found")
            props_dicts = self.mapper.one(item=props, schema=LetterSchemaOut)

            await self.cache.set_json(
                cache_key,
                self.paginate.get_single_json_dumps(props_dicts),
                ttl=300,
            )
            return props_dicts

        return await self.breaker.call(handler)

    async def get_single_property_letter(
        self, current_user, letter_id: uuid.UUID, property_id: uuid.UUID
    ) -> Optional[LetterSchemaOut]:
        async def handler():
            user_id = current_user.id
            await self.property_service.check_owner(
                property_id=property_id, user_id=user_id
            )
            if not await self.repo.get_owner_id(owner_id=user_id):
                raise HTTPException(400, "Not Allowed")
            cache_key = f"letters:{user_id}:{letter_id}:{property_id}"
            cached = await self.cache.get_json(cache_key)

            if cached:
                return self.mapper.one(item=cached, schema=LetterSchemaOut)
            props = await self.repo.get_single_property_letter(
                user_id=user_id, letter_id=letter_id, property_id=property_id
            )
            if not props:
                raise HTTPException(404, "Not found")
            props_dicts = self.mapper.one(item=props, schema=LetterSchemaOut)

            await self.cache.set_json(
                cache_key,
                self.paginate.get_single_json_dumps(props_dicts),
                ttl=300,
            )
            return props_dicts

        return await self.breaker.call(handler)

    async def get_single_letter_for_tenant(
        self, current_user, recipient_id: uuid.UUID
    ) -> Optional[LetterRecipientOut]:
        async def handler():
            user_id = current_user.id

            tenant = await self.tenant_repo.get_by_user(user_id)

            if not tenant:
                raise HTTPException(
                    status_code=403,
                    detail="Mot Allowed",
                )
            tenant_id = tenant.id
            if not await self.repo.get_recipient_letter_id(
                recipient_letter_id=recipient_id
            ):
                raise HTTPException(404, "Not found")
            cache_key = f"property:{user_id}:{recipient_id}"
            cached = await self.cache.get_json(cache_key)
            if cached:
                return self.mapper.one(cached, LetterRecipientOut)
            recipient = await self.repo.get_single_letter_tenant(
                tenant_id=tenant_id, recipient_letter_id=recipient_id
            )
            if not recipient:
                raise HTTPException(404, "Not found")
            if not recipient.is_read:
                await self.repo.update_is_read(letter_recipient_id=recipient.id)
            recipient_dict = self.mapper.one(recipient, LetterRecipientOut)
            await self.cache.set_json(
                cache_key,
                self.paginate.get_single_json_dumps(recipient_dict),
                ttl=300,
            )
            return recipient_dict

        return await self.breaker.call(handler)

    async def get_all_tenant_letters(
        self, current_user, page: int = 1, per_page=20
    ) -> list[LetterRecipientOut]:
        async def handler():
            user_id = current_user.id
            tenant = await self.tenant_repo.get_by_user(user_id)

            if not tenant:
                raise HTTPException(
                    status_code=403,
                    detail="Mot Allowed",
                )
            tenant_id = tenant.id

            cache_key = f"properties:{tenant_id}::page:{page}:per:{per_page}"
            cached = await self.cache.get_json(cache_key)

            if cached:
                return self.mapper.many(items=cached, schema=LetterRecipientOut)
            props = await self.repo.get_all_tenant_letters(tenant_id=tenant_id)
            if not props:
                return []
            props_dicts = self.mapper.many(items=props, schema=LetterRecipientOut)
            paginated_props = self.paginate.paginate(props_dicts, page, per_page)
            await self.cache.set_json(
                cache_key,
                self.paginate.get_list_json_dumps(paginated_props=paginated_props),
                ttl=300,
            )
            return paginated_props

        return await self.breaker.call(handler)
