"""Base storage adapter protocol."""

from typing import Protocol


class StorageAdapter(Protocol):
    """Protocol for storage adapters."""
    
    async def put_file(
        self,
        file_data: bytes,
        file_name: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload a file to storage.
        
        Args:
            file_data: File content as bytes
            file_name: Name/key for the file
            content_type: MIME type
            
        Returns:
            URL or key of uploaded file
        """
        ...
    
    async def get_file(
        self,
        file_name: str,
    ) -> bytes:
        """Download a file from storage.
        
        Args:
            file_name: Name/key of the file
            
        Returns:
            File content as bytes
        """
        ...
    
    async def delete_file(
        self,
        file_name: str,
    ) -> bool:
        """Delete a file from storage.
        
        Args:
            file_name: Name/key of the file
            
        Returns:
            True if deleted successfully
        """
        ...
    
    async def get_presigned_url(
        self,
        file_name: str,
        expiration: int = 3600,
    ) -> str:
        """Get a presigned URL for accessing a file.
        
        Args:
            file_name: Name/key of the file
            expiration: URL expiration time in seconds
            
        Returns:
            Presigned URL
        """
        ...

