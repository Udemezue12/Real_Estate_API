import asyncio
from datetime import datetime
import httpx
from PIL import Image
from io import BytesIO
import os

from sqlalchemy import insert
from core.get_db import AsyncSessionLocal as async_session
from models.models import SaleListingImage
from typing import Optional


class FileProcessingTasks:
    @staticmethod
    def register_tasks(app):
        app.task(name="process_file", bind=True)(FileProcessingTasks.process_file)
        app.task(
            name="post_process_file", bind=True, max_retries=3, default_retry_delay=10
        )(FileProcessingTasks.post_process_file)
        app.task(name="send_notification", bind=True)(
            FileProcessingTasks.send_notification
        )

    @staticmethod
    def send_notification(
        self, listing_id: str, url: str, message: Optional[str] = None
    ):
        try:
            notification_msg = (
                message or f"File processed for listing {listing_id}: {url}"
            )
            # Here you would integrate with your notification system (email, push, SMS)
            print(f"[NOTIFICATION] {notification_msg}")
        except Exception as e:
            print(f"[WARN] Failed to send notification: {e}")

    @staticmethod
    def post_process_file(self, url: str, listing_id: str):
        async def _post_process():
            start_time = datetime.now(timezone.utc)

            print(f"[{start_time.isoformat()}] Starting post-processing: {url}")

            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.get(url)
                    resp.raise_for_status()

                def generate_thumbnail():
                    img = Image.open(BytesIO(resp.content))
                    img.thumbnail((400, 400))
                    save_path = f"/tmp/thumb_{os.path.basename(url)}"
                    img.save(save_path)
                    return save_path

                thumbnail_path = asyncio.run(asyncio.to_thread(generate_thumbnail))
                print(f"[INFO] Thumbnail saved at {thumbnail_path}")

                # 2️⃣ Save thumbnail path to DB
                async with async_session() as session:
                    image_entry = await session.get(SaleListingImage, listing_id)
                    if image_entry:
                        image_entry.thumbnail_path = thumbnail_path
                        await session.commit()
                        print(
                            f"[INFO] DB updated with thumbnail for listing {listing_id}"
                        )

                FileProcessingTasks.send_notification(
                    self, listing_id=listing_id, url=url
                )

            except Exception as e:
                print(f"[ERROR] Post-processing failed for {url}: {e}")
                raise self.retry(exc=e)

            end_time = datetime.now(timezone.utc)

            print(f"[{end_time.isoformat()}] Finished post-processing: {url}")
            return True

        return asyncio.run(_post_process())

    @staticmethod
    def process_file(self, url: str, listing_id: str):
        async def _process():
            print(f"[{datetime.now(timezone.utc).isoformat()}] Processing file: {url}")

            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    head = await client.head(url)
                    if head.status_code != 200:
                        print(f"[WARN] File {url} returned status {head.status_code}")
                        return False
                    print(f"[INFO] File exists: {url}")
            except Exception as e:
                print(f"[ERROR] Could not access file {url}: {e}")
                return False

            save_path = None
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(url)
                    response.raise_for_status()

                    def resize_image():
                        img = Image.open(BytesIO(response.content))
                        img.thumbnail((800, 800))
                        save_path_local = f"/tmp/processed_{os.path.basename(url)}"
                        img.save(save_path_local)
                        return save_path_local, len(response.content)

                    save_path, size_bytes = await asyncio.to_thread(resize_image)
                    print(f"[INFO] Image resized: {save_path}")
            except Exception as e:
                print(f"[WARN] Failed to resize image: {e}")

            try:
                async with async_session() as session:
                    stmt = (
                        insert(SaleListingImage)
                        .values(
                            listing_id=listing_id,
                            image_path=url,
                            uploaded_at=datetime.now(timezone.utc),
                        )
                        .returning(SaleListingImage.id)
                    )
                    result = await session.execute(stmt)
                    await session.commit()
                    image_id = result.scalar_one()
                    print(f"[INFO] Metadata saved with ID {image_id}")
            except Exception as e:
                print(f"[ERROR] Failed to save metadata: {e}")

            try:
                self.app.send_task("post_process_file", args=(url, listing_id))
                print(f"[INFO] Queued post_process_file task for {url}")
            except Exception as e:
                print(f"[WARN] Failed to queue post_process_file task: {e}")

            return True

        return asyncio.run(_process())
