import asyncio
import re
import uuid
from dataclasses import dataclass
from io import BytesIO

from app.core.settings import Settings
from botocore.exceptions import BotoCoreError, ClientError
from litestar.datastructures import UploadFile
from litestar.exceptions import HTTPException
from PIL import Image, ImageOps, UnidentifiedImageError

THUMBNAIL_MAX_SIZE = (360, 360)


@dataclass(frozen=True)
class UploadedImage:
    key: str
    thumbnail_key: str
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

    @staticmethod
    def thumbnail_key(key: str) -> str:
        return f"{key}.thumbnail.jpg"

    @staticmethod
    def _is_missing_object_error(exc: ClientError) -> bool:
        error = exc.response.get("Error", {})
        status_code = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        return (
            error.get("Code") in {"404", "NoSuchKey", "NotFound", "NoSuchObject"}
            or status_code == 404
        )

    @staticmethod
    def _create_thumbnail(content: bytes) -> bytes:
        try:
            with Image.open(BytesIO(content)) as source:
                image = ImageOps.exif_transpose(source)
                if image.mode != "RGB":
                    background = Image.new("RGB", image.size, "white")
                    if image.mode == "RGBA":
                        background.paste(image, mask=image.getchannel("A"))
                    else:
                        background.paste(image)
                    image = background
                image.thumbnail(THUMBNAIL_MAX_SIZE, Image.Resampling.LANCZOS)
                output = BytesIO()
                image.save(output, format="JPEG", quality=85, optimize=True)
                return output.getvalue()
        except (UnidentifiedImageError, OSError) as exc:
            raise HTTPException(
                status_code=400, detail="Uploaded file is not a valid image"
            ) from exc

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
        thumbnail_key = self.thumbnail_key(object_key)
        thumbnail = await asyncio.to_thread(self._create_thumbnail, content)

        try:
            await asyncio.to_thread(
                self.s3_client.put_object,
                Bucket=self.settings.s3_bucket,
                Key=object_key,
                Body=content,
                ContentType=file.content_type,
            )
            await asyncio.to_thread(
                self.s3_client.put_object,
                Bucket=self.settings.s3_bucket,
                Key=thumbnail_key,
                Body=thumbnail,
                ContentType="image/jpeg",
            )
        except (BotoCoreError, ClientError) as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        return UploadedImage(
            key=object_key,
            thumbnail_key=thumbnail_key,
            size=len(content),
            content_type=file.content_type,
        )

    async def thumbnail_exists(self, key: str) -> bool:
        try:
            await asyncio.to_thread(
                self.s3_client.head_object,
                Bucket=self.settings.s3_bucket,
                Key=key,
            )
        except ClientError as exc:
            if self._is_missing_object_error(exc):
                return False
            raise HTTPException(
                status_code=500, detail="Unable to check image thumbnail"
            ) from exc
        except BotoCoreError as exc:
            raise HTTPException(
                status_code=500, detail="Unable to check image thumbnail"
            ) from exc
        return True

    async def ensure_thumbnail(self, key: str) -> str:
        thumbnail_key = self.thumbnail_key(key)
        if await self.thumbnail_exists(thumbnail_key):
            return thumbnail_key

        original = await self.download_image(key)
        thumbnail = await asyncio.to_thread(self._create_thumbnail, original.content)
        try:
            await asyncio.to_thread(
                self.s3_client.put_object,
                Bucket=self.settings.s3_bucket,
                Key=thumbnail_key,
                Body=thumbnail,
                ContentType="image/jpeg",
            )
        except (BotoCoreError, ClientError) as exc:
            raise HTTPException(
                status_code=500, detail="Unable to save image thumbnail"
            ) from exc
        return thumbnail_key

    async def download_image(self, key: str) -> DownloadedImage:
        try:
            response = await asyncio.to_thread(
                self.s3_client.get_object,
                Bucket=self.settings.s3_bucket,
                Key=key,
            )
            content = await asyncio.to_thread(response["Body"].read)
        except ClientError as exc:
            if self._is_missing_object_error(exc):
                raise HTTPException(status_code=404, detail="Image not found") from exc
            raise HTTPException(
                status_code=500, detail="Unable to download image"
            ) from exc
        except BotoCoreError as exc:
            raise HTTPException(
                status_code=500, detail="Unable to download image"
            ) from exc

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
