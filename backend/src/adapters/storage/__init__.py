"""Storage adapters module."""

from adapters.storage.base import StorageAdapter
from adapters.storage.s3_storage import S3StorageAdapter

__all__ = [
    "StorageAdapter",
    "S3StorageAdapter",
]

