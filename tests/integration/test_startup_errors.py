from manga_to_kindle.application.errors import describe_startup_error
from manga_to_kindle.infrastructure.config.settings import InvalidSettingsError
from manga_to_kindle.infrastructure.persistence.database import DatabaseMigrationError


def test_known_startup_errors_have_actionable_portuguese_messages() -> None:
    config = describe_startup_error(InvalidSettingsError(("log_max_bytes",)))
    migration = describe_startup_error(DatabaseMigrationError("migration failed"))

    assert "configuração local" in config.message.lower()
    assert "preservada" in config.message.lower()
    assert "dados anteriores" in migration.message.lower()


def test_unknown_startup_error_does_not_expose_exception_text() -> None:
    failure = describe_startup_error(RuntimeError("conteúdo secreto do livro"))

    assert failure.code == "UNEXPECTED_STARTUP_FAILURE"
    assert "conteúdo secreto" not in failure.message
    assert "tente novamente" in failure.message.lower()
