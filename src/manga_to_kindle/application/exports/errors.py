"""Erros categorizados da exportação local."""

from __future__ import annotations


class ExportError(RuntimeError):
    code = "EXPORT_FAILED"


class ExportPlanRejected(ExportError):
    code = "EXPORT_PLAN_REJECTED"
