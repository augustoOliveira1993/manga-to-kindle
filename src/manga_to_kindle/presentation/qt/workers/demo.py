"""Operações de interface sintéticas sem rede ou gravação de conteúdo."""

from __future__ import annotations

from collections.abc import Callable

from manga_to_kindle.domain.catalog import CatalogSnapshot
from manga_to_kindle.presentation.qt.view_models import DemoOutcome, DemoResult
from manga_to_kindle.presentation.qt.workers.adapter import (
    BackgroundOperation,
    CancellationToken,
    ProgressReporter,
)


class DemoOperationError(RuntimeError):
    code = "DEMO_OPERATION_FAILED"


type CatalogQuery = Callable[[str], CatalogSnapshot]


def make_catalog_operation(
    query: CatalogQuery,
    value: str,
    outcome: DemoOutcome,
    *,
    total_steps: int = 8,
    delay_seconds: float = 0.025,
) -> BackgroundOperation:
    """Executa consulta de fixture no worker, com progresso e cancelamento cooperativo."""

    def run(cancellation: CancellationToken, report: ProgressReporter) -> CatalogSnapshot | None:
        for step in range(1, total_steps + 1):
            if cancellation.wait(delay_seconds):
                return None
            report(step, total_steps, "Consultando catálogo local")
            if outcome is DemoOutcome.ERROR and step == max(1, total_steps // 2):
                raise DemoOperationError("Falha simulada.")
        if outcome is DemoOutcome.EMPTY:
            return None
        return query(value)

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

