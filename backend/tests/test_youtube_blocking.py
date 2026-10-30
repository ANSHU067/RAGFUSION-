"""Real ingestion control flow with deterministic upstream HTTP responses."""

import json
import time
from unittest.mock import Mock

import httpx
import pytest
import youtube_transcript_api
from youtube_transcript_api import RequestBlocked, IpBlocked

from app.services import youtube_service as youtube
from app.services import youtube_fallback as fallback

VIDEO = "dQw4w9WgXcQ"


def install_http(monkeypatch, handler):
    client_class = httpx.Client
    options = []

    def client(**kwargs):
        options.append(kwargs)
        return client_class(transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr(fallback.httpx, "Client", client)
    return options


def install_blocked_api(monkeypatch, error):
    api = Mock()
    api.fetch.side_effect = error
    monkeypatch.setattr(youtube, "YouTubeTranscriptApi", lambda **kwargs: api)


def player_page(tracks=1, status="OK"):
    player = {
        "playabilityStatus": {"status": status}, "videoDetails": {"videoId": VIDEO},
        "captions": {"playerCaptionsTracklistRenderer": {"captionTracks": [
            {"languageCode": "hi", "kind": "asr", "baseUrl":
             f"https://www.youtube.com/api/timedtext?v={VIDEO}&track={i}"}
            for i in range(tracks)
        ]}},
    }
    return '<script>window["ytInitialPlayerResponse"] = ' + json.dumps(player) + ';</script>'


@pytest.mark.parametrize("error_type", [RequestBlocked, IpBlocked])
def test_sdk_blocking_recovers_via_httpx_with_separate_browser_headers(monkeypatch, error_type):
    install_blocked_api(monkeypatch, error_type(VIDEO))
    requests = []

    def respond(request):
        requests.append(request)
        assert request.url.host == "www.youtube.com"
        assert request.headers["user-agent"] in fallback.BROWSER_PROFILES
        assert request.extensions["timeout"]["read"] <= 20
        if request.url.path == "/watch":
            return httpx.Response(200, text=player_page())
        return httpx.Response(200, json={"events": [{"segs": [{"utf8": "नमस्ते दुनिया"}]}]})

    options = install_http(monkeypatch, respond)
    result = youtube._fetch_transcript_sync(VIDEO, ["en"], time.monotonic() + 60)
    assert result == "नमस्ते दुनिया"
    assert len(requests) == 2
    assert requests[0].headers["user-agent"] == requests[1].headers["user-agent"]
    assert options[0]["follow_redirects"] is False


def test_legacy_too_many_requests_class_is_supported(monkeypatch):
    class TooManyRequests(Exception):
        pass
    monkeypatch.setattr(youtube_transcript_api, "TooManyRequests", TooManyRequests, raising=False)
    install_blocked_api(monkeypatch, TooManyRequests())
    recover = Mock(return_value="captions")
    monkeypatch.setattr(youtube, "fetch_watch_page_captions", recover)
    assert youtube._fetch_transcript_sync(VIDEO, ["en"], time.monotonic() + 60) == "captions"
    recover.assert_called_once()


@pytest.mark.parametrize("prefix", [
    "var ytInitialPlayerResponse = ", 'window["ytInitialPlayerResponse"] = ',
    '"ytInitialPlayerResponse": ',
])
def test_player_variants_are_decoded_without_running_javascript(prefix):
    player = {"captions": {}, "title": "braces { } and quoted content"}
    assert fallback._extract_player(prefix + json.dumps(player) + ";ignored()") == player


def test_track_failures_try_other_languages_with_hard_request_cap(monkeypatch):
    requests = []
    def respond(request):
        requests.append(request)
        if request.url.path == "/watch":
            return httpx.Response(200, text=player_page(tracks=10))
        return httpx.Response(403)
    install_http(monkeypatch, respond)
    with pytest.raises(RuntimeError, match="captions unavailable"):
        fallback.fetch_watch_page_captions(VIDEO, ["en"], time.monotonic() + 60)
    assert len(requests) == 4  # One HTML fetch plus at most three caption tracks.


def test_empty_track_uses_next_track(monkeypatch):
    def respond(request):
        if request.url.path == "/watch":
            return httpx.Response(200, text=player_page(tracks=2))
        if request.url.params["track"] == "0":
            return httpx.Response(200, json={"events": []})
        return httpx.Response(200, json={"events": [{"segs": [{"utf8": "captions"}]}]})
    install_http(monkeypatch, respond)
    assert fallback.fetch_watch_page_captions(VIDEO, ["en"], time.monotonic() + 60) == "captions"


@pytest.mark.parametrize("mode,expected_status", [("blocked", 503), ("timeout", 504), ("empty", 503)])
def test_failed_fallback_is_not_bad_request(client, auth_headers, monkeypatch, mode, expected_status):
    install_blocked_api(monkeypatch, RequestBlocked(VIDEO))
    def respond(request):
        if mode == "timeout":
            raise httpx.ReadTimeout("private upstream response", request=request)
        return httpx.Response(403 if mode == "blocked" else 200, text="No public captions")
    install_http(monkeypatch, respond)
    response = client.post("/api/v1/youtube/ingest", headers=auth_headers,
                           json={"url": f"https://www.youtube.com/watch?v={VIDEO}"})
    assert response.status_code == expected_status
    assert "private upstream" not in response.text
    if expected_status == 503:
        assert response.headers["retry-after"] == "60"
    assert client.get("/api/v1/youtube", headers=auth_headers).json()["total"] == 0


def test_ingestion_finishes_ready_after_primary_api_is_blocked(client, auth_headers, monkeypatch):
    install_blocked_api(monkeypatch, RequestBlocked(VIDEO))
    def respond(request):
        if request.url.path == "/watch":
            return httpx.Response(200, text=player_page())
        return httpx.Response(200, json={"events": [{"segs": [{"utf8": "Recovered public transcript."}]}]})
    install_http(monkeypatch, respond)
    async def embed(chunks, model_name):
        return [[0.1] * 384 for _ in chunks]
    monkeypatch.setattr(youtube, "generate_embeddings", embed)
    index = Mock()
    monkeypatch.setattr(youtube, "add_youtube_chunks_to_retriever", index)
    response = client.post("/api/v1/youtube/ingest", headers=auth_headers,
                           json={"url": f"https://www.youtube.com/watch?v={VIDEO}"})
    assert response.status_code == 202, response.text
    assert response.json()["status"] == "ready"
    assert response.json()["total_chunks"] == 1
    index.assert_called_once()
