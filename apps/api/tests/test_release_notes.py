import httpx
import pytest
from fastapi.testclient import TestClient

from beatprints_api.main import app
from beatprints_api.services import release_notes


@pytest.fixture(autouse=True)
def clear_cache():
    release_notes._cache.clear()
    yield
    release_notes._cache.clear()


def test_release_notes_are_cached_and_stale_data_survives_outage(monkeypatch):
    calls = []
    now = [1000.0]
    monkeypatch.setattr(release_notes, "monotonic", lambda: now[0])

    def get(url, **kwargs):
        calls.append(url)
        if len(calls) > 1:
            raise httpx.ConnectError("unavailable")
        return httpx.Response(200, json={"body": "## Release notes"}, request=httpx.Request("GET", url))

    monkeypatch.setattr(release_notes.httpx, "get", get)
    client = TestClient(app)
    for _ in range(2):
        response = client.get("/v1/release-notes", params={"version": "1.3.2"})
        assert response.status_code == 200
        assert response.json()["data"]["body"] == "## Release notes"
    assert len(calls) == 1
    now[0] += 3601
    assert client.get("/v1/release-notes?version=1.3.2").json()["data"]["body"] == "## Release notes"
    assert len(calls) == 2


def test_release_notes_report_unavailable_and_reject_invalid_version(monkeypatch):
    def unavailable(*_args, **_kwargs):
        raise httpx.ConnectTimeout("unavailable")

    monkeypatch.setattr(release_notes.httpx, "get", unavailable)
    client = TestClient(app)
    assert client.get("/v1/release-notes?version=1.3.2").status_code == 503
    assert client.get("/v1/release-notes?version=../../invalid").status_code == 422
