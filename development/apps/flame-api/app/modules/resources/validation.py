"""B9.2 media and link validation; no arbitrary executable hosting."""
import ipaddress
from pathlib import PurePosixPath
from urllib.parse import urlsplit, urlunsplit

from PIL import Image, UnidentifiedImageError

FORMATS = {
    ".html": ("text/html", "interactive", 2 * 1024 * 1024),
    ".htm": ("text/html", "interactive", 2 * 1024 * 1024),
    ".jpg": ("image/jpeg", "image", 10 * 1024 * 1024),
    ".jpeg": ("image/jpeg", "image", 10 * 1024 * 1024),
    ".png": ("image/png", "image", 10 * 1024 * 1024),
    ".webp": ("image/webp", "image", 10 * 1024 * 1024),
    ".gif": ("image/gif", "video", 10 * 1024 * 1024),
    ".mp4": ("video/mp4", "video", 100 * 1024 * 1024),
    ".webm": ("video/webm", "video", 100 * 1024 * 1024),
}
RESOURCE_TYPES = {"image", "video", "interactive"}
MEDIA_TYPES = {"image": {"image"}, "video": {"video"}, "interactive": {"interactive"}}
TYPE_ALIASES = {"diagram": "image", "animation": "video", "external_video": "video"}


def canonical_type(value):
    return TYPE_ALIASES.get(value, value)



class MediaRejected(ValueError):
    pass


def declared_format(filename: str, content_type: str):
    suffix = PurePosixPath(filename.replace("\\", "/")).suffix.lower()
    result = FORMATS.get(suffix)
    if not result or content_type.lower().split(";", 1)[0].strip() != result[0]:
        raise MediaRejected("unsupported_media_format")
    return suffix, *result


def inspect_media(path, mime_type: str):
    if mime_type == "text/html":
        from app.modules.resources.interactive import HTML_LIMIT, InvalidInteractive, validate_document
        try:
            with open(path, "rb") as stream:
                validate_document(stream.read(HTML_LIMIT + 1))
        except InvalidInteractive as exc:
            raise MediaRejected(str(exc)) from exc
        return
    with open(path, "rb") as stream:
        head = stream.read(32)
    if mime_type == "image/gif" and head[:6] not in {b"GIF87a", b"GIF89a"}:
        raise MediaRejected("invalid_media_content")
    if mime_type == "image/png" and not head.startswith(b"\x89PNG\r\n\x1a\n"):
        raise MediaRejected("invalid_media_content")
    if mime_type == "image/jpeg" and not head.startswith(b"\xff\xd8\xff"):
        raise MediaRejected("invalid_media_content")
    if mime_type == "image/webp" and not (head[:4] == b"RIFF" and head[8:12] == b"WEBP"):
        raise MediaRejected("invalid_media_content")
    if mime_type == "audio/mpeg" and not (head.startswith(b"ID3") or head[:1] == b"\xff" and head[1:2] and head[1] & 0xE0 == 0xE0):
        raise MediaRejected("invalid_media_content")
    if mime_type in {"audio/mp4", "video/mp4"} and not (head[4:8] == b"ftyp" and len(head) >= 12):
        raise MediaRejected("invalid_media_content")
    if mime_type == "video/webm" and not head.startswith(b"\x1a\x45\xdf\xa3"):
        raise MediaRejected("invalid_media_content")
    if mime_type.startswith("image/"):
        try:
            with Image.open(path) as img:
                if img.format not in {"JPEG", "PNG", "WEBP", "GIF"} or img.width * img.height > 40_000_000:
                    raise MediaRejected("invalid_media_content")
                if Image.MIME.get(img.format) != mime_type:
                    raise MediaRejected("invalid_media_content")
                # Decode every GIF frame to reject truncated/corrupt animations.
                if mime_type == "image/gif":
                    if img.n_frames > 1000 or img.width * img.height * img.n_frames > 200_000_000:
                        raise MediaRejected("animation_too_complex")
                    for frame in range(img.n_frames):
                        img.seek(frame); img.load()
                else:
                    img.load()
        except MediaRejected:
            raise
        except (UnidentifiedImageError, OSError, ValueError, EOFError, Image.DecompressionBombError) as exc:
            raise MediaRejected("invalid_media_content") from exc


def validate_external_url(raw: str, allowed_hosts: set[str]) -> str:
    if not isinstance(raw, str) or len(raw) > 2048 or any(ord(char) <= 32 or ord(char) == 127 for char in raw) or "\\" in raw:
        raise MediaRejected("invalid_external_url")
    try:
        parsed = urlsplit(raw)
        host = (parsed.hostname or "").encode("idna").decode("ascii").lower().rstrip(".")
        if parsed.scheme != "https" or parsed.username or parsed.password or parsed.port not in (None, 443):
            raise ValueError
        if parsed.fragment or not host or host == "localhost" or host.endswith(".localhost"):
            raise ValueError
        try:
            ipaddress.ip_address(host)
        except ValueError:
            pass
        else:
            raise ValueError
        if host not in allowed_hosts:
            raise MediaRejected("external_host_not_approved")
    except MediaRejected:
        raise
    except (ValueError, UnicodeError):
        raise MediaRejected("invalid_external_url") from None
    return urlunsplit(("https", host, parsed.path or "/", parsed.query, ""))
