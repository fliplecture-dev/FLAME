"""Keyless provider metadata validation and owner-approved standard embeds."""
from datetime import datetime, timezone
import logging
import re
from urllib.parse import parse_qs, urlsplit

import httpx
from fastapi import HTTPException
from app.modules.resources.validation import MediaRejected, validate_external_url

LOGGER = logging.getLogger(__name__)
HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be", "www.youtube-nocookie.com", "vimeo.com", "www.vimeo.com", "player.vimeo.com"}
PLAYBACK_NOTICE = "Video plays inside FLAME. Provider branding, recommendations or links may open the provider site."


def is_provider_url(raw):
    try: return urlsplit(raw or "").hostname in HOSTS
    except ValueError: return False


def learner_video_policy(resource_model):
    # Also cover legacy provider URLs incorrectly classified as interactive/video.
    from sqlalchemy import or_, not_
    return (
            or_(resource_model.type == "video", resource_model.external_url.is_(None), not_(or_(*[resource_model.external_url.like("https://" + host + "/%") for host in HOSTS]))),)


def reject(code, status=422):
    raise HTTPException(status, {"code": code, "field": "external_url"})


def parse_video(raw):
    try:
        url = validate_external_url(raw, HOSTS)
    except MediaRejected:
        reject("external_video_url_invalid")
    parsed = urlsplit(url); parts = parsed.path.strip("/").split("/"); query = parse_qs(parsed.query)
    if parsed.hostname in {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be", "www.youtube-nocookie.com"}:
        video_id = None
        if parsed.hostname == "youtu.be" and len(parts) == 1: video_id = parts[0]
        elif parts == ["watch"] and len(query.get("v", [])) == 1: video_id = query["v"][0]
        elif len(parts) == 2 and parts[0] in {"embed", "shorts", "live"}: video_id = parts[1]
        if not video_id or not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id): reject("external_video_url_invalid")
        # Ignore tracking/start/share parameters; never propagate caller player settings.
        return {"provider": "youtube", "provider_name": "YouTube", "video_id": video_id, "canonical_url": "https://www.youtube.com/watch?v=" + video_id}
    video_id = None
    if parsed.hostname in {"vimeo.com", "www.vimeo.com"}:
        if len(parts) == 1: video_id = parts[0]
        elif len(parts) == 3 and parts[0] in {"channels", "groups"}: video_id = parts[-1]
    elif parsed.hostname == "player.vimeo.com" and len(parts) == 2 and parts[0] == "video": video_id = parts[1]
    # Private/unlisted hash URLs and arbitrary path formats are not accepted.
    if not video_id or not re.fullmatch(r"[1-9][0-9]{0,11}", video_id) or query.get("h"): reject("external_video_url_invalid")
    return {"provider": "vimeo", "provider_name": "Vimeo", "video_id": video_id, "canonical_url": "https://vimeo.com/" + video_id}


def provider_json(endpoint, *, params=None, headers=None):
    # Endpoints are constants owned by adapters. No redirects, user hosts or HTML.
    try:
        with httpx.Client(timeout=4, follow_redirects=False, trust_env=False) as client:
            with client.stream("GET", endpoint, params=params, headers=headers) as response:
                if response.status_code in {401, 403, 404, 410}: reject("external_video_unavailable")
                if response.status_code != 200: reject("external_video_verification_failed", 503)
                data = bytearray()
                for chunk in response.iter_bytes():
                    data.extend(chunk)
                    if len(data) > 256 * 1024: reject("external_video_verification_failed", 503)
                import json
                result = json.loads(data)
                if not isinstance(result, dict): raise ValueError()
                return result
    except (httpx.HTTPError, ValueError):
        LOGGER.warning("External video provider verification failed; no URL, credentials or provider body logged")
        reject("external_video_verification_failed", 503)


def thumbnail_url(raw, provider):
    if not raw: return None
    hosts = {"i.ytimg.com", "img.youtube.com"} if provider == "youtube" else {"i.vimeocdn.com"}
    try: return validate_external_url(raw, hosts)
    except MediaRejected: return None


def inspect_video(raw, settings):
    video = parse_video(raw)
    endpoint = "https://www.youtube.com/oembed" if video["provider"] == "youtube" else "https://vimeo.com/api/oembed.json"
    metadata = provider_json(endpoint, params={"url": video["canonical_url"], "format": "json"})
    # Private/password-protected Vimeo responses omit these fields. Never use html.
    if metadata.get("type") != "video" or not metadata.get("title") or not metadata.get("author_name"):
        reject("external_video_unavailable")
    if video["provider"] == "vimeo" and str(metadata.get("video_id")) != video["video_id"]:
        reject("external_video_unavailable")
    video.update(title=str(metadata["title"])[:255], description=str(metadata.get("description") or "")[:2000],
                 thumbnail_url=thumbnail_url(metadata.get("thumbnail_url"), video["provider"]),
                 verified_at=datetime.now(timezone.utc).isoformat(), verification="metadata_only", embeddable=None)
    video.update(student_playback_allowed=True, playback_reason=PLAYBACK_NOTICE)
    return video


def video_data(resource):
    # The current server policy supersedes previously stored strict-mode flags.
    if resource.type not in {"video", "external_video"} or not is_provider_url(resource.external_url): return None
    stored = resource.external_video or {}
    stored = {**stored, "thumbnail_url": thumbnail_url(stored.get("thumbnail_url"), parse_video(resource.external_url)["provider"])}
    parsed = parse_video(resource.external_url)
    if not stored.get("thumbnail_url") and parsed["provider"] == "youtube":
        stored = {**stored, "thumbnail_url": "https://i.ytimg.com/vi/" + parsed["video_id"] + "/hqdefault.jpg"}
    return {**stored, **parsed, "student_playback_allowed": True, "playback_reason": PLAYBACK_NOTICE}


def embed_url(resource):
    video = parse_video(resource.external_url)
    if video["provider"] == "youtube":
        return "https://www.youtube.com/embed/" + video["video_id"] + "?enablejsapi=1&playsinline=1&rel=0"
    return "https://player.vimeo.com/video/" + video["video_id"] + "?title=0&byline=0&portrait=0"

