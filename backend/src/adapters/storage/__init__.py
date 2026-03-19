"""Storage adapters module."""

from adapters.storage.base import StorageAdapter
from adapters.storage.local_storage import LocalStorageAdapter


def get_storage_adapter() -> StorageAdapter:
    """Return the local storage adapter."""
    return LocalStorageAdapter()

__all__ = [
    "StorageAdapter",
    "LocalStorageAdapter",
    "get_storage_adapter",
]

