"""Mapeamento de falhas internas para mensagens acionáveis em português."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class StartupErrorInfo:
    code: str
    message: str
    recoverable: bool = True


def describe_startup_error(error: Exception) -> StartupErrorInfo:
    """Retorna código e texto seguro sem incluir mensagem ou dado da exceção."""
    code = getattr(error, "code", "UNEXPECTED_STARTUP_FAILURE")
    if code == "INVALID_LOCAL_CONFIGURATION":
        return StartupErrorInfo(
            code=code,
            message=(
                "A configuração local é inválida e foi preservada. "
                "Revise o arquivo de configuração antes de tentar novamente."
            ),
        )
    if code == "LOCAL_CONFIGURATION_WRITE_FAILED":
        return StartupErrorInfo(
            code=code,
            message=(
                "Não foi possível salvar a configuração local. "
                "Verifique as permissões e o espaço em disco."
            ),
        )
    if code == "APP_PATHS_UNAVAILABLE":
        return StartupErrorInfo(
            code=code,
            message=(
                "Não foi possível criar os diretórios locais do aplicativo. "
                "Verifique as permissões do perfil do Windows."
            ),
        )
    if code == "LOGGING_SETUP_FAILED":
        return StartupErrorInfo(
            code=code,
            message=(
                "Não foi possível preparar o log local. "
                "Verifique as permissões e o espaço em disco."
            ),
        )
    if code == "DATABASE_RECOVERY_FAILED":
        return StartupErrorInfo(
            code=code,
            message=(
                "A migração falhou e a recuperação automática precisa de atenção. "
                "Não remova a base ou o backup local."
            ),
        )
    if code == "DATABASE_MIGRATION_FAILED":
        return StartupErrorInfo(
            code=code,
            message=(
                "Não foi possível atualizar a base local. Os dados anteriores foram preservados. "
                "Tente novamente ou procure suporte."
            ),
        )
    if code == "DATABASE_INITIALIZATION_FAILED":
        return StartupErrorInfo(
            code=code,
            message="Não foi possível validar a base local. O aplicativo não apagou seus dados.",
        )
    return StartupErrorInfo(
        code="UNEXPECTED_STARTUP_FAILURE",
        message=(
            "O aplicativo não conseguiu iniciar. Seus dados foram preservados. "
            "Verifique as permissões do perfil do Windows e tente novamente."
        ),
    )
