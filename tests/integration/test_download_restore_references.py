from __future__ import annotations

import json
from pathlib import Path

from manga_to_kindle.application.catalog.get_catalog import GetCatalog
from manga_to_kindle.application.downloads.enqueue import EnqueueDownload
from manga_to_kindle.application.downloads.restore_references import RestoreDownloadReferences
from manga_to_kindle.application.providers.registry import ProviderRegistry
from manga_to_kindle.domain.download_job import DownloadState
from manga_to_kindle.infrastructure.network.url_policy import ExternalUrlPolicy
from manga_to_kindle.infrastructure.providers.ndl_provider import NdlProvider
from tests.download_support import make_repository


class FakeResponse:
    status_code = 200
    headers = {"Content-Type": "application/json; charset=utf-8"}
    connected_address = "93.184.216.34"

    def __init__(self, payload: object) -> None:
        self._body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.closed = False

    def read_limited(self, maximum_bytes: int) -> bytes:
        assert len(self._body) <= maximum_bytes
        return self._body

    def close(self) -> None:
        self.closed = True


class FakeTransport:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response
        self.calls = 0

    def get(self, _url, **_kwargs) -> FakeResponse:
        self.calls += 1
        return self.response


def test_explicit_resume_restores_ndl_page_urls_without_a_second_metadata_request(
    tmp_path: Path,
) -> None:
    response = FakeResponse(
        {
            "id": "851650",
            "title": "北斎漫画",
            "volume": "５編",
            "responsibility": "葛飾北斎",
            "page": 2,
        }
    )
    transport = FakeTransport(response)
    policy = ExternalUrlPolicy(lambda _host: ("93.184.216.34",))
    provider = NdlProvider(transport, policy)
    providers = ProviderRegistry((provider,))
    catalog = GetCatalog(providers).execute("https://lab.ndl.go.jp/dl/book/851650")
    database, repository = make_repository(tmp_path, catalog)
    try:
        prepared = EnqueueDownload(repository, policy).prepare(
            provider=provider,
            catalog=catalog,
            selected_chapter_ids=(catalog.chapters[0].id,),
        )
        repository.set_job_state(prepared.snapshot.job.id, DownloadState.RUNNING)
        repository.set_job_state(prepared.snapshot.job.id, DownloadState.INTERRUPTED)

        restored = RestoreDownloadReferences(repository, providers).execute(
            prepared.snapshot.job.id
        )

        assert restored.snapshot.job.state is DownloadState.INTERRUPTED
        assert transport.calls == 1
        assert restored.page_references == prepared.page_references
        assert repository.get_policy_snapshot(prepared.snapshot.job.id) == {
            "provider_id": "ndl-next-digital-library",
            "source_id": "ndl:851650",
            "authorization_reviewed_on": "2026-11-27",
            "allowed_hosts": [
                "dl.ndl.go.jp",
                "dss-r4-prod-contents-download.s3.amazonaws.com",
                "lab.ndl.go.jp",
            ],
            "allowed_ports": [443],
            "allowed_schemes": ["https"],
            "requests_per_minute": 12,
            "authorization_evidence": provider.capabilities.authorization_evidence,
            "authorization_scope": provider.capabilities.authorization_scope,
            "required_attribution": provider.capabilities.required_attribution,
            "removal_policy": provider.capabilities.removal_policy,
        }
    finally:
        database.close()
