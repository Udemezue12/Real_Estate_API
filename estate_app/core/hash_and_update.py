import uuid
import asyncio
from core.get_db import AsyncSessionLocal
from core.file_hash import ComputeFileHash
from core.cloudinary_setup import CloudinaryClient

class AsyncioHashAndUpdate:
    async def hash_and_dedupe_profile_pic(
        self,
        Repo,
        profile_id: uuid.UUID,
        user_id: uuid.UUID,
        profile_pic_path: str,
        public_id: str,
    ):
        compute_file_hash = ComputeFileHash()
        cloudinary=CloudinaryClient()
        try:
            
            loop = asyncio.get_running_loop()
            new_hash = await loop.run_in_executor(
                None,
                compute_file_hash.compute_file_hash_sync,
                profile_pic_path,
            )

            async with AsyncSessionLocal() as db:
                repo = Repo(db)

                existing = await repo.get_by_hash(user_id, new_hash)

                if existing and existing.id != profile_id:
                    
                    await cloudinary.safe_delete_cloudinary(public_id, "images")
                    await repo.delete(user_id, profile_id)
                    await repo.db_commit()
                    return

                
                await repo.update_hash(profile_id, user_id, new_hash)
                await repo.db_commit()

        except Exception:
            await cloudinary.safe_delete_cloudinary(public_id, "images")
