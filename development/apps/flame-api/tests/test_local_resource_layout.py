from pathlib import Path
import pytest
from app.core.config import Settings
from app.modules.functional.resources.storage import ResourceStorage, StorageUnavailable


def test_local_uploads_route_by_type_and_preserve_existing_file(tmp_path):
    storage=ResourceStorage(Settings(_env_file=None,resource_local_dir=str(tmp_path/'assets')))
    source=tmp_path/'source';source.write_bytes(b'original')
    for suffix,folder in [('.png','images'),('.mp4','media'),('.html','interactive')]:
        key=storage.new_key(suffix)
        storage.put(key,source,'application/octet-stream')
        expected=tmp_path/'assets'/folder
        if suffix=='.html':expected=expected/Path(key).stem
        assert storage.local_path(key)==expected/Path(key).name
        assert storage.exists(key)
        with pytest.raises(StorageUnavailable):storage.put(key,source,'application/octet-stream')
        assert storage.local_path(key).read_bytes()==b'original'
        if suffix=='.html':assert storage.read_document(key,100)==b'original'
        storage.delete(key);assert not storage.exists(key)


def test_legacy_key_and_traversal(tmp_path):
    storage=ResourceStorage(Settings(_env_file=None,resource_local_dir=str(tmp_path)))
    key=storage.new_key('.html');legacy=tmp_path/key
    legacy.parent.mkdir();legacy.write_bytes(b'legacy')
    assert storage.exists(key) and storage.read_document(key,100)==b'legacy'
    with pytest.raises(StorageUnavailable):storage.local_path('../interactive/file.html')


def test_named_activity_folders_and_flat_compatibility(tmp_path):
    storage=ResourceStorage(Settings(_env_file=None,resource_local_dir=str(tmp_path)))
    key=storage.new_key('.html')
    flat=tmp_path/'interactive'/Path(key).name
    flat.parent.mkdir();flat.write_bytes(b'activity')
    assert storage.read_document(key,100)==b'activity'
    named=flat.parent/'gravity-lab'/flat.name
    named.parent.mkdir();flat.rename(named)
    assert storage.local_path(key)==named
    assert storage.read_document(key,100)==b'activity'
    duplicate=flat.parent/'another-lab'/flat.name
    duplicate.parent.mkdir();duplicate.write_bytes(b'other')
    with pytest.raises(StorageUnavailable,match='duplicate_interactive_asset'):storage.exists(key)
    duplicate.unlink()
    storage.delete(key)
    assert not named.exists()
