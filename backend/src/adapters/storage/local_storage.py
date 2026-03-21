"""Local filesystem storage adapter for development."""

from pathlib import Path
from urllib.parse import quote

from config.logging import get_logger
from config.settings import get_local_storage_path, get_settings

logger = get_logger(__name__)


class LocalStorageAdapter:
    """Store files locally and expose them via the backend static route."""

    def __init__(self) -> None:
        settings = get_settings()
        self.base_dir = get_local_storage_path()
        self.public_base_url = settings.public_base_url.rstrip("/")
        self.base_dir.mkdir(parents=True, exist_ok=True)

    async def put_file(
        self,
        file_data: bytes,
        file_name: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Write a file under the local storage root."""
        target_path = self._resolve_path(file_name)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(file_data)

        public_path = quote(file_name.replace("\\", "/").lstrip("/"), safe="/")
        url = f"{self.public_base_url}/media/{public_path}"
        logger.info("Stored local file at %s", target_path)
        return url

    async def get_file(
        self,
        file_name: str,
    ) -> bytes:
        """Read a stored local file."""
        return self._resolve_path(file_name).read_bytes()

    async def delete_file(
        self,
        file_name: str,
    ) -> bool:
        """Delete a stored local file if it exists."""
        target_path = self._resolve_path(file_name)
        if not target_path.exists():
            return False
        target_path.unlink()
        logger.info("Deleted local file at %s", target_path)
        return True

    async def get_presigned_url(
        self,
        file_name: str,
        expiration: int = 3600,
    ) -> str:
        """Return the public media URL for local files."""
        public_path = quote(file_name.replace("\\", "/").lstrip("/"), safe="/")
        return f"{self.public_base_url}/media/{public_path}"

    def _resolve_path(self, file_name: str) -> Path:
        relative_path = Path(file_name.replace("\\", "/").lstrip("/"))
        resolved_path = (self.base_dir / relative_path).resolve()
        if self.base_dir not in resolved_path.parents and resolved_path != self.base_dir:
            raise ValueError("Invalid storage path")
        return resolved_path
