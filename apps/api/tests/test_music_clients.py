import ast
import json
import shutil
import subprocess
import sys
from pathlib import Path

import httpx
import pytest

from beatprints_api.exceptions import (
    UnsupportedCatalogSourceError,
    UnsupportedDestinationError,
    UnsupportedLyricsSourceError,
    UpstreamError,
)
from beatprints_api.integrations.catalog import netease_music as netease_catalog
from beatprints_api.integrations.catalog import qq_music as qq_catalog
from beatprints_api.integrations.catalog import registry as catalog_registry
from beatprints_api.integrations.clients.netease_music import NetEaseMusicClient
from beatprints_api.integrations.clients.qq_music import QQMusicClient
from beatprints_api.integrations.destinations import (
    netease_music as netease_destination,
)
from beatprints_api.integrations.destinations import qq_music as qq_destination
from beatprints_api.integrations.destinations import registry as destination_registry
from beatprints_api.integrations.lyrics import netease as netease_lyrics
from beatprints_api.integrations.lyrics import qq_music as qq_lyrics
from beatprints_api.integrations.lyrics import registry as lyrics_registry

FIXTURES = Path(__file__).parent / "fixtures" / "lyrics"


@pytest.mark.parametrize(
    ("client_type", "prefix", "track_id", "album_id"),
    [
        (QQMusicClient, "qq_music", "studio-mid", "album-mid"),
        (NetEaseMusicClient, "netease", 102, 103),
    ],
)
def test_clients_share_platform_operations_and_keep_exact_ids(
    client_type, prefix, track_id, album_id
) -> None:
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if "search" in request.url.path:
            filename = f"{prefix}_search.json"
        elif "lyric" in request.url.path:
            filename = f"{prefix}_lyrics.json"
        else:
            return httpx.Response(200, json={})
        return httpx.Response(200, json=json.loads((FIXTURES / filename).read_text()))

    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        client = client_type(http)
        assert client.search("fixture song", "track", 10)
        client.search("fixture album", "album", 5)
        if prefix == "qq_music":
            client.track(track_id)
        else:
            client.tracks([track_id])
        client.album(album_id)
        assert client.lyrics(track_id)

    track_search, album_search, track, album, lyrics = requests
    if prefix == "qq_music":
        assert dict(track_search.url.params) == {
            "format": "json",
            "p": "1",
            "n": "10",
            "w": "fixture song",
            "t": "0",
        }
        assert album_search.url.params["t"] == "8"
        assert track.url.params["songmid"] == str(track_id)
        assert album.url.params["albummid"] == str(album_id)
        assert lyrics.url.params["songmid"] == str(track_id)
        assert lyrics.url.params["nobase64"] == "1"
    else:
        assert dict(track_search.url.params) == {
            "type": "1",
            "s": "fixture song",
            "limit": "10",
            "offset": "0",
        }
        assert album_search.url.params["type"] == "10"
        assert track.url.params["ids"] == f"[{track_id}]"
        assert album.url.path.endswith(f"/{album_id}")
        assert lyrics.url.params["id"] == str(track_id)
    assert album_search.url.params.get("n", album_search.url.params.get("limit")) == "5"


@pytest.mark.parametrize(
    ("client_type", "error_payload"),
    [
        (QQMusicClient, {"code": 1}),
        (QQMusicClient, {"retcode": 1}),
        (NetEaseMusicClient, {"code": 500}),
    ],
)
def test_client_rejects_platform_error_responses(client_type, error_payload) -> None:
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(200, json=error_payload)
        )
    ) as http:
        with pytest.raises(UpstreamError):
            client_type(http).search("track", "track", 10)


@pytest.mark.parametrize("client_type", [QQMusicClient, NetEaseMusicClient])
@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, json=[]),
        httpx.Response(200, text="bad json"),
        httpx.Response(503),
    ],
)
def test_client_rejects_invalid_and_http_error_responses(client_type, response) -> None:
    with httpx.Client(transport=httpx.MockTransport(lambda _request: response)) as http:
        with pytest.raises(UpstreamError):
            client_type(http).search("track", "track", 10)


