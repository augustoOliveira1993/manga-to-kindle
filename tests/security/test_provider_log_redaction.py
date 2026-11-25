from __future__ import annotations

import logging

from manga_to_kindle.application.providers.resolve_provider import provider_error_message
from manga_to_kindle.domain.providers import UnsupportedSource


def test_provider_errors_and_user_messages_never_echo_sensitive_url(caplog) -> None:
    sensitive_url = "https://user:secret@example.test/manga?token=private"
    error = UnsupportedSource()
    caplog.set_level(logging.INFO)
    logging.getLogger("manga_to_kindle.providers").info("%s", error)
    message = provider_error_message(error)

    assert "secret" not in str(error)
    assert "token" not in str(error)
    assert sensitive_url not in caplog.text
    assert "private" not in message
    assert "suportada" in message.lower()
