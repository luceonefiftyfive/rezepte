import asyncio
import re
import uuid
from dataclasses import dataclass

from app.core.settings import Settings
from botocore.exceptions import BotoCoreError, ClientError
from litestar.datastructures import UploadFile
from litestar.exceptions import HTTPException


@dataclass(frozen=True)
class UploadedImage:
    key: str
    size: int
    content_type: str


@dataclass(frozen=True)
class DownloadedImage:
    key: str
    content: bytes
    content_type: str


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
        except (BotoCoreError, ClientError) as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        return UploadedImage(
            key=object_key,
            size=len(content),
            content_type=file.content_type,
        )

    async def download_image(self, key: str) -> DownloadedImage:
        try:
            response = await asyncio.to_thread(
                self.s3_client.get_object,
                Bucket=self.settings.s3_bucket,
                Key=key,
            )
            content = await asyncio.to_thread(response["Body"].read)
        except (BotoCoreError, ClientError) as exc:
            raise HTTPException(status_code=404, detail="Image not found") from exc

        return DownloadedImage(
            key=key,
            content=content,
            content_type=response.get("ContentType") or "application/octet-stream",
        )

    async def restore_image(
        self, *, key: str, content: bytes, content_type: str
    ) -> None:
        try:
            await asyncio.to_thread(
                self.s3_client.put_object,
                Bucket=self.settings.s3_bucket,
                Key=key,
                Body=content,
                ContentType=content_type,
            )
        except (BotoCoreError, ClientError) as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
