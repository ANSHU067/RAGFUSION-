"""Bounded public watch-page caption extraction, used after upstream API blocking."""

import json
import random
import re
import time
from urllib.parse import parse_qsl, urlencode, urlsplit

import httpx
from requests.exceptions import HTTPError, Timeout

MAX_RESPONSE_BYTES = 2 * 1024 * 1024


# Keep a consistent browser profile throughout one fallback attempt. These
# headers are never applied to youtube-transcript-api's Innertube session.
BROWSER_PROFILES = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:132.0) Gecko/20100101 Firefox/132.0",
)


def browser_headers() -> dict[str, str]:
    return {
        "User-Agent": random.choice(BROWSER_PROFILES),
        "Accept": "text/html,application/json,application/xhtml+xml,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }


def should_use_caption_fallback(error: BaseException) -> bool:
    """Handle current/legacy SDK blocking classes and wrapped HTTP failures."""
    import youtube_transcript_api
    _errors = getattr(youtube_transcript_api, "_errors", None)

    blocking_types = tuple(cls for name in (
        "RequestBlocked", "IpBlocked", "TooManyRequests", "YouTubeRequestFailed",
    ) if isinstance(cls := getattr(youtube_transcript_api, name, getattr(_errors, name, None)), type))
    pending = [error]
    seen = set()
    while pending:
        current = pending.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        if isinstance(current, (HTTPError, *blocking_types)):
            return True
        pending.extend(exc for exc in (current.__cause__, current.__context__) if exc is not None)
    return False


def _read_response(session, url: str, deadline: float) -> str:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise Timeout("Transcript deadline exceeded")
    # Both callers construct URLs on a fixed YouTube origin. No redirects,
    # external caption hosts, subprocesses, or video downloads.
    with session.stream(
        "GET", url, follow_redirects=False,
        timeout=httpx.Timeout(min(20.0, remaining), connect=min(5.0, remaining)),
    ) as response:
        response.raise_for_status()
        if response.status_code != 200:
            raise RuntimeError("Unexpected caption response")
        body = bytearray()
        for part in response.iter_bytes():
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


def _extract_player(page: str) -> dict:
    # Parse JSON, never execute JavaScript. Support assignments, window keys,
    # and embedded player-response properties used by watch-page variants.
    pattern = r'(?:\bytInitialPlayerResponse|window\[\s*["\']ytInitialPlayerResponse["\']\s*\])\s*=\s*|["\']ytInitialPlayerResponse["\']\s*:\s*'
    for match in re.finditer(pattern, page):
        try:
            candidate, _ = json.JSONDecoder().raw_decode(page, match.end())
            if isinstance(candidate, str):
                candidate = json.loads(candidate)
        except ValueError:
            continue
        if isinstance(candidate, dict) and "captions" in candidate:
            return candidate
    raise RuntimeError("Public captions unavailable")


def fetch_watch_page_captions(video_id: str, languages: list[str], deadline: float) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
        raise ValueError("Invalid video ID")
    if time.monotonic() >= deadline:
        raise Timeout("Transcript deadline exceeded")
    with httpx.Client(
        headers=browser_headers(), follow_redirects=False,
        limits=httpx.Limits(max_connections=1, max_keepalive_connections=1),
    ) as client:
        return _fetch_captions(client, video_id, languages, deadline)


def _fetch_captions(client, video_id: str, languages: list[str], deadline: float) -> str:
    page = _read_response(client, "https://www.youtube.com/watch?" + urlencode({"v": video_id}), deadline)
    player = _extract_player(page)
    if player.get("playabilityStatus", {}).get("status", "OK") != "OK":
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
    attempts = 0
    visited = set()
    for track in tracks:
        try:
            url = _caption_url(track)
        except ValueError:
            continue
        if url in visited:
            continue
        if attempts >= 3:
            break
        attempts += 1
        visited.add(url)
        try:
            payload = json.loads(_read_response(client, url, deadline))
        except (httpx.HTTPStatusError, ValueError):
            # Try another available language/automatic track; keep the same
            # overall deadline and never fan out across all caption tracks.
            continue
        if not isinstance(payload, dict) or not isinstance(payload.get("events"), list):
            continue
        parts = []
        for event in payload["events"]:
            if not isinstance(event, dict) or not isinstance(event.get("segs"), list):
                continue
            parts.extend(segment["utf8"] for segment in event["segs"]
                         if isinstance(segment, dict) and isinstance(segment.get("utf8"), str))
        text = " ".join(parts).strip()
        if text:
            return text
    raise RuntimeError("Public captions unavailable")
