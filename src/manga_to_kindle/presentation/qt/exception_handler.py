"""Encaminha exceções não tratadas ao logger e à interface Qt."""

from __future__ import annotations

import sys
import threading
from logging import Logger
from types import TracebackType

from PySide6.QtCore import QObject, Signal

from manga_to_kindle.application.errors import StartupErrorInfo, describe_startup_error


class QtExceptionReporter(QObject):
    reported = Signal(object)

    def __init__(self, logger: Logger) -> None:
        super().__init__()
        self._logger = logger
        self._previous_sys_hook = sys.excepthook
        self._previous_thread_hook = threading.excepthook
        self._installed = False

    def install(self) -> None:
        if self._installed:
            return
        sys.excepthook = self._handle_sys_exception
        threading.excepthook = self._handle_thread_exception
        self._installed = True

    def restore(self) -> None:
        if not self._installed:
            return
        sys.excepthook = self._previous_sys_hook
        threading.excepthook = self._previous_thread_hook
        self._installed = False

    def _report(self, error: Exception) -> StartupErrorInfo:
        info = describe_startup_error(error)
        log_error = self._logger.error
        log_error(
            "unhandled exception code=%s exception_type=%s",
            info.code,
            type(error).__name__,
        )
        self.reported.emit(info)
        return info

    def _handle_sys_exception(
        self,
        exception_type: type[BaseException],
        exception: BaseException,
        _: TracebackType | None,
    ) -> None:
        safe_exception = exception if isinstance(exception, Exception) else Exception()
        self._report(safe_exception)

    def _handle_thread_exception(self, args: threading.ExceptHookArgs) -> None:
        safe_exception = args.exc_value
        error = safe_exception if isinstance(safe_exception, Exception) else Exception()
        self._report(error)
