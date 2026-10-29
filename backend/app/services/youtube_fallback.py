"""Bounded public watch-page caption extraction, used only after an HTTP 403."""

import json
import re
import time
from urllib.parse import parse_qsl, urlencode, urlsplit

from requests.exceptions import HTTPError, Timeout

MAX_RESPONSE_BYTES = 2 * 1024 * 1024


def is_http_403(error: BaseException) -> bool:
    """Recognize the HTTPError wrapped by youtube-transcript-api, not its text."""
    pending = [error]
    seen = set()
    while pending:
        current = pending.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        if isinstance(current, HTTPError) and getattr(current.response, "status_code", None) == 403:
            return True
        pending.extend(exc for exc in (current.__cause__, current.__context__) if exc is not None)
    return False


def _read_response(session, url: str, deadline: float) -> str:
    if time.monotonic() >= deadline:
        raise Timeout("Transcript deadline exceeded")
    # Both callers construct URLs on a fixed YouTube origin. No redirects,
    # external caption hosts, subprocesses, or video downloads.
    with session.get(url, stream=True, allow_redirects=False) as response:
        response.raise_for_status()
        if response.status_code != 200:
            raise RuntimeError("Unexpected caption response")
        body = bytearray()
        for part in response.iter_content(chunk_size=16 * 1024):
            if time.monotonic() >= deadline:
                raise Timeout("Transcript deadline exceeded")
            if len(body) + len(part) > MAX_RESPONSE_BYTES:
                raise RuntimeError("Caption response exceeds size limit")
            body.extend(part)
    return body.decode("utf-8")


def _caption_url(track: dict) -> str:
    value = track.get("baseUrl", "")
    if not isinstance(value, str):
        raise ValueError("Invalid caption URL")
    parsed = urlsplit(value)
    if (parsed.scheme != "https" or parsed.hostname not in {"www.youtube.com", "youtube.com"}
            or parsed.port not in {None, 443} or parsed.username or parsed.password
            or parsed.path != "/api/timedtext" or parsed.fragment):
        raise ValueError("Unsupported caption URL")
    query = [(key, value) for key, value in parse_qsl(parsed.query) if key != "fmt"]
    return "https://www.youtube.com/api/timedtext?" + urlencode([*query, ("fmt", "json3")])


def fetch_watch_page_captions(session, video_id: str, languages: list[str], deadline: float) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
        raise ValueError("Invalid video ID")
    page = _read_response(session, "https://www.youtube.com/watch?" + urlencode({"v": video_id}), deadline)
    player = None
    for match in re.finditer(r"(?:var\s+)?ytInitialPlayerResponse\s*=\s*", page):
        try:
            candidate, _ = json.JSONDecoder().raw_decode(page, match.end())
        except ValueError:
            continue
        if isinstance(candidate, dict):
            player = candidate
            break
    if player is None or player.get("playabilityStatus", {}).get("status", "OK") != "OK":
        raise RuntimeError("Public captions unavailable")
    if player.get("videoDetails", {}).get("videoId", video_id) != video_id:
        raise RuntimeError("Caption video mismatch")
    tracks = player.get("captions", {}).get("playerCaptionsTracklistRenderer", {}).get("captionTracks", [])
    if not isinstance(tracks, list):
        raise RuntimeError("Invalid caption tracks")
    preferred = {language.lower().split("-")[0] for language in languages}
    tracks = sorted((track for track in tracks[:100] if isinstance(track, dict)), key=lambda track: (
        str(track.get("languageCode", "")).lower().split("-")[0] not in preferred,
        track.get("kind") == "asr",
    ))
    for track in tracks:
        try:
            url = _caption_url(track)
        except ValueError:
            continue
        payload = json.loads(_read_response(session, url, deadline))
        parts = [segment["utf8"] for event in payload.get("events", [])
                 for segment in event.get("segs", []) if isinstance(segment.get("utf8"), str)]
        text = " ".join(parts).strip()
        if text:
            return text
        # Never fan out into dozens of requests for empty/broken caption tracks.
        break
    raise RuntimeError("Public captions unavailable")
