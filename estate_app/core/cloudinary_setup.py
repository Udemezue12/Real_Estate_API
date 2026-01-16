import time, asyncio
import uuid
from pathlib import Path

import cloudinary
import cloudinary.api
import cloudinary.uploader
from cloudinary.utils import api_sign_request, private_download_url
from fastapi import HTTPException

from core.settings import settings

MAX_FILE_SIZE = 5 * 1024 * 1024


class CloudinaryClient:
    def __init__(self):
        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_SECRET_KEY,
            secure=True,
        )

    async def validate_signature_timestamp(
        self, timestamp: int, *, ttl_seconds: int = 30
    ) -> None:
        now = int(time.time())
        if not isinstance(timestamp, int):
            raise HTTPException(status_code=400, detail="Invalid timestamp fprmat")
        if now - timestamp > ttl_seconds:
            raise HTTPException(
                status_code=400,
                detail=f"The provided timestamp is expired or too old (limit is {ttl_seconds} seconds).",
            )

        if timestamp > now + 5:
            raise HTTPException(
                status_code=400,
                detail="The provided timestamp is in the future.",
            )

    async def connect(self) -> bool:
        try:
            info = cloudinary.api.ping()
            return info.get("status") == "ok"
        except Exception as e:
            raise HTTPException(500, f"Cloudinary connection failed: {e}")

    async def get_image_signed_upload_params(
        self,
        folder: str = "uploads",
        file_size: int | None = None,
        file_name: str | None = None,
    ) -> dict:
        try:
            if file_size is not None:
                if file_size > MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=400,
                        detail=f"File '{file_name or 'unknown'}' exceeds maximum allowed size.",
                    )

            allowed_formats = ["jpg", "jpeg", "png", "webp"]

            timestamp = int(time.time())
            await self.validate_signature_timestamp(timestamp=timestamp, ttl_seconds=30)

            eager = "f_auto,q_auto"

            params_to_sign = {
                "timestamp": timestamp,
                "folder": folder,
                "eager": eager,
                # "resource_type": "image",
            }

            signature = api_sign_request(
                params_to_sign,
                cloudinary.config().api_secret,
            )

            return {
                "signature": signature,
                "timestamp": timestamp,
                "api_key": cloudinary.config().api_key,
                "folder": folder,
                "max_file_size": MAX_FILE_SIZE,
                "eager": eager,
                "allowed_formats": allowed_formats,
                "cloud_name": cloudinary.config().cloud_name,
            }

        except Exception as e:
            raise HTTPException(
                500,
                f"Failed to generate upload signature: {e}",
            )

    async def get_signed_multiple_upload_params(
        self,
        count: int,
        folder: str = "uploads",
    ) -> list[dict]:
        try:
            signed_payloads: list[dict] = []
            for _ in range(count):
                allowed_formats = ["jpg", "jpeg", "png", "webp"]

                timestamp = int(time.time())
                await self.validate_signature_timestamp(
                    timestamp=timestamp, ttl_seconds=30
                )

                eager = "f_auto,q_auto"

                params_to_sign = {
                    "timestamp": timestamp,
                    "folder": folder,
                    "eager": eager,
                }

                signature = api_sign_request(
                    params_to_sign,
                    cloudinary.config().api_secret,
                )

                signed_payloads.append(
                    {
                        "signature": signature,
                        "timestamp": timestamp,
                        "api_key": cloudinary.config().api_key,
                        "folder": folder,
                        "max_file_size": MAX_FILE_SIZE,
                        "eager": eager,
                        "allowed_formats": allowed_formats,
                        "cloud_name": cloudinary.config().cloud_name,
                        "resource_type": "image",
                    }
                )
            return signed_payloads

        except Exception as e:
            raise HTTPException(
                500,
                f"Failed to generate upload signature: {e}",
            )

    async def get_signed_video_upload_params(self, folder: str = "videos") -> dict:
        try:
            timestamp = int(time.time())
            allowed_formats = ["mp4", "webm", "mov"]

            params_to_sign = {
                "timestamp": timestamp,
                "folder": folder,
                "resource_type": "video",
            }

            signature = cloudinary.utils.api_sign_request(
                params_to_sign,
                cloudinary.config().api_secret,
            )

            return {
                "signature": signature,
                "timestamp": timestamp,
                "api_key": cloudinary.config().api_key,
                "cloud_name": cloudinary.config().cloud_name,
                "folder": folder,
                "resource_type": "video",
                # FRONTEND VALIDATION ONLY
                "allowed_formats": allowed_formats,
                "max_file_size": MAX_FILE_SIZE,  # 50MB
                "max_duration": 60,  # frontend check only
            }

        except Exception as e:
            raise HTTPException(500, f"Failed to generate video upload signature: {e}")

    async def get_pdf_signed_upload_params(
        self,
        *,
        folder: str = "receipts",
        public_id: str | None = None,
    ) -> dict:
        try:
            timestamp = int(time.time())
            await self.validate_signature_timestamp(timestamp=timestamp)

            params_to_sign = {
                "timestamp": timestamp,
                "folder": folder,
            }
            if public_id:
                params_to_sign["public_id"] = public_id

            signature = api_sign_request(
                params_to_sign,
                cloudinary.config().api_secret,
            )

            return {
                "signature": signature,
                "timestamp": timestamp,
                "api_key": cloudinary.config().api_key,
                "cloud_name": cloudinary.config().cloud_name,
                "folder": folder,
                "resource_type": "raw",
                "allowed_formats": ["pdf"],
                "max_file_size": MAX_FILE_SIZE,
            }
        except Exception as e:
            raise HTTPException(
                500,
                f"Failed to generate upload signature: {e}",
            )

    async def upload_pdf_with_signature(
        self,
        file_path: Path | None,
        folder: str = "receipts",
        public_id: str | None = None,
    ) -> dict:
        if not file_path or not file_path.exists():
            raise HTTPException(500, "Generated PDF file not found")

        try:
            result = cloudinary.uploader.upload(
                str(file_path),
                resource_type="raw",
                folder=folder,
                public_id=public_id,
            )
            return result

        except Exception as e:
            raise HTTPException(500, f"Signed PDF upload failed: {e}")

    async def delete_image(self, public_id: str, resource_type:str) -> dict:
        try:
            return cloudinary.uploader.destroy(
                public_id, resource_type=resource_type, invalidate=True
            )
        except Exception as e:
            raise HTTPException(500, f"Failed to delete image: {e}")

    async def delete_images(self, public_ids: list[str], resource_type:str) -> dict:
        if not public_ids:
            raise HTTPException(status_code=400, detail="No public_ids provided")

        try:
            loop = asyncio.get_running_loop()

            result = await loop.run_in_executor(
                None,
                lambda: cloudinary.api.delete_resources(public_ids, resource_type=resource_type, invalidate=True),
            )

            return {
                "deleted": result.get("deleted"),
                "partial": result.get("partial"),
                "raw": result,
            }

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to delete images: {str(e)}",
            )

    async def generate_delete_token(
        self,
        image_id: uuid.UUID,
        public_id: str,
        expires_in: int = 300,
    ) -> str:
        payload = f"{image_id}:{public_id}:{int(time.time()) + expires_in}"
        return api_sign_request(
            {"payload": payload},
            cloudinary.config().api_secret,
        )

    def generate_signed_pdf_url(self, public_id: str, expires_in: int = 300) -> str:
        return private_download_url(
            public_id,
            resource_type="raw",
            format=None,
            expires_in=expires_in,
        )

    async def resource_exists(self, public_id: str, resource_type: str = "raw") -> bool:
        try:
            info = cloudinary.api.resource(public_id, resource_type=resource_type)
            return True if info else False
            print(f"Details: {info}")
        except cloudinary.exceptions.NotFound:
            return False
        except Exception:
            return False

    async def list_resources(
        self,
        *,
        resource_type: str = "image",
        folder: str | None = None,
        max_results: int = 50,
        next_cursor: str | None = None,
    ) -> dict:
        try:
            params = {
                "resource_type": resource_type,
                "type": "upload",
                "max_results": max_results,
            }

            if folder:
                params["prefix"] = folder

            if next_cursor:
                params["next_cursor"] = next_cursor

            return cloudinary.api.resources(**params)

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to list Cloudinary resources: {e}",
            )

    async def safe_delete_cloudinary(self, public_id: str, resource_type:str):
        try:
            await self.delete_image(public_id,resource_type=resource_type)
        except Exception:
            pass

    async def safe_delete_many_cloudinary(self, public_ids: list[str], resource_type:str):
        try:
            await self.delete_images(public_ids,resource_type=resource_type)
        except Exception:
            pass


cloudinary_client = CloudinaryClient()
