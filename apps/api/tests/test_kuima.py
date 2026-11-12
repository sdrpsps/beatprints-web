from io import BytesIO
from pathlib import Path
from dataclasses import replace

import httpx
import pytest
from PIL import Image

from beatprints_api.exceptions import UpstreamError
from beatprints_api.integrations.destinations import apple_music
from beatprints_api.integrations.destinations.kuima import KuimaClient
from beatprints_api.integrations.destinations import kuima


@pytest.fixture(autouse=True)
def configured_service(monkeypatch):
    monkeypatch.setattr(kuima, "settings", replace(kuima.settings, wechat_qr_base_url="http://example.test"))


def test_kuima_sends_logo_and_filled_badge_options(tmp_path: Path) -> None:
    icon = tmp_path / 'icon.png'
    Image.new('RGBA', (10, 10), 'black').save(icon)
    buffer = BytesIO()
    Image.new('RGB', (518, 518), 'black').save(buffer, format='PNG')
    def handler(request: httpx.Request) -> httpx.Response:
        import json
        body = json.loads(request.content)
        assert body['text'] == 'https://example.com/song'
        assert body['badge'] == 'none'
        assert body['fillBadge'] is True
        assert body['version'] == '2'
        assert body['mask'] == 24
        assert body['margin'] == 19
        assert body['logo'].startswith('data:image/png;base64,')
        return httpx.Response(200, headers={'content-type': 'image/png'}, content=buffer.getvalue())
    client = KuimaClient()
    client.http.close()
    client.http = httpx.Client(transport=httpx.MockTransport(handler))
    result = client.image('https://example.com/song', icon, (50, 47, 48), version='2', mask=24, margin=19)
    assert result.getpixel((10, 10)) == (50, 47, 48, 255)
    client.http.close()


def test_kuima_reports_service_errors(tmp_path: Path) -> None:
    icon = tmp_path / 'icon.png'
    Image.new('RGBA', (10, 10), 'black').save(icon)
    client = KuimaClient()
    client.http.close()
    client.http = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(400)))
    with pytest.raises(UpstreamError, match='HTTP 400'):
        client.image('https://example.com/song', icon, (0, 0, 0))
    client.http.close()


def test_apple_shortens_track_and_album_urls() -> None:
    assert apple_music._scannable_link('https://music.apple.com/cn/album/title/535391943?i=535391944&uo=4') == 'https://music.apple.com/cn/song/535391944'
    assert apple_music._scannable_link('https://music.apple.com/us/album/title/535391943?uo=4') == 'https://music.apple.com/us/album/535391943'


def test_wechat_qr_requires_configuration(monkeypatch, tmp_path: Path) -> None:
    from beatprints_api.exceptions import IntegrationNotConfiguredError

    monkeypatch.setattr(kuima, "settings", replace(kuima.settings, wechat_qr_base_url=None))
    with pytest.raises(IntegrationNotConfiguredError, match="not configured"):
        KuimaClient().image("https://example.com", tmp_path / "icon.png", (0, 0, 0))


def test_capabilities_report_configuration(monkeypatch) -> None:
    from fastapi.testclient import TestClient
    from beatprints_api.api.routes import system
    from beatprints_api.main import app

    client = TestClient(app)
    for url, available in [(None, False), ("http://example.test", True)]:
        monkeypatch.setattr(system, "settings", replace(system.settings, wechat_qr_base_url=url))
        assert client.get("/capabilities").json()["data"]["wechat_qr"] is available
