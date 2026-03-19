"""Storage adapters module."""

from adapters.storage.base import StorageAdapter
from adapters.storage.local_storage import LocalStorageAdapter
from adapters.storage.supabase_storage import SupabaseStorageAdapter


def get_storage_adapter() -> StorageAdapter:
    """Return the Supabase storage adapter."""
    return SupabaseStorageAdapter()

__all__ = [
    "StorageAdapter",
    "LocalStorageAdapter",
    "SupabaseStorageAdapter",
    "get_storage_adapter",
]

