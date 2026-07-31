import pytest

from app.ingestion.storage import LocalDiskStorage


@pytest.mark.asyncio
async def test_local_disk_storage_save_and_resolve(tmp_path):
    storage = LocalDiskStorage(str(tmp_path))

    storage_key = await storage.save("call.wav", b"fake audio bytes")
    resolved = storage.resolve_path(storage_key)

    assert resolved.exists()
    assert resolved.read_bytes() == b"fake audio bytes"
    assert resolved.suffix == ".wav"
