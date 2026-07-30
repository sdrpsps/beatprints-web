from io import BytesIO

from PIL import Image
import pytest

from beatprints_api.models import TrackPosterRequest
from beatprints_api.services import beatprints as beatprints_service
from beatprints_api.spotify import SpotifyClient, SpotifyNotConfiguredError


def test_spotify_requires_credentials() -> None:
    client = SpotifyClient(client_id=None, client_secret=None, market="US")

    with pytest.raises(SpotifyNotConfiguredError):
        client.search("SUMMER BREEZE", "track", 5)


def test_spotify_formats_track_search_result() -> None:
    item = {
        "id": "spotify-track-id",
        "name": "Summer Breeze",
        "artists": [{"name": "The Isley Brothers"}],
        "album": {
            "id": "spotify-album-id",
            "name": "3 + 3",
            "release_date": "1973-08-07",
            "release_date_precision": "day",
            "images": [{"url": "https://i.scdn.co/image/example"}],
        },
        "duration_ms": 372000,
        "explicit": False,
        "external_ids": {"isrc": "USSM17300508"},
        "external_urls": {"spotify": "https://open.spotify.com/track/spotify-track-id"},
    }

    result = SpotifyClient._format_track(item)

    assert result["provider"] == "spotify"
    assert result["id"] == "spotify-track-id"
    assert result["release_date"] == "1973-08-07"
    assert result["release_year"] == 1973
    assert result["release_date_precision"] == "day"
    assert result["duration_seconds"] == 372
    assert result["duration"] == "06:12"
    assert result["isrc"] == "USSM17300508"


def test_spotify_uses_album_label_when_available() -> None:
    assert SpotifyClient._album_label({"label": "Epic", "copyrights": []}) == "Epic"


def test_spotify_derives_deprecated_label_from_phonographic_copyright() -> None:
    album = {
        "copyrights": [
            {"type": "C", "text": "© 1973 Sony Music Entertainment"},
            {"type": "P", "text": "℗ 1973 Epic Records"},
        ]
    }

    assert SpotifyClient._album_label(album) == "Epic Records"


def test_spotify_leaves_missing_label_blank_instead_of_fabricating_unknown() -> None:
    assert SpotifyClient._album_label({}) == ""


def test_spotify_catalog_id_can_supply_poster_metadata(monkeypatch) -> None:
    monkeypatch.setattr(
        beatprints_service.spotify_client,
        "track_metadata",
        lambda track_id: {
            "title": "Summer Breeze",
            "artists": ["The Isley Brothers"],
            "album": "3 + 3",
            "released": "1973-08-07",
            "duration": "06:12",
            "cover": "https://i.scdn.co/image/example",
            "label": "Epic",
            "link": f"https://open.spotify.com/track/{track_id}",
        },
    )
    request = TrackPosterRequest(
        provider="spotify",
        catalog_id="spotify-track-id",
        lyrics="one\ntwo\nthree\nfour",
    )

    metadata = beatprints_service._track_metadata(request)

    assert metadata.title == "Summer Breeze"
    assert metadata.album == "3 + 3"
    assert metadata.cover == "https://i.scdn.co/image/example"
    assert metadata.label == "Epic"
    assert metadata.link == "https://open.spotify.com/track/spotify-track-id"


def test_catalog_metadata_is_cached_without_sharing_mutable_objects(
    monkeypatch,
) -> None:
    beatprints_service.clear_metadata_cache()
    calls = 0

    def track_metadata(track_id: str) -> dict:
        nonlocal calls
        calls += 1
        return {
            "title": "Cached Track",
            "artists": ["Cache Artist"],
            "album": "Cache Album",
            "released": "2026",
            "duration": "03:30",
            "cover": "https://i.scdn.co/image/cache",
            "label": "Cache Records",
            "link": f"https://open.spotify.com/track/{track_id}",
        }

    monkeypatch.setattr(
        beatprints_service.spotify_client,
        "track_metadata",
        track_metadata,
    )
    request = TrackPosterRequest(
        provider="spotify",
        catalog_id="metadata-cache-test-track",
        lyrics="one\ntwo\nthree\nfour",
    )

    first = beatprints_service._track_metadata(request)
    second = beatprints_service._track_metadata(request)

    assert calls == 1
    assert first.title == second.title == "Cached Track"
    assert first is not second
    beatprints_service.clear_metadata_cache()


def test_multilingual_fonts_are_cached_per_weight() -> None:
    first = beatprints_service.write.font("Regular")
    second = beatprints_service.write.font("Regular")

    assert first is second


