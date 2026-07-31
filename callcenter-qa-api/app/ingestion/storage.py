import uuid
from abc import ABC, abstractmethod
from pathlib import Path


class StorageBackend(ABC):
    """Storage seam: LocalDiskStorage is the MVP implementation. An S3Storage /
    AzureBlobStorage implementation can be added later, selected via config,
    with no changes to the ingestion or transcription code that calls this."""

    @abstractmethod
    async def save(self, filename: str, content: bytes) -> str:
        """Persist content, return a storage_key usable to retrieve it later."""

    @abstractmethod
    def resolve_path(self, storage_key: str) -> Path:
        """Return a local filesystem path (engines like faster-whisper need one)."""


class LocalDiskStorage(StorageBackend):
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    async def save(self, filename: str, content: bytes) -> str:
        ext = Path(filename).suffix
        storage_key = f"{uuid.uuid4()}{ext}"
        self.resolve_path(storage_key).write_bytes(content)
        return storage_key

    def resolve_path(self, storage_key: str) -> Path:
        return self.base_path / storage_key
