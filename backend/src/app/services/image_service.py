import asyncio
import re
import uuid
from dataclasses import dataclass

from app.core.settings import Settings
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import HTTPException, UploadFile


@dataclass(frozen=True)
class UploadedImage:
    key: str
    size: int
    content_type: str
    view_url: str
    expires_in: int


class ImageService:
    def __init__(self, s3_client, settings: Settings):
        self.s3_client = s3_client
        self.settings = settings

    @staticmethod
    def _safe_filename(filename: str | None) -> str:
        candidate = (filename or "upload").strip()
        candidate = re.sub(r"[^A-Za-z0-9._-]", "-", candidate)
        candidate = re.sub(r"-+", "-", candidate).strip("-")
        return candidate or "upload"

    async def upload_image(
        self,
        *,
        file: UploadFile,
        key_prefix: str,
        max_size_bytes: int = 10 * 1024 * 1024,
        url_expires_in: int = 60 * 60 * 24,
    ) -> UploadedImage:
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="Only image files are allowed")

        content = await file.read()
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")
        if len(content) > max_size_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"Image is larger than {max_size_bytes // (1024 * 1024)} MB",
            )

        object_key = f"{key_prefix}/{uuid.uuid4()}-{self._safe_filename(file.filename)}"

        try:
            await asyncio.to_thread(
                self.s3_client.put_object,
                Bucket=self.settings.s3_bucket,
                Key=object_key,
                Body=content,
                ContentType=file.content_type,
            )
            view_url = await asyncio.to_thread(
                self.s3_client.generate_presigned_url,
                "get_object",
                Params={"Bucket": self.settings.s3_bucket, "Key": object_key},
                ExpiresIn=url_expires_in,
            )
        except (BotoCoreError, ClientError) as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        return UploadedImage(
            key=object_key,
            size=len(content),
            content_type=file.content_type,
            view_url=view_url,
            expires_in=url_expires_in,
        )

    async def create_view_url(self, key: str, expires_in: int = 60 * 60 * 24) -> str:
        try:
            return await asyncio.to_thread(
                self.s3_client.generate_presigned_url,
                "get_object",
                Params={"Bucket": self.settings.s3_bucket, "Key": key},
                ExpiresIn=expires_in,
            )
        except (BotoCoreError, ClientError) as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