def test_spotify_source_link_is_added_to_platform_qr_codes() -> None:
    request = TrackPosterRequest(
        provider="spotify",
        catalog_id="spotify-track-id",
        qr_platform="spotify",
        platform_links={
            "apple_music": "https://music.apple.com/us/album/example/123456789"
        },
    )

    link = beatprints_service._selected_platform_link(
        request.platform_links,
        request.qr_platform,
        request.provider,
        "https://open.spotify.com/track/spotify-track-id",
    )

    assert link == ("Spotify", "https://open.spotify.com/track/spotify-track-id")


def test_no_qr_platform_means_no_selected_link() -> None:
    request = TrackPosterRequest(
        provider="spotify",
        catalog_id="spotify-track-id",
        platform_links={"spotify": "https://open.spotify.com/track/example"},
    )

    link = beatprints_service._selected_platform_link(
        request.platform_links,
        request.qr_platform,
        request.provider,
        "https://open.spotify.com/track/spotify-track-id",
    )

    assert link is None


def test_rendering_hides_platform_area_without_manual_selection() -> None:
    original = beatprints_service.beatprints_image.scannable

    with beatprints_service._provider_rendering(None, None, None):
        image = beatprints_service.beatprints_image.scannable("Light")
        assert image.getbbox() is None

    assert beatprints_service.beatprints_image.scannable is original


def test_platform_scannable_uses_cover_color() -> None:
    item = ("QQ 音乐", "https://y.qq.com/n/ryqq/songDetail/example")
    color = (82, 44, 126)

    image = beatprints_service._platform_scannable(item, color)("Light")

    assert image.mode == "RGBA"
    assert image.size == beatprints_service.beatprints_image.s.SCANCODE
    assert image.getbbox() is not None
    colors = image.getcolors(maxcolors=image.width * image.height) or []
    assert color + (255,) in {value for _count, value in colors}


def test_spotify_uri_accepts_canonical_track_and_album_urls() -> None:
    track_id = "4uLU6hMCjMI75M1A2tKUQC"
    album_id = "1ATL5GLyefJaxhQzSPVrLX"

    assert (
        beatprints_service._spotify_uri(
            f"https://open.spotify.com/track/{track_id}?si=example"
        )
        == f"spotify:track:{track_id}"
    )
    assert (
        beatprints_service._spotify_uri(
            f"https://open.spotify.com/intl-zh/album/{album_id}"
        )
        == f"spotify:album:{album_id}"
    )
    assert beatprints_service._spotify_uri("https://example.com/track/abc") is None


def test_spotify_code_scannable_uses_spotify_image_service_output(monkeypatch) -> None:
    source = Image.new("RGB", (560, 140), "white")
    source.paste((0, 0, 0), (28, 28, 532, 112))
    payload = BytesIO()
    source.save(payload, format="PNG")
    calls: list[tuple[str, int]] = []

    def png(uri: str, width: int) -> bytes:
        calls.append((uri, width))
        return payload.getvalue()

    monkeypatch.setattr(beatprints_service.spotify_code_client, "png", png)
    scannable = beatprints_service._spotify_code_scannable(
        "https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC"
    )

    assert scannable is not None
    image = scannable("Light")
    assert calls == [("spotify:track:4uLU6hMCjMI75M1A2tKUQC", 560)]
    assert image.size == (560, 120)
    assert image.getpixel((0, 0))[3] == 0
    assert image.getpixel((212, 60)) == (50, 47, 48, 255)


def test_apple_music_scannable_uses_the_same_theme_color_rule_as_spotify_code() -> (
    None
):
    scannable = beatprints_service._apple_music_scannable(
        ("Apple Music", "https://music.apple.com/us/album/example/123456789"),
    )
    image = scannable("Light")
    dark_image = scannable("Dark")

    light_color = beatprints_service.beatprints_image.t.THEMES["Light"]
    dark_color = beatprints_service.beatprints_image.t.THEMES["Dark"]
    assert image.mode == "RGBA"
    assert image.size == beatprints_service.beatprints_image.s.SCANCODE
    assert image.getpixel((20, 60)) == light_color + (255,)
    assert dark_image.getpixel((20, 60)) == dark_color + (255,)
    assert image.getpixel((98, 4))[3] == 0
    colors = image.getcolors(maxcolors=image.width * image.height) or []
    assert light_color + (255,) in {value for _count, value in colors}


def test_cover_qr_color_is_colored_and_has_safe_white_contrast(tmp_path) -> None:
    cover_path = tmp_path / "cover.png"
    Image.new("RGB", (200, 200), (217, 164, 65)).save(cover_path)

    color = beatprints_service._cover_qr_color(cover_path)

    assert color[0] > color[2]
    assert beatprints_service._contrast_with_white(color) >= 4.5
