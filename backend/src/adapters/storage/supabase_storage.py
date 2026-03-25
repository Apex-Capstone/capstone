"""Supabase Storage adapter implementation."""

from urllib.parse import quote

import httpx

from config.logging import get_logger
from config.settings import get_settings

logger = get_logger(__name__)


class SupabaseStorageAdapter:
    """Adapter for Supabase Storage."""

    def __init__(self) -> None:
        settings = get_settings()
        self.supabase_url = settings.supabase_url.rstrip("/")
        self.service_role_key = settings.supabase_service_role_key
        self.bucket_name = settings.supabase_storage_bucket
        self._client = httpx.AsyncClient(timeout=30.0)

    async def put_file(
        self,
        file_data: bytes,
        file_name: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload file to Supabase Storage and return the stable object key."""
        self._require_config()
        object_key = file_name.replace("\\", "/").lstrip("/")
        encoded_key = quote(object_key, safe="/")

        response = await self._client.post(
            f"{self.supabase_url}/storage/v1/object/{self.bucket_name}/{encoded_key}",
            content=file_data,
            headers={
                "Authorization": f"Bearer {self.service_role_key}",
                "apikey": self.service_role_key,
                "Content-Type": content_type,
                "x-upsert": "true",
            },
        )
        response.raise_for_status()
        logger.info("Uploaded file to Supabase Storage: %s", object_key)
        return object_key

    async def get_file(
        self,
        file_name: str,
    ) -> bytes:
        """Download file from Supabase Storage."""
        self._require_config()
        object_key = file_name.replace("\\", "/").lstrip("/")
        encoded_key = quote(object_key, safe="/")

        response = await self._client.get(
            f"{self.supabase_url}/storage/v1/object/authenticated/{self.bucket_name}/{encoded_key}",
            headers={
                "Authorization": f"Bearer {self.service_role_key}",
                "apikey": self.service_role_key,
            },
        )
        response.raise_for_status()
        return response.content

    async def delete_file(
        self,
        file_name: str,
    ) -> bool:
        """Delete file from Supabase Storage."""
        self._require_config()
        object_key = file_name.replace("\\", "/").lstrip("/")

        response = await self._client.delete(
            f"{self.supabase_url}/storage/v1/object/{self.bucket_name}",
            headers={
                "Authorization": f"Bearer {self.service_role_key}",
                "apikey": self.service_role_key,
                "Content-Type": "application/json",
            },
            json={"prefixes": [object_key]},
        )
        response.raise_for_status()
        logger.info("Deleted file from Supabase Storage: %s", object_key)
        return True

    async def get_presigned_url(
        self,
        file_name: str,
        expiration: int = 3600,
    ) -> str:
        """Create a signed URL for private Supabase Storage access."""
        self._require_config()
        object_key = file_name.replace("\\", "/").lstrip("/")
        encoded_key = quote(object_key, safe="/")

        response = await self._client.post(
            f"{self.supabase_url}/storage/v1/object/sign/{self.bucket_name}/{encoded_key}",
            headers={
                "Authorization": f"Bearer {self.service_role_key}",
                "apikey": self.service_role_key,
                "Content-Type": "application/json",
            },
            json={"expiresIn": expiration},
        )
        response.raise_for_status()
        data = response.json()
        signed_path = data.get("signedURL") or data.get("signedUrl")
        if not signed_path:
            raise RuntimeError("Supabase signed URL response missing signedURL")
        if signed_path.startswith("http://") or signed_path.startswith("https://"):
            return signed_path
        return f"{self.supabase_url}{signed_path}"

    def _require_config(self) -> None:
        if not self.supabase_url or not self.service_role_key or not self.bucket_name:
            raise RuntimeError("Supabase storage is not configured")
