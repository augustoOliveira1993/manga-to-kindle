"""Erros tipados da consulta e atualização de catálogos."""

from __future__ import annotations


class CatalogRefreshCancelled(RuntimeError):
    code = "OPERATION_CANCELLED"
