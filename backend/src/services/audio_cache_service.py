"""Backend local disk cache for assistant audio reads."""

from pathlib import Path

from config.settings import get_audio_cache_path, get_settings


class AudioCacheService:
    """Cache assistant audio locally with LRU eviction."""

    def __init__(self) -> None:
        self.base_dir = get_audio_cache_path()
        self.max_bytes = get_settings().audio_cache_max_bytes
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def get_cached_path(self, object_key: str) -> Path | None:
        """Return the cached file path if present and update access time."""
        cache_path = self._resolve_path(object_key)
        if not cache_path.exists():
            return None
        cache_path.touch(exist_ok=True)
        return cache_path

    def cache_file(self, object_key: str, file_data: bytes) -> Path:
        """Write a file into the cache and evict old files if needed."""
        cache_path = self._resolve_path(object_key)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_bytes(file_data)
        cache_path.touch(exist_ok=True)
        self._evict_if_needed(exclude_path=cache_path)
        return cache_path

    def delete_cached_file(self, object_key: str) -> bool:
        """Delete a cached file if it exists."""
        cache_path = self._resolve_path(object_key)
        if not cache_path.exists():
            return False
        cache_path.unlink()
        return True

    def _resolve_path(self, object_key: str) -> Path:
        relative_path = Path(object_key.replace("\\", "/").lstrip("/"))
        resolved_path = (self.base_dir / relative_path).resolve()
        if self.base_dir not in resolved_path.parents and resolved_path != self.base_dir:
            raise ValueError("Invalid cache path")
        return resolved_path

    def _evict_if_needed(self, exclude_path: Path | None = None) -> None:
        files = [path for path in self.base_dir.rglob("*") if path.is_file()]
        total_size = sum(path.stat().st_size for path in files)
        if total_size <= self.max_bytes:
            return

        files_by_access = sorted(files, key=lambda path: path.stat().st_atime)
        for path in files_by_access:
            if exclude_path is not None and path == exclude_path:
                continue
            total_size -= path.stat().st_size
            path.unlink(missing_ok=True)
            self._cleanup_empty_parents(path.parent)
            if total_size <= self.max_bytes:
                break

    def _cleanup_empty_parents(self, path: Path) -> None:
        while path != self.base_dir and path.exists():
            try:
                path.rmdir()
            except OSError:
                break
            path = path.parent
