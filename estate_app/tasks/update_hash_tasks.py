import asyncio
import logging
import uuid

import httpx
from core.get_db import AsyncSessionLocal


from sqlalchemy.ext.asyncio import AsyncSession


logger = logging.getLogger("nin.youverify")


def update_hash_tasks(app):
    class UpdateHashTask(app.Task):
        

        autoretry_for = (RuntimeError, ConnectionError, httpx.HTTPError)
        retry_backoff = True
        retry_jitter = True
        max_retries = 3
        default_retry_delay = 10

        def _run_async(self, coro):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(coro)
            finally:
                loop.close()

        async def _update_hash(
            self,
            Repo,
            session: AsyncSession,
            profile_id: uuid.UUID,
            user_id: uuid.UUID,
            profile_pic_path: str,
            public_id: str,
        ):
            repo = Repo(session)

            repo = session
            new_hash = await self.compute.compute_file_hash_sync(profile_pic_path)

            existing = await repo.get_by_hash(user_id, new_hash)
            try:
                if existing and existing.id != profile_id:
                    await self.cloudinary.safe_delete_cloudinary(public_id, "images")
                    await repo.delete(user_id, profile_id)
                    await repo.db_commit()
                    return

                # store hash
                await repo.update_hash(profile_id, user_id, new_hash)
                await repo.db_commit()

            except Exception:
                await self.cloudinary.safe_delete_cloudinary(public_id, "images")

        def run(
            self,
            profile_id: uuid.UUID,
            profile_id: uuid.UUID,
            profile_pic_path: str,
            public_id: str,
            user_id:uuid.UUID
        ):
            async def _runner():
                async with AsyncSessionLocal() as session:
                    await self._update_hash(
                        session=session,
                        profile_id=profile_id,
                        profile_pic_path=profile_pic_path,
                        public_id=public_id
                        user_id=user_id
                    )

            return self._run_async(_runner())

    return UpdateHashTask
