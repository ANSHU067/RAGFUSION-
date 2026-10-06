"""Focused Batch 4 chat service contract tests."""

from uuid import uuid4

from app.services.chat_service import ChatService


def test_chat_service_preserves_persisted_generation_settings():
    service = ChatService(
        db=None,  # type: ignore[arg-type]
        user_id=uuid4(),
        rag_pipeline=object(),  # type: ignore[arg-type]
        model_name="configured-model",
        provider="groq",
        configured_temperature=0.0,
        configured_max_tokens=2048,
    )

    assert service.model_name == "configured-model"
    assert service.provider == "groq"
    assert service.configured_temperature == 0.0
    assert service.configured_max_tokens == 2048
