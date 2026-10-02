from pathlib import Path
import socket

import httpcore
import httpx
import pytest

from BeatPrints.deez import TrackMetadata
from beatprints_api.services import rendering


def test_download_cover_accepts_image_jpg_content_type(
    monkeypatch, tmp_path: Path
) -> None:
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(
                200,
                headers={"content-type": "image/jpg"},
                content=b"jpeg-content",
            )
        )
    )
    monkeypatch.setattr(rendering, "cover_client", client)
    monkeypatch.setattr(rendering, "_validate_cover_url", lambda _url: None)

    destination = tmp_path / "cover.jpg"
    rendering.download_cover("https://example.com/cover.jpg", destination)

    assert destination.read_bytes() == b"jpeg-content"


def test_rendering_prepares_empty_optional_catalog_text() -> None:
    metadata = TrackMetadata(
        title="Track",
        artists=[],
        album="Album",
        released="",
        duration="03:15",
        cover="https://example.com/cover.jpg",
        label="",
    )

    result = rendering._prepare_metadata_for_rendering(metadata)

    assert result.artists == [" "]
    assert result.released == " "
    assert result.label == " "


def test_right_aligned_text_measures_the_full_mixed_font_line(monkeypatch) -> None:
    calls: list[tuple[tuple[int, int], str, str | None]] = []
    monkeypatch.setattr(
        rendering.write, "text_width", lambda value, _fonts, _size: len(value) * 10
    )
    monkeypatch.setattr(
        rendering.write,
        "text",
        lambda _draw, position, value, *_args, **kwargs: calls.append(
            (position, value, kwargs.get("anchor"))
        ),
    )

    rendering._write_right_aligned_text(
        None,
        (100, 20),
        "2004-12-30\n永稻星娱乐",
        (0, 0, 0),
        {},
        60,
    )

    assert calls == [
        ((0, 20), "2004-12-30", "lt"),
        ((50, 88), "永稻星娱乐", "lt"),
    ]


def test_label_text_size_fits_the_reserved_right_side_width(monkeypatch) -> None:
    monkeypatch.setattr(
        rendering.write, "text_width", lambda value, _fonts, size: len(value) * size
    )

    size = rendering._fitted_text_size("Long label", {}, 60, 400)

    assert size == 40


def test_album_track_layout_keeps_every_track_when_titles_are_wide() -> None:
    tracks = [
        "我亲爱的偏执狂",
        "太聪明",
        "小步舞曲",
        "1234567",
        "随便说说",
        "躺在你的衣柜 (Guitar)",
        "A Practice",
        "吉他手",
        "黑眼圈",
        "就算全世界与我为敌",
        "小尘埃",
        "不应该",
        "躺在你的衣柜 (Piano)",
    ]

    layout = rendering._album_track_layout(tracks, indexing=True)

    assert [track for column in layout.columns for track in column] == [
        f"{number}. {track}" for number, track in enumerate(tracks, start=1)
    ]
    assert (
        sum(layout.widths) + layout.gap * (len(layout.widths) - 1)
        <= rendering.poster.s.MAX_WIDTH
    )


@pytest.mark.parametrize("ips", [
    [], ["8.8.8.8", "127.0.0.1"], ["::1"], ["fe80::1"],
    ["169.254.169.254"], ["10.0.0.1"], ["100.64.0.1"], ["::ffff:127.0.0.1"],
])
def test_cover_connection_rejects_non_public_dns(monkeypatch, ips) -> None:
    monkeypatch.setattr(
        rendering.socket, "getaddrinfo",
        lambda *_args, **_kwargs: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 443)) for ip in ips
        ],
    )
    connected = []
    monkeypatch.setattr(httpcore.SyncBackend, "connect_tcp", lambda *_args, **_kwargs: connected.append(True))
    with pytest.raises(ValueError, match="only to public"):
        rendering._PublicCoverBackend().connect_tcp("mixed.example", 443)
    assert connected == []


def test_cover_transport_pins_dns_and_preserves_tls_hostname_and_host(monkeypatch) -> None:
    dns_calls, connections, tls_names, writes = [], [], [], []

    def resolve(host, port, **_kwargs):
        dns_calls.append(host)
        # A second resolution of the original host would return a private IP.
        ip = "8.8.8.8" if len(dns_calls) == 1 else "127.0.0.1"
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, port))]

    class Stream:
        def read(self, _max_bytes, timeout=None):
            return b"HTTP/1.1 200 OK\r\nContent-Length: 4\r\nConnection: close\r\n\r\nbody"

        def write(self, buffer, timeout=None):
            writes.append(buffer)

        def start_tls(self, ssl_context, server_hostname=None, timeout=None):
            tls_names.append(server_hostname)
            return self

        def get_extra_info(self, _name):
            return None

        def close(self):
            pass

    def connect(_self, host, port, **_kwargs):
        connections.append((host, port))
        return Stream()

    monkeypatch.setattr(rendering.socket, "getaddrinfo", resolve)
    monkeypatch.setattr(httpcore.SyncBackend, "connect_tcp", connect)
    with httpx.Client(transport=rendering._PublicCoverTransport(), trust_env=False) as client:
        response = client.get("https://cover.example/art.png")
    assert response.content == b"body"
    assert dns_calls == ["cover.example"]
    assert connections == [("8.8.8.8", 443)]
    assert tls_names == ["cover.example"]
    assert b"Host: cover.example\r\n" in b"".join(writes)


def test_cover_redirect_cannot_connect_to_private_host(monkeypatch, tmp_path) -> None:
    connections = []

    class RedirectStream:
        def read(self, _max_bytes, timeout=None):
            return b"HTTP/1.1 302 Found\r\nLocation: http://private.example/image.png\r\nContent-Length: 0\r\nConnection: close\r\n\r\n"

        def write(self, _buffer, timeout=None):
            pass

        def get_extra_info(self, _name):
            return None

        def close(self):
            pass

    def resolve(host, port, **_kwargs):
        ip = "8.8.8.8" if host == "cover.example" else "10.0.0.1"
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, port))]

    def connect(_self, host, port, **_kwargs):
        connections.append(host)
        return RedirectStream()

    monkeypatch.setattr(rendering.socket, "getaddrinfo", resolve)
    monkeypatch.setattr(httpcore.SyncBackend, "connect_tcp", connect)
    with httpx.Client(transport=rendering._PublicCoverTransport(), trust_env=False) as client:
        monkeypatch.setattr(rendering, "cover_client", client)
        with pytest.raises(ValueError, match="only to public"):
            rendering.download_cover("http://cover.example/image.png", tmp_path / "cover")
    assert connections == ["8.8.8.8"]
