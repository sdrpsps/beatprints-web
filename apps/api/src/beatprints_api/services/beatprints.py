import ipaddress
import random
import socket
import tempfile
import threading
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urljoin, urlparse

import deezer
import httpx
from BeatPrints import deez, image as beatprints_image, lyrics, poster
from PIL import Image

from beatprints_api.config import settings
from beatprints_api.models.dto import AlbumPosterRequest, TrackPosterRequest
from beatprints_api.spotify import SpotifyClient

MAX_COVER_BYTES = 15 * 1024 * 1024
ALLOWED_COVER_TYPES = {"image/jpeg", "image/png", "image/webp"}
spotify_client = SpotifyClient(
    settings.spotify_client_id,
    settings.spotify_client_secret,
    settings.spotify_market,
)
rendering_lock = threading.Lock()


class UpstreamError(RuntimeError):
    """Raised when a metadata, lyrics, or cover provider fails."""


def _is_public_host(hostname: str) -> bool:
    try:
        addresses = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise UpstreamError(f"Could not resolve cover host: {hostname}") from exc

    # Some container/VPN DNS resolvers return an internal IPv6 proxy address next
    # to a valid public address. Requiring every answer to be public would reject
    # legitimate CDNs in those environments. Internal-only hosts are still blocked.
    return any(ipaddress.ip_address(address[4][0]).is_global for address in addresses)


def _validate_cover_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("cover_url must be an HTTP(S) URL")
    if parsed.username or parsed.password:
        raise ValueError("cover_url must not contain credentials")
    if not _is_public_host(parsed.hostname):
        raise ValueError("cover_url must resolve to a public Internet address")


def _download_cover(url: str, destination: Path) -> None:
    try:
        with httpx.Client(
            follow_redirects=False,
            timeout=httpx.Timeout(15.0, connect=5.0),
            headers={"User-Agent": "BeatPrints-API/0.1"},
        ) as client:
            current_url = url
            for _ in range(6):
                _validate_cover_url(current_url)
                with client.stream("GET", current_url) as response:
                    if response.is_redirect:
                        location = response.headers.get("location")
                        if not location:
                            raise UpstreamError(
                                "Cover provider returned an empty redirect"
                            )
                        current_url = urljoin(current_url, location)
                        continue

                    response.raise_for_status()
                    content_type = response.headers.get("content-type", "").split(";")[
                        0
                    ]
                    if content_type not in ALLOWED_COVER_TYPES:
                        raise ValueError(
                            "cover_url must return a JPEG, PNG, or WebP image"
                        )

                    size = 0
                    with destination.open("wb") as output:
                        for chunk in response.iter_bytes():
                            size += len(chunk)
                            if size > MAX_COVER_BYTES:
                                raise ValueError("Cover image exceeds the 15 MB limit")
                            output.write(chunk)
                    return
            raise UpstreamError("Cover provider returned too many redirects")
    except httpx.HTTPError as exc:
        raise UpstreamError(f"Could not download cover image: {exc}") from exc


def _track_metadata(request: TrackPosterRequest) -> deez.TrackMetadata:
    if request.metadata is not None:
        value = request.metadata
        return deez.TrackMetadata(
            title=value.title,
            artists=value.artists,
            album=value.album,
            released=value.released,
            duration=value.duration,
            cover=str(value.cover_url),
            label=value.label,
        )

    provider, track_id = _catalog_reference(request, "track")
    if provider == "spotify":
        value = spotify_client.track_metadata(str(track_id))
        return deez.TrackMetadata(
            title=value["title"],
            artists=value["artists"],
            album=value["album"],
            released=value["released"],
            duration=value["duration"],
            cover=value["cover"],
            label=value["label"],
        )

    return deez.Deezer().get_track(int(track_id))


def _album_metadata(request: AlbumPosterRequest) -> deez.AlbumMetadata:
    if request.metadata is not None:
        value = request.metadata
        return deez.AlbumMetadata(
            title=value.title,
            artists=value.artists,
            released=value.released,
            tracks=value.tracks.copy(),
            cover=str(value.cover_url),
            label=value.label,
        )

    provider, album_id = _catalog_reference(request, "album")
    if provider == "spotify":
        value = spotify_client.album_metadata(str(album_id))
        metadata = deez.AlbumMetadata(
            title=value["title"],
            artists=value["artists"],
            released=value["released"],
            tracks=value["tracks"],
            cover=value["cover"],
            label=value["label"],
        )
        if request.shuffle:
            random.shuffle(metadata.tracks)
        return metadata

    return deez.Deezer().get_album(int(album_id), shuffle=request.shuffle)


def _catalog_reference(
    request: TrackPosterRequest | AlbumPosterRequest,
    item_type: str,
) -> tuple[str, int | str]:
    if request.catalog_id is not None:
        return request.provider, request.catalog_id

    results = search_catalog(request.query or "", item_type, 1, request.provider)
    if not results:
        raise UpstreamError(f"No matching {item_type} found")
    return request.provider, results[0]["id"]


def _poster_bytes(directory: Path) -> tuple[bytes, str]:
    generated = list(directory.glob("*.png"))
    if len(generated) != 1:
        raise RuntimeError("BeatPrints did not generate exactly one poster")
    path = generated[0]
    return path.read_bytes(), path.name


def _spotify_cover(_url: str, path: str | None) -> Image.Image:
    if path is None:
        raise ValueError("Spotify rendering requires a downloaded cover")
    with Image.open(path) as source:
        cover = source.convert("RGB")
    if cover.width != cover.height:
        raise ValueError("Spotify artwork must be square and cannot be cropped")
    return cover.resize(beatprints_image.s.COVER, Image.Resampling.LANCZOS)


