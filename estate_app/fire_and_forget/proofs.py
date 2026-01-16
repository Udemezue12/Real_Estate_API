from core.cache import cache
from core.cloudinary_setup import CloudinaryClient
import uuid

from core.event_publish import publish_event


class AsyncioRentProof:
    def __init__(self):
        self.cloudinary: CloudinaryClient = CloudinaryClient()

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

    async def delete(
        self, file, user_id: uuid.UUID, proof_id: uuid.UUID, property_id: uuid.UUID,resource_type:str
    ):
        await self.cloudinary.safe_delete_cloudinary(public_id=file.public_id, resource_type=resource_type)

        await self._cache_delete(
            proof_id=proof_id, property_id=property_id, user_id=user_id
        )

    async def upload(
        self, created, proof_id: uuid.UUID, property_id: uuid.UUID, user_id: uuid.UUID, 
    ):
        await self._cache_delete(
            proof_id=proof_id, property_id=property_id, user_id=user_id
        )
        await publish_event(
            "rent_proofs_images.created",
            {
                "property_id": str(property_id),
                "file_id": str(proof_id),
                "url": created.file_path,
            },
        )
