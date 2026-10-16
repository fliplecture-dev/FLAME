"""Three media families retain source and GIF semantics."""
import pytest
from pydantic import ValidationError
from app.modules.functional.resources.validation import RESOURCE_TYPES, declared_format, MediaRejected
from app.modules.functional.resources.router import DraftCreate
from app.modules.functional.resources.models import Resource
from app.modules.functional.resources.external_video import video_data
from app.modules.functional.resources.service import publication_check
from app.core.config import Settings


def test_three_types_and_backwards_compatible_inputs():
    assert RESOURCE_TYPES == {"image", "video", "interactive"}
    for old, new in [("diagram", "image"), ("animation", "video"), ("external_video", "video")]:
        draft = DraftCreate(type=old,title="Learning media",external_url="https://media.example.test/file")
        assert draft.type == new
        assert Resource(type=old).type == new
    with pytest.raises(ValidationError):
        DraftCreate(type="audio",title="Audio",external_url="https://media.example.test/audio.mp3")


def test_gif_video_and_audio_upload_rejection():
    assert declared_format("motion.gif", "image/gif")[2] == "video"
    with pytest.raises(MediaRejected):
        declared_format("voice.mp3", "audio/mpeg")
    with pytest.raises(MediaRejected):
        declared_format("voice.m4a", "audio/mp4")


def test_provider_video_keeps_embed_metadata():
    row = Resource(type="video",external_url="https://www.youtube.com/watch?v=M7lc1UVf-VE",external_video={})
    assert video_data(row)["video_id"] == "M7lc1UVf-VE"
    assert video_data(Resource(type="video",external_url="https://media.example.test/movie.mp4")) is None