def _empty_scannable(_theme: str = "Light") -> Image.Image:
    return Image.new("RGBA", beatprints_image.s.SCANCODE, (0, 0, 0, 0))


@contextmanager
def _provider_rendering(provider: str | None):
    """Temporarily adapt BeatPrints' fixed Deezer rendering to a catalog provider."""

    with rendering_lock:
        original_cover = beatprints_image.cover
        original_scannable = beatprints_image.scannable
        if provider == "spotify":
            beatprints_image.cover = _spotify_cover
            beatprints_image.scannable = _empty_scannable
        try:
            yield
        finally:
            beatprints_image.cover = original_cover
            beatprints_image.scannable = original_scannable


def _select_lyrics(metadata: deez.TrackMetadata, request: TrackPosterRequest) -> str:
    if request.lyrics is not None:
        return request.lyrics.strip()

    lyric_result = lyrics.Lyrics(metadata).get_lyrics()
    if lyric_result.check_instrumental(metadata):
        return request.instrumental_text
    if request.lyrics_range is not None:
        return lyric_result.select_lines(request.lyrics_range)

    nonempty_lines = [
        line.strip()
        for line in (lyric_result.lyrics or "").splitlines()
        if line.strip()
    ]
    if len(nonempty_lines) < 4:
        raise UpstreamError("Fewer than four non-empty lyric lines were available")
    return "\n".join(nonempty_lines[:4])


def generate_track(request: TrackPosterRequest) -> tuple[bytes, str]:
    metadata = _track_metadata(request)
    selected_lyrics = _select_lyrics(metadata, request)

    with tempfile.TemporaryDirectory(prefix="beatprints-") as temp:
        directory = Path(temp)
        cover_path = directory / "cover"
        _download_cover(metadata.cover, cover_path)
        provider = request.provider if request.metadata is None else None
        with _provider_rendering(provider):
            poster.Poster(str(directory)).track(
                metadata=metadata,
                lyrics=selected_lyrics,
                accent=request.accent,
                theme=request.theme,
                pcover=str(cover_path),
            )
        return _poster_bytes(directory)


def generate_album(request: AlbumPosterRequest) -> tuple[bytes, str]:
    metadata = _album_metadata(request)
    if request.metadata is not None and request.shuffle:
        random.shuffle(metadata.tracks)

    with tempfile.TemporaryDirectory(prefix="beatprints-") as temp:
        directory = Path(temp)
        cover_path = directory / "cover"
        _download_cover(metadata.cover, cover_path)
        provider = request.provider if request.metadata is None else None
        with _provider_rendering(provider):
            poster.Poster(str(directory)).album(
                metadata=metadata,
                indexing=request.indexing,
                accent=request.accent,
                theme=request.theme,
                pcover=str(cover_path),
            )
        return _poster_bytes(directory)


def search_deezer(query: str, search_type: str, limit: int) -> list[dict]:
    client = deezer.Client()
    search_fn = client.search if search_type == "track" else client.search_albums
    results = search_fn(query)[:limit]
    if not results:
        raise UpstreamError(f"No matching {search_type} found")

    formatted = []
    for item in results:
        data = item.as_dict()
        primary_artist = data.get("artist") or {}
        try:
            release_date = item.release_date
        except Exception:
            release_date = None
        try:
            artists = [artist.name for artist in item.contributors]
        except Exception:
            artists = [primary_artist["name"]] if primary_artist.get("name") else []

        if search_type == "track":
            album = data.get("album") or {}
            seconds = int(data.get("duration") or 0)
            minutes, remaining_seconds = divmod(seconds, 60)
            formatted.append(
                {
                    "id": data["id"],
                    "provider": "deezer",
                    "type": "track",
                    "title": data["title"],
                    "artists": artists,
                    "cover_url": album.get("cover_xl") or album.get("cover_big"),
                    "link": data["link"],
                    "release_date": (
                        release_date.isoformat() if release_date is not None else None
                    ),
                    "release_year": (
                        release_date.year if release_date is not None else None
                    ),
                    "release_date_precision": "day",
                    "album": {
                        "id": album["id"],
                        "title": album["title"],
                    },
                    "duration_seconds": seconds,
                    "duration": f"{minutes:02d}:{remaining_seconds:02d}",
                    "explicit": bool(data.get("explicit_lyrics")),
                    "isrc": data.get("isrc"),
                }
            )
        else:
            formatted.append(
                {
                    "id": data["id"],
                    "provider": "deezer",
                    "type": "album",
                    "title": data["title"],
                    "artists": artists,
                    "cover_url": data.get("cover_xl") or data.get("cover_big"),
                    "link": data["link"],
                    "release_date": (
                        release_date.isoformat() if release_date is not None else None
                    ),
                    "release_year": (
                        release_date.year if release_date is not None else None
                    ),
                    "release_date_precision": "day",
                    "explicit": bool(data.get("explicit_lyrics")),
                    "track_count": data.get("nb_tracks"),
                }
            )
    return formatted


def search_catalog(
    query: str,
    search_type: str,
    limit: int,
    provider: str,
) -> list[dict]:
    providers = {
        "deezer": lambda: search_deezer(query, search_type, limit),
        "spotify": lambda: spotify_client.search(query, search_type, limit),
    }
    if provider != "all":
        return providers[provider]()

    results = providers["deezer"]()
    if spotify_client.configured:
        results.extend(providers["spotify"]())
    return results
