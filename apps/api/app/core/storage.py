from __future__ import annotations

from abc import ABC, abstractmethod

import httpx

from app.core.config import settings


class StorageError(Exception):
    """Raised when a storage operation fails, without leaking response bodies."""


class StorageNotConfiguredError(StorageError):
    """Raised when storage access is attempted but Supabase Storage is not configured."""


class DocumentStorage(ABC):
    @abstractmethod
    async def upload(self, path: str, content: bytes, content_type: str) -> None: ...

    @abstractmethod
    async def download(self, path: str) -> bytes: ...

    @abstractmethod
    async def delete(self, path: str) -> None: ...


class SupabaseStorage(DocumentStorage):
    """Talks to Supabase Storage's REST API directly (no Storage SDK), using
    the service_role key — see the settings.supabase_service_role_key
    comment in app/core/config.py for why that key is required here."""

    def __init__(self, base_url: str, service_role_key: str, bucket: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._service_role_key = service_role_key
        self._bucket = bucket

    def _headers(self, **extra: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._service_role_key}",
            "apikey": self._service_role_key,
            **extra,
        }

    async def upload(self, path: str, content: bytes, content_type: str) -> None:
        url = f"{self._base_url}/object/{self._bucket}/{path}"
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                url,
                headers=self._headers(**{"Content-Type": content_type}),
                content=content,
            )
        if response.status_code >= 400:
            raise StorageError(f"upload failed with status {response.status_code}")
        
    async def download(self, path: str) -> bytes:
         url = f"{self._base_url}/object/{self._bucket}/{path}"

         async with httpx.AsyncClient(timeout=30) as client:
             response = await client.get(
                 url,
                 headers=self._headers(),
        )

         if response.status_code >= 400:
            raise StorageError(
            f"download failed with status {response.status_code}"
        )

         return response.content   


    async def delete(self, path: str) -> None:
        url = f"{self._base_url}/object/{self._bucket}"
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.request(
                "DELETE", url, headers=self._headers(), json={"prefixes": [path]}
            )
        if response.status_code >= 400:
            raise StorageError(f"delete failed with status {response.status_code}")


_storage_client: DocumentStorage | None = None


def get_storage_client() -> DocumentStorage:
    """Returns a process-wide singleton Supabase Storage client, constructed
    lazily so importing this module never requires Storage settings to be
    set (e.g. running pytest, which overrides this via app.api.deps.get_storage
    instead of ever calling this function)."""
    global _storage_client
    if _storage_client is None:
        if not (settings.supabase_url and settings.supabase_service_role_key):
            raise StorageNotConfiguredError("Supabase Storage is not configured")
        _storage_client = SupabaseStorage(
            base_url=f"{settings.supabase_url.rstrip('/')}/storage/v1",
            service_role_key=settings.supabase_service_role_key,
            bucket=settings.supabase_storage_bucket,
        )
    return _storage_client
