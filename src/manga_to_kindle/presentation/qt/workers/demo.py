"""Consulta offline do catálogo e operações de demonstração explícitas."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from manga_to_kindle.application.catalog.errors import CatalogRefreshCancelled
from manga_to_kindle.domain.catalog import CatalogSnapshot
from manga_to_kindle.presentation.qt.view_models import DemoOutcome, DemoResult
from manga_to_kindle.presentation.qt.workers.adapter import (
    BackgroundOperation,
    CancellationToken,
    ProgressReporter,
)


class DemoOperationError(RuntimeError):
    code = "DEMO_OPERATION_FAILED"


class CatalogQuery(Protocol):
    def __call__(
        self,
        value: str,
        *,
        is_cancelled: Callable[[], bool] | None = None,
    ) -> CatalogSnapshot: ...


def make_catalog_operation(
    query: CatalogQuery,
    value: str,
) -> BackgroundOperation:
    """Executa a consulta atual no worker e não publica resultado cancelado."""

    def run(cancellation: CancellationToken, report: ProgressReporter) -> CatalogSnapshot | None:
        if cancellation.cancelled:
            return None
        report(0, 1, "Consultando catálogo local")
        try:
            snapshot = query(value, is_cancelled=lambda: cancellation.cancelled)
        except CatalogRefreshCancelled:
            if cancellation.cancelled:
                return None
            raise
        if cancellation.cancelled:
            return None
        report(1, 1, "Catálogo recebido")
        return snapshot

    return run


def make_demo_operation(
    outcome: DemoOutcome = DemoOutcome.SUCCESS,
    *,
    total_steps: int = 24,
    delay_seconds: float = 0.08,
    summary: str = "Operação de demonstração concluída.",
) -> BackgroundOperation:
    """Cria trabalho cancelável de teste; a função só espera e emite progresso."""

    def run(
        cancellation: CancellationToken,
        report: ProgressReporter,
    ) -> DemoResult:
        midpoint = max(1, total_steps // 2)
        for step in range(1, total_steps + 1):
            if cancellation.wait(delay_seconds):
                break
            report(step, total_steps, "Etapa simulada")
            if outcome is DemoOutcome.ERROR and step == midpoint:
                raise DemoOperationError("Erro de demonstração.")
        if outcome is DemoOutcome.EMPTY:
            return DemoResult(simulated=True, summary="A demonstração não encontrou itens.")
        return DemoResult(simulated=True, summary=summary)

    return run

