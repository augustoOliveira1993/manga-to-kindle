from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from manga_to_kindle.application.settings.preferences import (
    GetApplicationPreferences,
    ResetPreferences,
)
from manga_to_kindle.domain.settings import ApplicationPreferences, DeviceProfileSettings
from manga_to_kindle.infrastructure.paths import AppPaths
from manga_to_kindle.infrastructure.persistence.database import SQLiteDatabase
from manga_to_kindle.infrastructure.persistence.models import MangaRecord, SmtpProfileRecord
from manga_to_kindle.infrastructure.persistence.settings_repository import SettingsRepository


def test_reset_preserves_custom_profiles_exports_and_credential_references(tmp_path: Path) -> None:
    paths = AppPaths.from_root(tmp_path / "profile")
    paths.ensure()
    database = SQLiteDatabase(paths.database_file)
    database.initialize()
    repository = SettingsRepository(database)
    initial = GetApplicationPreferences(repository, paths).execute()
    profile = DeviceProfileSettings(
        id=uuid4(),
        name="Meu leitor",
        model="Perfil personalizado",
        generation=None,
        width=600,
        height=900,
    )
    repository.save_custom_profile(profile)
    changed = ApplicationPreferences(
        selected_profile_id=profile.id,
        download_concurrency=1,
        download_directory=initial.download_directory,
        export_directory=initial.export_directory,
        cache_directory=initial.cache_directory,
        cache_limit_bytes=2 * 1024 * 1024 * 1024,
        cache_retention_days=15,
    )
    repository.save_preferences(changed)
    with database.unit_of_work() as session:
        session.add(
            MangaRecord(
                id=uuid4(),
                title="Coleção preservada",
                provider_id="local-test",
                simulated=False,
            )
        )
        session.add(
            SmtpProfileRecord(
                id=1,
                host="smtp.example.test",
                port=587,
                tls_mode="starttls",
                sender="reader@example.test",
                recipient="device@example.test",
                username="reader@example.test",
                credential_ref="windows-credential-reference",
                sender_authorized=True,
                recipient_confirmed=True,
            )
        )
    export_sentinel = tmp_path / "outside-export.epub"
    export_sentinel.write_bytes(b"keep outside preferences reset")

    ResetPreferences(repository, paths).execute(confirmed=True)

    assert repository.get_preferences() == initial
    assert repository.list_custom_profiles() == (profile,)
    with database.unit_of_work() as session:
        assert session.query(MangaRecord).filter_by(title="Coleção preservada").count() == 1
        smtp_profile = session.get(SmtpProfileRecord, 1)
        assert smtp_profile is not None
        assert smtp_profile.credential_ref == "windows-credential-reference"
    assert export_sentinel.read_bytes() == b"keep outside preferences reset"
    database.close()
