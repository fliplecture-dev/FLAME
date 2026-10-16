from uuid import uuid4

from app.core.config import Settings
from app.modules.functional.resources.candidates import eligible_candidates
from app.modules.functional.resources.models import Resource
from app.modules.functional.resources.storage import ResourceStorage


class BrowseSession:
    def __init__(self, rows):
        self.rows = rows
        self.info = {}

    def scalars(self, _statement):
        return self

    def all(self):
        return self.rows


def test_shared_media_checked_once_per_browse_but_rechecked_next_request(monkeypatch):
    media = Resource(id=uuid4(), type="image", title="Illustration", version=1,
                     storage_key="resource-uploads/" + uuid4().hex + ".png",
                     mime_type="image/png", published=True, availability="available",
                     learning_metadata={})
    checks = []
    available = True

    def exists(_storage, key):
        checks.append(key)
        return available

    monkeypatch.setattr(ResourceStorage, "exists", exists)
    settings = Settings(environment="test", _env_file=None)
    request = BrowseSession([media])
    assert eligible_candidates(request, uuid4(), None, settings)
    assert eligible_candidates(request, uuid4(), None, settings)
    assert checks == [media.storage_key]

    available = False
    assert eligible_candidates(BrowseSession([media]), uuid4(), None, settings) == []
    assert checks == [media.storage_key, media.storage_key]
