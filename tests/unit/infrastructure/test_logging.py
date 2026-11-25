from pathlib import Path

from manga_to_kindle.infrastructure.config.settings import AppSettings
from manga_to_kindle.infrastructure.logging import configure_logging


def test_logs_rotate_and_redact_secrets_urls_and_book_content(tmp_path: Path) -> None:
    manager = configure_logging(
        tmp_path / "application.log",
        AppSettings(log_max_bytes=64 * 1024, log_backup_count=3),
        logger_name="test.foundation.rotation",
    )
    manager.logger.info("password=s3cr3t token=private-token")
    manager.logger.info("source=https://example.test/manga?key=private")
    manager.logger.info('book_title="Título privado" page_content="imagem privada"')
    for index in range(100):
        manager.logger.info("evento %s %s", index, "x" * 1200)
    manager.close()

    log_files = list(tmp_path.glob("application.log*"))
    contents = "\n".join(path.read_text(encoding="utf-8") for path in log_files)

    assert len(log_files) <= 4
    assert "s3cr3t" not in contents
    assert "private-token" not in contents
    assert "example.test" not in contents
    assert "Título privado" not in contents
    assert "imagem privada" not in contents
    assert "[REDACTED]" in contents


def test_exception_logging_keeps_type_but_drops_sensitive_message(tmp_path: Path) -> None:
    manager = configure_logging(
        tmp_path / "application.log",
        AppSettings(),
        logger_name="test.foundation.exception",
    )
    try:
        raise RuntimeError("password=segredo-do-teste")
    except RuntimeError:
        manager.logger.exception("falha interna")
    manager.close()

    contents = (tmp_path / "application.log").read_text(encoding="utf-8")

    assert "RuntimeError" in contents
    assert "segredo-do-teste" not in contents
