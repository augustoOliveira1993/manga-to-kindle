from __future__ import annotations

from PySide6.QtCore import QEventLoop, Qt, QTimer
from PySide6.QtTest import QTest

from manga_to_kindle.application.transfers.smtp_settings import (
    RemoveSmtpProfile,
    SaveSmtpProfile,
    TestSmtpConnection,
)
from manga_to_kindle.domain.transfers import SmtpProfile
from manga_to_kindle.presentation.qt.views.smtp_settings_view import SmtpSettingsView
from manga_to_kindle.presentation.qt.workers.adapter import OperationRunner


class ProfileRepository:
    def __init__(self) -> None:
        self.profile: SmtpProfile | None = None
        self.saved = 0

    def get_profile(self) -> SmtpProfile | None:
        return self.profile

    def save_profile(self, profile: SmtpProfile) -> str | None:
        previous = self.profile.credential_ref if self.profile is not None else None
        self.profile = profile
        self.saved += 1
        return previous

    def remove_profile(self) -> str | None:
        reference = self.profile.credential_ref if self.profile is not None else None
        self.profile = None
        return reference


class FakeVault:
    def __init__(self) -> None:
        self.secrets: dict[str, str] = {}

    def store(self, reference: str, secret: str) -> None:
        self.secrets[reference] = secret

    def get(self, reference: str) -> str:
        return self.secrets[reference]

    def delete(self, reference: str) -> None:
        self.secrets.pop(reference, None)


class FakeSmtpConnection:
    def __init__(self) -> None:
        self.calls = 0

    def test_connection(self, _profile: SmtpProfile, _password: str | None) -> None:
        self.calls += 1


def _wait(runner: OperationRunner, operation_id: str, qt_core_app) -> None:
    loop = QEventLoop()
    runner.finished.connect(lambda finished: loop.quit() if finished == operation_id else None)
    QTimer.singleShot(5000, loop.quit)
    loop.exec()
    qt_core_app.processEvents()
    if runner.active_count:
        idle_loop = QEventLoop()
        runner.idle.connect(idle_loop.quit)
        QTimer.singleShot(5000, idle_loop.quit)
        idle_loop.exec()
        runner.idle.disconnect(idle_loop.quit)


def test_smtp_profile_ui_requires_authorization_and_keeps_secret_out_of_profile(
    qt_core_app,
) -> None:
    runner = OperationRunner()
    repository = ProfileRepository()
    vault = FakeVault()
    connection = FakeSmtpConnection()
    view = SmtpSettingsView(runner)
    view.bind_services(
        repository,
        SaveSmtpProfile(repository, vault),
        RemoveSmtpProfile(repository, vault),
        TestSmtpConnection(repository, vault, connection),
    )
    load_id = next(iter(view._operations))
    _wait(runner, load_id, qt_core_app)

    view.host_input.setText("smtp.example.test")
    view.sender_input.setText("reader@example.test")
    view.recipient_input.setText("device@kindle.com")
    view.username_input.setText("reader@example.test")
    view.password_input.setText("ui-smtp-secret")
    view.sender_check.setChecked(True)
    assert not view.save_button.isEnabled()
    view.recipient_check.setChecked(True)
    assert view.save_button.isEnabled()
    QTest.mouseClick(view.save_button, Qt.MouseButton.LeftButton)
    save_id = next(iter(view._operations))
    _wait(runner, save_id, qt_core_app)

    assert repository.saved == 1
    assert repository.profile is not None
    assert repository.profile.credential_ref in vault.secrets
    assert "ui-smtp-secret" not in repr(repository.profile)
    assert view.password_input.text() == ""
    assert "Nenhuma conexão ou mensagem" in view.status_label.text()

    QTest.mouseClick(view.test_button, Qt.MouseButton.LeftButton)
    test_id = next(iter(view._operations))
    _wait(runner, test_id, qt_core_app)
    assert connection.calls == 1
    assert "Nenhuma mensagem ou arquivo foi enviado" in view.status_label.text()


def test_smtp_settings_disable_save_when_destination_changes_after_confirmation(
    qt_core_app,
) -> None:
    runner = OperationRunner()
    repository = ProfileRepository()
    vault = FakeVault()
    connection = FakeSmtpConnection()
    view = SmtpSettingsView(runner)
    view.bind_services(
        repository,
        SaveSmtpProfile(repository, vault),
        RemoveSmtpProfile(repository, vault),
        TestSmtpConnection(repository, vault, connection),
    )
    load_id = next(iter(view._operations))
    _wait(runner, load_id, qt_core_app)

    view.host_input.setText("smtp.example.test")
    view.sender_input.setText("reader@example.test")
    view.recipient_input.setText("device@kindle.com")
    view.sender_check.setChecked(True)
    view.recipient_check.setChecked(True)
    assert view.save_button.isEnabled()
    view.recipient_input.setFocus()
    view.recipient_input.selectAll()
    QTest.keyClicks(view.recipient_input, "other@kindle.com")

    assert not view.recipient_check.isChecked()
    assert not view.save_button.isEnabled()
    assert repository.saved == 0
