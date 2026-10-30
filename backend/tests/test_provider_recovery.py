"""Provider failures remain bounded and distinct from user authentication."""

import json
import logging
import os
import time
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest
from groq import AuthenticationError
from requests import Response, Session
from requests.exceptions import HTTPError, Timeout
from youtube_transcript_api import NoTranscriptFound, YouTubeRequestFailed

from app.config.settings import GROQ_KEY_ALIASES, Settings, configure_groq_environment
from app.core.exceptions import GroqConfigurationError
from app.rag.pipelines.rag_pipeline import RAGPipeline
from app.services import youtube_service as youtube
from app.services import youtube_fallback as fallback

VIDEO = "dQw4w9WgXcQ"
SAFE_ERROR = "LLM configuration error: Invalid Groq API key on server"


@pytest.mark.parametrize("canonical,legacy,generic,expected", [
    ("", "", ' "gsk_generic" ', "gsk_generic"),
    ("placeholder", "bad", "gsk_generic", "gsk_generic"),
    ("", "gsk_legacy", "invalid", "gsk_legacy"),
    ("gsk_canonical", "gsk_legacy", "gsk_generic", "gsk_canonical"),
    ("gsk_", "gsk_legacy", "", "gsk_legacy"),
])
def test_key_selection_skips_invalid_aliases(monkeypatch, canonical, legacy, generic, expected):
    for name, value in zip(GROQ_KEY_ALIASES, (canonical, legacy, generic)):
        monkeypatch.setenv(name, value)
    assert Settings(_env_file=None).groq_api_key == expected


def test_dotenv_selection_and_explicit_values(monkeypatch, tmp_path):
    for name in GROQ_KEY_ALIASES:
        monkeypatch.delenv(name, raising=False)
    path = tmp_path / ".env"
    path.write_text('DOCPRO_GROQ_API_KEY=""\nGROQ_API_KEY="gsk_dotenv"\n')
    assert Settings(_env_file=path).groq_api_key == "gsk_dotenv"
    assert Settings(_env_file=path, groq_api_key="gsk_explicit").groq_api_key == "gsk_explicit"


def test_masked_startup_logging_never_emits_secret(monkeypatch, caplog):
    monkeypatch.setenv("GROQ_API_KEY", "")
    settings = Settings(_env_file=None, groq_api_key="gsk_secret_that_must_not_be_logged")
    with caplog.at_level(logging.INFO):
        configure_groq_environment(settings, log_status=True)
    assert os.environ["GROQ_API_KEY"] == settings.groq_api_key
    assert "gsk_****..." in caplog.text
    assert f"len={len(settings.groq_api_key)}" in caplog.text
    assert settings.groq_api_key not in caplog.text
    assert "secret_that" not in caplog.text