@pytest.mark.parametrize(
    ("catalog", "destination", "lyrics", "attribute"),
    [
        (qq_catalog, qq_destination, qq_lyrics, "qq_music_client"),
        (netease_catalog, netease_destination, netease_lyrics, "netease_music_client"),
    ],
)
def test_roles_use_the_same_platform_client(
    catalog, destination, lyrics, attribute
) -> None:
    assert getattr(catalog, attribute) is getattr(destination, attribute)
    assert getattr(catalog, attribute) is getattr(lyrics, attribute)


@pytest.mark.parametrize(
    "platform", ["spotify", "apple_music", "qq_music", "netease_music"]
)
def test_disabling_one_capability_keeps_the_other_enabled(
    monkeypatch, platform
) -> None:
    with monkeypatch.context() as patch:
        patch.setattr(
            destination_registry,
            "_adapters",
            {
                key: value
                for key, value in destination_registry._adapters.items()
                if key != platform
            },
        )
        with pytest.raises(UnsupportedDestinationError):
            destination_registry.get_destination_adapter(platform)
        assert catalog_registry.get_catalog_adapter(platform).key == platform

    with monkeypatch.context() as patch:
        patch.setattr(
            catalog_registry,
            "_adapters",
            {
                key: value
                for key, value in catalog_registry._adapters.items()
                if key != platform
            },
        )
        with pytest.raises(UnsupportedCatalogSourceError):
            catalog_registry.get_catalog_adapter(platform)
        assert destination_registry.get_destination_adapter(platform).key == platform

    if platform in ("qq_music", "netease_music"):
        lyrics_key = "netease" if platform == "netease_music" else platform
        with monkeypatch.context() as patch:
            patch.setattr(
                lyrics_registry,
                "_adapters",
                {
                    key: value
                    for key, value in lyrics_registry._adapters.items()
                    if key != lyrics_key
                },
            )
            with pytest.raises(UnsupportedLyricsSourceError):
                lyrics_registry.get_lyrics_source(lyrics_key)
            assert catalog_registry.get_catalog_adapter(platform).key == platform
            assert (
                destination_registry.get_destination_adapter(platform).key == platform
            )


def test_importing_clients_does_not_register_integrations() -> None:
    script = """
import importlib
import sys
for name in ('spotify', 'apple_music', 'qq_music', 'netease_music', 'kuima'):
    importlib.import_module('beatprints_api.integrations.clients.' + name)
for role in ('catalog', 'destinations', 'lyrics', 'labels'):
    assert 'beatprints_api.integrations.' + role + '.registry' not in sys.modules
"""
    subprocess.run([sys.executable, "-c", script], check=True)


@pytest.mark.parametrize(
    ("role", "module", "key"),
    [
        (role, platform, platform)
        for role in ("catalog", "destinations")
        for platform in ("spotify", "apple_music", "qq_music", "netease_music")
    ]
    + [
        ("lyrics", "qq_music", "qq_music"),
        ("lyrics", "netease", "netease"),
        ("lyrics", "lrclib", "lrclib"),
        ("labels", "spotify", "spotify"),
    ],
)
def test_removing_registry_import_does_not_enable_adapter_indirectly(
    tmp_path, role, module, key
) -> None:
    source = Path(qq_catalog.__file__).resolve().parents[2]
    package = tmp_path / "beatprints_api"
    shutil.copytree(source, package, ignore=shutil.ignore_patterns("__pycache__"))
    registry = package / "integrations" / role / "registry.py"
    text = registry.read_text()
    imports = [
        node
        for node in ast.walk(ast.parse(text))
        if isinstance(node, ast.ImportFrom)
        and node.module == f"beatprints_api.integrations.{role}"
        and any(alias.name == module for alias in node.names)
    ]
    assert len(imports) == 1
    lines = text.splitlines(keepends=True)
    del lines[imports[0].lineno - 1 : imports[0].end_lineno]
    registry.write_text("".join(lines))

    script = """
import importlib
import sys
sys.path.insert(0, sys.argv[1])
role, module, key = sys.argv[2:]
registries = {
    name: importlib.import_module('beatprints_api.integrations.' + name + '.registry')
    for name in ('catalog', 'destinations', 'lyrics', 'labels')
}
registry = registries[role]
entries = registry._resolvers if role == 'labels' else registry._adapters
assert key not in entries
assert 'beatprints_api.integrations.' + role + '.' + module not in sys.modules
"""
    subprocess.run(
        [sys.executable, "-c", script, str(tmp_path), role, module, key], check=True
    )