def failing_pipeline():
    error = AuthenticationError(
        "private provider response", response=httpx.Response(
            401, request=httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")),
        body={"secret": "must not leak"},
    )
    pipeline = RAGPipeline.__new__(RAGPipeline)
    pipeline.llm = Mock()
    pipeline.llm.invoke.side_effect = error
    return pipeline


def test_groq_401_is_translated_without_exposing_provider_body():
    with pytest.raises(GroqConfigurationError) as error:
        failing_pipeline()._generate_response({"messages": [], "metadata": {}})
    assert error.value.status_code == 502
    assert error.value.message == SAFE_ERROR


def test_chat_rest_and_sse_report_server_key_error(client, auth_headers, monkeypatch):
    from main import app
    pipeline = failing_pipeline()
    pipeline.graph = SimpleNamespace(invoke=lambda state: pipeline._generate_response({
        **state, "messages": [{"role": "user", "content": state["question"]}],
    }))
    monkeypatch.setattr(app.state, "rag_pipeline", pipeline)
    response = client.post("/api/v1/chat", headers=auth_headers, json={"message": "Hello"})
    assert response.status_code == 502
    assert response.json()["detail"] == SAFE_ERROR
    assert response.json()["error"]["message"] == SAFE_ERROR
    stream = client.post("/api/v1/chat/stream", headers=auth_headers, json={"message": "Hello"})
    assert SAFE_ERROR in stream.text
    assert "private provider response" not in stream.text + response.text
    assert "must not leak" not in stream.text + response.text


def test_native_headers_are_preserved():
    with Session() as native, youtube.TranscriptSession(time.monotonic() + 60) as session:
        assert session.headers == native.headers


@pytest.mark.parametrize("manual", [True, False])
def test_missing_english_uses_any_available_transcript(monkeypatch, manual):
    track = SimpleNamespace(is_generated=not manual, language_code="hi", fetch=Mock(return_value=[{"text": "नमस्ते"}]))
    api = Mock()
    api.fetch.side_effect = NoTranscriptFound(VIDEO, ["en"], [])
    api.list.return_value = [track]
    monkeypatch.setattr(youtube, "YouTubeTranscriptApi", lambda **kwargs: api)
    assert youtube._fetch_transcript_sync(VIDEO, ["en"], time.monotonic() + 60) == "नमस्ते"
    track.fetch.assert_called_once()


def blocked_error(status=403):
    response = Response()
    response.status_code = status
    return HTTPError("HTTP provider failure", response=response)


def test_wrapped_403_uses_fallback_with_same_deadline(monkeypatch):
    def fetch(*args, **kwargs):
        try:
            raise blocked_error()
        except HTTPError as exc:
            raise YouTubeRequestFailed(VIDEO, exc)
    api = Mock()
    api.fetch.side_effect = fetch
    monkeypatch.setattr(youtube, "YouTubeTranscriptApi", lambda **kwargs: api)
    recover = Mock(return_value="Recovered captions")
    monkeypatch.setattr(youtube, "fetch_watch_page_captions", recover)
    deadline = time.monotonic() + 60
    assert youtube._fetch_transcript_sync(VIDEO, ["en"], deadline) == "Recovered captions"
    assert recover.call_args.args == (VIDEO, ["en"], deadline)
    recover.assert_called_once()


@pytest.mark.parametrize("status", [401, 429, 500])
def test_http_failures_trigger_caption_fallback(status):
    assert fallback.should_use_caption_fallback(blocked_error(status))


class BoundedResponse:
    def __init__(self, body, status=200):
        self.body = body.encode()
        self.status_code = status

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def raise_for_status(self):
        if self.status_code >= 400:
            raise blocked_error(self.status_code)

    def iter_bytes(self):
        chunk_size = 16 * 1024
        for start in range(0, len(self.body), chunk_size):
            yield self.body[start:start + chunk_size]


def test_watch_page_extraction_uses_json_parser_and_fixed_caption_origin():
    player = {"captions": {"playerCaptionsTracklistRenderer": {"captionTracks": [
        {"baseUrl": "https://www.youtube.com/api/timedtext?v=" + VIDEO + "&fmt=srv3",
         "languageCode": "en-IN", "kind": "asr"},
    ]}}}
    http = Mock()
    http.stream.side_effect = [
        BoundedResponse('<script>var ytInitialPlayerResponse = ' + json.dumps(player) + ';</script>'),
        BoundedResponse(json.dumps({"events": [{"segs": [{"utf8": "Hello"}, {"utf8": "world"}]}]})),
    ]
    assert fallback._fetch_captions(http, VIDEO, ["en"], time.monotonic() + 60) == "Hello world"
    assert "fmt=json3" in http.stream.call_args.args[1]
    assert "fmt=srv3" not in http.stream.call_args.args[1]
    assert all(call.kwargs["follow_redirects"] is False for call in http.stream.call_args_list)
    assert all(call.kwargs["timeout"].read <= 20 for call in http.stream.call_args_list)


@pytest.mark.parametrize("url", [
    "http://169.254.169.254/api/timedtext", "https://127.0.0.1/api/timedtext",
    "https://www.youtube.com.evil.test/api/timedtext", "https://user@www.youtube.com/api/timedtext",
    "https://www.youtube.com:8443/api/timedtext", "https://www.youtube.com/redirect?url=http://localhost",
])
def test_caption_urls_cannot_escape_fixed_public_endpoint(url):
    with pytest.raises(ValueError):
        fallback._caption_url({"baseUrl": url})


def test_fallback_caps_body_and_refuses_redirects_or_expired_deadline(monkeypatch):
    http = Mock()
    monkeypatch.setattr(fallback, "MAX_RESPONSE_BYTES", 8)
    http.stream.return_value = BoundedResponse("x" * 9)
    with pytest.raises(RuntimeError, match="size limit"):
        fallback._read_response(http, "https://www.youtube.com/watch", time.monotonic() + 60)
    http.stream.return_value = BoundedResponse("", status=302)
    with pytest.raises(RuntimeError, match="Unexpected"):
        fallback._read_response(http, "https://www.youtube.com/watch", time.monotonic() + 60)
    with pytest.raises(Timeout):
        fallback._read_response(http, "https://www.youtube.com/watch", 0)
    assert http.stream.call_count == 2
