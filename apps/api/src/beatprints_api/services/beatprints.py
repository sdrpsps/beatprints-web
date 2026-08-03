import atexit
import colorsys
import copy
import ipaddress
import random
import re
import socket
import tempfile
import threading
import time
import unicodedata
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path
from urllib.parse import urljoin, urlparse

import deezer
import httpx
from PIL import Image

from beatprints_api.config import settings
from beatprints_api.integrations.destinations import DestinationAdapter, get_destination_adapter
from beatprints_api.integrations.destinations.scannable import empty_scannable, fallback_scannable
from beatprints_api.exceptions import PlatformLinkNoMatchError, UpstreamError
from beatprints_api.models.dto import (
    AlbumPosterRequest,
    LyricsLine,
    LyricsPreviewData,
    PosterPlatformLinks,
    PlatformLinkMatchData,
    PlatformMatchOptionsData,
    TrackPosterRequest,
)
from beatprints_api.palette import extract_palette, install_pylette_compatibility_module
from beatprints_api.spotify import spotify_client

install_pylette_compatibility_module()

from BeatPrints import (
    deez,
    errors as beatprints_errors,
    image as beatprints_image,
    lyrics,
    poster,
    write,
)

beatprints_image.get_palette = extract_palette

MAX_COVER_BYTES = 15 * 1024 * 1024
ALLOWED_COVER_TYPES = {"image/jpeg", "image/png", "image/webp"}
cover_client = httpx.Client(
    follow_redirects=False,
    timeout=httpx.Timeout(15.0, connect=5.0),
    limits=httpx.Limits(
        max_connections=20,
        max_keepalive_connections=10,
        keepalive_expiry=30.0,
    ),
    headers={"User-Agent": "BeatPrints-API/0.1"},
)
atexit.register(cover_client.close)
rendering_lock = threading.Lock()


@dataclass(frozen=True)
class PosterResult:
    content: bytes
    filename: str
    timings_ms: dict[str, float]


_uncached_font = write.font
_uncached_check_glyph = write._check_glyph


@lru_cache(maxsize=3)
def _cached_font(weight: str):
    return _uncached_font(weight)


@lru_cache(maxsize=4096)
def _cached_check_glyph(font, glyph: str) -> bool:
    return _uncached_check_glyph(font, glyph)


# BeatPrints repeatedly parses the same multilingual fonts and cmap tables while
# rendering a poster. The rendering lock makes these process-wide objects safe to
# reuse, and warming them here moves the first-request penalty to process startup.
write.font = _cached_font
write._check_glyph = _cached_check_glyph
for _font_weight in ("Regular", "Bold", "Light"):
    write.font(_font_weight)


def _normalized_label(value: object) -> str:
    label = str(value or "").strip()
    if label.casefold() in {"unknown", "unknown label", "unknown records"}:
        return ""
    return label


def _match_text(value: object) -> str:
    """Normalize catalog text while retaining non-Latin artist and title characters."""

    return "".join(
        character for character in str(value or "").casefold() if character.isalnum()
    )


def _text_similarity(left: object, right: object) -> float:
    normalized_left = _match_text(left)
    normalized_right = _match_text(right)
    if not normalized_left or not normalized_right:
        return 0.0
    if normalized_left == normalized_right:
        return 1.0
    return SequenceMatcher(None, normalized_left, normalized_right).ratio()


def _metadata_artists(metadata: deez.TrackMetadata | deez.AlbumMetadata) -> str:
    return " ".join(str(artist) for artist in metadata.artists)


def _duration_seconds(value: str) -> int | None:
    try:
        minutes, seconds = value.split(":", maxsplit=1)
        return int(minutes) * 60 + int(seconds)
    except (AttributeError, ValueError):
        return None


def _release_year(value: object) -> int | None:
    try:
        return date.fromisoformat(str(value)[:10]).year
    except ValueError:
        try:
            return int(str(value)[:4])
        except ValueError:
            return None


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
        current_url = url
        for _ in range(6):
            _validate_cover_url(current_url)
            with cover_client.stream("GET", current_url) as response:
                if response.is_redirect:
                    location = response.headers.get("location")
                    if not location:
                        raise UpstreamError("Cover provider returned an empty redirect")
                    current_url = urljoin(current_url, location)
                    continue

                response.raise_for_status()
                content_type = response.headers.get("content-type", "").split(";")[0]
                if content_type not in ALLOWED_COVER_TYPES:
                    raise ValueError("cover_url must return a JPEG, PNG, or WebP image")

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


def _metadata_cache_token() -> int:
    return int(time.monotonic() // settings.metadata_cache_ttl_seconds)


@lru_cache(maxsize=settings.metadata_cache_max_entries)
def _cached_track_metadata(
    provider: str,
    track_id: int | str,
    _cache_token: int,
) -> deez.TrackMetadata:
    if provider == "spotify":
        value = spotify_client.track_metadata(str(track_id))
        metadata = deez.TrackMetadata(
            title=value["title"],
            artists=value["artists"],
            album=value["album"],
            released=value["released"],
            duration=value["duration"],
            cover=value["cover"],
            label=_normalized_label(value["label"]),
        )
        metadata.link = value["link"]
        metadata.isrc = value.get("isrc")
        return metadata

    metadata = deez.Deezer().get_track(int(track_id))
    metadata.label = _normalized_label(metadata.label)
    return metadata


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
    return copy.deepcopy(
        _cached_track_metadata(provider, track_id, _metadata_cache_token())
    )


@lru_cache(maxsize=settings.metadata_cache_max_entries)
def _cached_album_metadata(
    provider: str,
    album_id: int | str,
    _cache_token: int,
) -> deez.AlbumMetadata:
    if provider == "spotify":
        value = spotify_client.album_metadata(str(album_id))
        metadata = deez.AlbumMetadata(
            title=value["title"],
            artists=value["artists"],
            released=value["released"],
            tracks=value["tracks"],
            cover=value["cover"],
            label=_normalized_label(value["label"]),
        )
        metadata.link = value["link"]
        return metadata

    metadata = deez.Deezer().get_album(int(album_id), shuffle=False)
    metadata.label = _normalized_label(metadata.label)
    return metadata


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
    metadata = copy.deepcopy(
        _cached_album_metadata(provider, album_id, _metadata_cache_token())
    )
    if request.shuffle:
        random.shuffle(metadata.tracks)
    return metadata


_VERSION_MARKERS = {
    "live", "remaster", "remastered", "acoustic", "instrumental",
    "karaoke", "radio edit", "demo", "mono", "stereo", "deluxe",
    "extended", "现场版", "現場版", "重制版", "重製版", "伴奏",
    "纯音乐", "純音樂", "原声", "原聲", "混音", "豪华版", "豪華版",
}
_VERSION_SUFFIX = re.compile(r"(?:^|[\s\[(（【\-–—])(?P<value>[^\])）】]+)(?=$|[\s\])）】])")


def _catalog_title_parts(
    value: object,
) -> tuple[frozenset[str], frozenset[str]]:
    text = unicodedata.normalize("NFKC", str(value or "")).casefold().strip()
    version_regions = [match.group("value") for match in _VERSION_SUFFIX.finditer(text)]
    versions = frozenset(
        marker
        for marker in _VERSION_MARKERS
        if any(
            marker in region
            if any(ord(character) > 127 for character in marker)
            else re.search(rf"(?<![a-z]){re.escape(marker)}(?![a-z])", region)
            for region in version_regions
        )
    )
    base = re.sub(r"\s*[（(][^()（）]*[）)]\s*$", "", text).strip()
    aliases = {
        normalized
        for variant in (text, base)
        for part in re.split(r"\s+[-–—]\s+", variant)
        if (normalized := _match_text(part))
    }
    return frozenset(aliases), versions


def _catalog_title_similarity(left: object, right: object) -> float:
    left_aliases, left_versions = _catalog_title_parts(left)
    right_aliases, right_versions = _catalog_title_parts(right)
    if not left_aliases or not right_aliases or left_versions != right_versions:
        return 0.0
    return max(
        _text_similarity(left_alias, right_alias)
        for left_alias in left_aliases
        for right_alias in right_aliases
    )


def _artist_match_state(source: str, candidate: str) -> str:
    if _text_similarity(source, candidate) >= 0.88:
        return "matched"

    def latin_only(value: str) -> bool:
        letters = [character for character in value if character.isalpha()]
        return bool(letters) and all("LATIN" in unicodedata.name(character, "") for character in letters)

    return "mismatched" if latin_only(source) and latin_only(candidate) else "unknown"


def _artist_comparison(
    source_artists: list[str], candidate_artists: list[str]
) -> tuple[float, str]:
    pair_scores = [
        _text_similarity(source, candidate)
        for source in source_artists
        for candidate in candidate_artists
    ]
    score = max(pair_scores, default=0.0)
    if score >= 0.88:
        return score, "matched"
    return score, _artist_match_state(
        " ".join(source_artists), " ".join(candidate_artists)
    )


def _candidate_title_similarity(left: object, right: object) -> tuple[float, bool]:
    left_aliases, left_versions = _catalog_title_parts(left)
    right_aliases, right_versions = _catalog_title_parts(right)
    if not left_aliases or not right_aliases:
        return 0.0, False
    similarity = max(
        _text_similarity(left_alias, right_alias)
        for left_alias in left_aliases
        for right_alias in right_aliases
    )
    return similarity, left_versions != right_versions


def _candidate_score(
    metadata: deez.TrackMetadata | deez.AlbumMetadata,
    candidate: dict,
    item_type: str,
    origins: set[str],
) -> float | None:
    title_score, version_conflict = _candidate_title_similarity(
        metadata.title, candidate.get("title")
    )
    if title_score < 0.45:
        return None

    source_artists = [str(artist) for artist in metadata.artists]
    candidate_artists = [str(artist) for artist in candidate.get("artists") or []]
    artist_score, artist_state = _artist_comparison(
        source_artists, candidate_artists
    )
    if artist_state == "unknown":
        artist_score = 0.45
    if "artist" in origins:
        artist_score = min(1.0, artist_score + 0.20)

    source_year = _release_year(metadata.released)
    candidate_year = candidate.get("release_year")
    year_score = (
        0.5
        if not source_year or not candidate_year
        else float(source_year == candidate_year)
    )
    score = title_score * 0.50 + artist_score * 0.24 + year_score * 0.08

    if item_type == "track":
        album_score, _album_version_conflict = _candidate_title_similarity(
            metadata.album, candidate.get("album")
        )
        source_duration = _duration_seconds(metadata.duration)
        candidate_duration = candidate.get("duration_seconds")
        duration_score = (
            0.5
            if not source_duration or not candidate_duration
            else (
                1.0 if abs(source_duration - candidate_duration) <= 2
                else 0.8 if abs(source_duration - candidate_duration) <= 5
                else 0.35 if abs(source_duration - candidate_duration) <= 15
                else 0.0
            )
        )
        score += album_score * 0.08 + duration_score * 0.10
        if _album_version_conflict:
            score -= 0.05
    else:
        source_count = len(metadata.tracks)
        candidate_count = candidate.get("track_count")
        count_score = (
            0.5
            if not source_count or not candidate_count
            else float(source_count == candidate_count)
        )
        score += count_score * 0.12

    if version_conflict:
        score -= 0.25
    if source_year and candidate_year and source_year != candidate_year:
        score -= 0.10 if item_type == "track" else 0.20
    return score


def _source_metadata(provider: str, catalog_id: int | str, item_type: str):
    return (
        _track_metadata(TrackPosterRequest(provider=provider, catalog_id=catalog_id))
        if item_type == "track"
        else _album_metadata(AlbumPosterRequest(provider=provider, catalog_id=catalog_id))
    )


def _destination_adapter(platform: str) -> DestinationAdapter:
    """Compatibility seam for the shared engine and its isolated tests."""

    return get_destination_adapter(platform)


def _source_isrc(
    provider: str, catalog_id: int | str, metadata: deez.TrackMetadata
) -> str | None:
    value = getattr(metadata, "isrc", None)
    if value:
        return str(value)
    if provider != "deezer":
        return None
    try:
        response = cover_client.get(f"https://api.deezer.com/track/{catalog_id}")
        response.raise_for_status()
        result = response.json().get("isrc")
        return str(result) if result else None
    except (httpx.HTTPError, ValueError):
        return None


def _matching_queries(metadata, item_type: str, isrc: str | None) -> list[tuple[str, str]]:
    artist = _metadata_artists(metadata)
    queries: list[tuple[str, str]] = []
    if item_type == "track" and isrc:
        queries.append(("isrc", f"isrc:{isrc}"))
    queries.extend(
        [
            ("combined", f"{metadata.title} {artist}"),
            ("title", metadata.title),
            ("artist", artist),
        ]
    )
    return list(dict.fromkeys(queries))


def _collect_destination_candidates(
    adapter: DestinationAdapter, metadata, item_type: str, isrc: str | None
) -> list[tuple[dict, set[str]]]:
    candidates: dict[str, dict] = {}
    origins: dict[str, set[str]] = {}
    for origin, query in _matching_queries(
        metadata, item_type, isrc if adapter.supports_isrc else None
    ):
        for candidate in adapter.search(query, item_type):
            url = str(candidate.get("url") or "")
            if not url:
                continue
            identity = str(candidate.get("platform_id") or url)
            candidates.setdefault(identity, candidate)
            origins.setdefault(identity, set()).add(origin)
    return [
        (candidate, origins[identity])
        for identity, candidate in candidates.items()
    ]


def _has_hard_conflict(metadata, candidate: dict, item_type: str) -> bool:
    title_score, version_conflict = _candidate_title_similarity(
        metadata.title, candidate.get("title")
    )
    if title_score < 0.88 or version_conflict:
        return True
    _artist_score, artist_state = _artist_comparison(
        [str(artist) for artist in metadata.artists],
        [str(artist) for artist in candidate.get("artists") or []],
    )
    if artist_state == "mismatched":
        return True
    source_year = _release_year(metadata.released)
    candidate_year = candidate.get("release_year")
    if item_type == "album":
        source_count = len(metadata.tracks)
        candidate_count = candidate.get("track_count")
        return bool(
            source_year and candidate_year and source_year != candidate_year
            or source_count and candidate_count and source_count != candidate_count
        )
    source_duration = _duration_seconds(metadata.duration)
    candidate_duration = candidate.get("duration_seconds")
    return bool(
        source_duration
        and candidate_duration
        and abs(source_duration - candidate_duration) > 15
    )


def _can_confirm(
    metadata,
    ranked: list[tuple[float, dict, set[str]]],
    item_type: str,
    isrc: str | None,
) -> dict | None:
    if not ranked:
        return None
    score, candidate, origins = ranked[0]
    if isrc and candidate.get("isrc") == isrc:
        return candidate
    if _has_hard_conflict(metadata, candidate, item_type):
        return None
    _artist_score, artist_state = _artist_comparison(
        [str(artist) for artist in metadata.artists],
        [str(artist) for artist in candidate.get("artists") or []],
    )
    if artist_state == "mismatched":
        return None
    if artist_state == "unknown" and "artist" not in origins:
        return None
    threshold = 0.84
    if score < threshold:
        return None
    if len(ranked) > 1 and score - ranked[1][0] < 0.04:
        return None
    return candidate


def platform_match_options(
    provider: str,
    catalog_id: int | str,
    item_type: str,
    platform: str,
    limit: int = 8,
) -> PlatformMatchOptionsData:
    """Run one shared matching pipeline for every QR destination."""

    adapter = _destination_adapter(platform)
    direct_match = (
        adapter.resolve_source(provider, catalog_id, item_type)
        if adapter.resolve_source is not None
        else None
    )
    if direct_match is not None:
        match = direct_match
        return PlatformMatchOptionsData(match=match, candidates=[match])

    metadata = _source_metadata(provider, catalog_id, item_type)
    isrc = (
        _source_isrc(provider, catalog_id, metadata)
        if item_type == "track" and adapter.supports_isrc
        else None
    )
    collected = _collect_destination_candidates(adapter, metadata, item_type, isrc)
    ranked: list[tuple[float, dict, set[str]]] = []
    for candidate, origins in collected:
        exact_isrc = bool(isrc and candidate.get("isrc") == isrc)
        score = (
            2.0
            if exact_isrc
            else _candidate_score(metadata, candidate, item_type, origins)
        )
        if score is not None:
            ranked.append((score, candidate, origins))
    ranked.sort(key=lambda item: item[0], reverse=True)
    confirmed = _can_confirm(metadata, ranked, item_type, isrc)
    return PlatformMatchOptionsData(
        match=(
            PlatformLinkMatchData.model_validate(confirmed) if confirmed is not None else None
        ),
        candidates=[
            PlatformLinkMatchData.model_validate(candidate)
            for _score, candidate, _origins in ranked[:limit]
        ],
    )


def resolve_platform_url(platform: str, url: str):
    return _destination_adapter(platform).resolve(url)


def clear_metadata_cache() -> None:
    _cached_track_metadata.cache_clear()
    _cached_album_metadata.cache_clear()


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


def _selected_platform_link(
    links: PosterPlatformLinks | None,
    selected_platform: str | None,
    provider: str | None,
    source_link: str | None,
) -> tuple[DestinationAdapter, str] | None:
    if selected_platform is None:
        return None
    adapter = _destination_adapter(selected_platform)
    values = links.root if links is not None else {}
    link = values.get(selected_platform)
    if link is None and source_link and provider and adapter.reuses_source_link(provider):
        link = source_link
    if link is None:
        raise ValueError(
            f"platform_links.{selected_platform} is required for "
            f"qr_platform={selected_platform}"
        )
    return adapter, str(link)


def _relative_luminance(color: tuple[int, int, int]) -> float:
    channels = []
    for value in color:
        channel = value / 255
        channels.append(
            channel / 12.92
            if channel <= 0.04045
            else ((channel + 0.055) / 1.055) ** 2.4
        )
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def _contrast_with_white(color: tuple[int, int, int]) -> float:
    return 1.05 / (_relative_luminance(color) + 0.05)


def _cover_qr_color(cover_path: Path) -> tuple[int, int, int]:
    with Image.open(cover_path) as cover:
        palette = extract_palette(cover, size=8)

    def saturation(color: tuple[int, int, int]) -> float:
        return colorsys.rgb_to_hsv(*(channel / 255 for channel in color))[1]

    high_contrast = [color for color in palette if _contrast_with_white(color) >= 4.5]
    if high_contrast:
        return max(high_contrast, key=saturation)

    selected = max(palette, key=saturation)
    for step in range(19, -1, -1):
        factor = step / 20
        darkened = tuple(round(channel * factor) for channel in selected)
        if _contrast_with_white(darkened) >= 4.5:
            return darkened
    return 0, 0, 0


@contextmanager
def _provider_rendering(
    provider: str | None,
    platform_link: tuple[DestinationAdapter, str] | None,
    qr_color: tuple[int, int, int] | None,
):
    """Temporarily adapt BeatPrints' fixed Deezer rendering to a catalog provider."""

    with rendering_lock:
        original_cover = beatprints_image.cover
        original_scannable = beatprints_image.scannable
        beatprints_image.scannable = empty_scannable
        if provider == "spotify":
            beatprints_image.cover = _spotify_cover
        if platform_link is not None and qr_color is not None:
            adapter, link = platform_link
            beatprints_image.scannable = adapter.scannable(link) or fallback_scannable(
                adapter.label, link, qr_color
            )
        try:
            yield
        finally:
            beatprints_image.cover = original_cover
            beatprints_image.scannable = original_scannable


def _fetch_lyrics(metadata: deez.TrackMetadata):
    try:
        lyric_result = lyrics.Lyrics(metadata).get_lyrics()
        instrumental = lyric_result.check_instrumental(metadata)
    except beatprints_errors.NoLyricsAvailable as exc:
        raise UpstreamError("No lyrics were found for this recording") from exc
    except Exception as exc:
        raise UpstreamError("Lyrics provider request failed") from exc
    nonempty_lines = [
        line.strip()
        for line in (lyric_result.lyrics or "").splitlines()
        if line.strip()
    ]
    return lyric_result, instrumental, nonempty_lines


def preview_lyrics(provider: str, catalog_id: int | str) -> LyricsPreviewData:
    request = TrackPosterRequest(provider=provider, catalog_id=catalog_id)
    metadata = _track_metadata(request)
    _lyric_result, instrumental, lines = _fetch_lyrics(metadata)
    return LyricsPreviewData(
        provider=provider,
        catalog_id=catalog_id,
        instrumental=instrumental,
        lines=[
            LyricsLine(index=index, text=line)
            for index, line in enumerate(lines, start=1)
        ],
    )


def _select_lyrics(metadata: deez.TrackMetadata, request: TrackPosterRequest) -> str:
    if request.lyrics is not None:
        return request.lyrics.strip()

    lyric_result, instrumental, nonempty_lines = _fetch_lyrics(metadata)
    if instrumental:
        return request.instrumental_text.strip()
    if request.lyrics_range is not None:
        return lyric_result.select_lines(request.lyrics_range)

    if len(nonempty_lines) < 4:
        raise UpstreamError("Fewer than four non-empty lyric lines were available")
    return "\n".join(nonempty_lines[:4])


def _renderable_lyrics(value: str) -> str:
    # BeatPrints 0.1.0 indexes the first glyph even for an empty string.
    # A space is visually empty while keeping the upstream renderer safe.
    return value or " "


def _elapsed_ms(started_at: float) -> float:
    return (time.perf_counter() - started_at) * 1000


def generate_track(request: TrackPosterRequest) -> PosterResult:
    timings: dict[str, float] = {}
    started_at = time.perf_counter()
    metadata = _track_metadata(request)
    timings["metadata"] = _elapsed_ms(started_at)

    started_at = time.perf_counter()
    selected_lyrics = _select_lyrics(metadata, request)
    timings["lyrics"] = _elapsed_ms(started_at)
    provider = request.provider if request.metadata is None else None
    platform_link = _selected_platform_link(
        request.platform_links,
        request.qr_platform,
        provider,
        getattr(metadata, "link", None),
    )

    with tempfile.TemporaryDirectory(prefix="beatprints-") as temp:
        directory = Path(temp)
        cover_path = directory / "cover"

        started_at = time.perf_counter()
        _download_cover(metadata.cover, cover_path)
        timings["cover"] = _elapsed_ms(started_at)

        started_at = time.perf_counter()
        qr_color = _cover_qr_color(cover_path) if platform_link is not None else None
        timings["palette"] = _elapsed_ms(started_at)

        started_at = time.perf_counter()
        with _provider_rendering(provider, platform_link, qr_color):
            poster.Poster(str(directory)).track(
                metadata=metadata,
                lyrics=_renderable_lyrics(selected_lyrics),
                accent=request.accent,
                theme=request.theme,
                pcover=str(cover_path),
            )
        timings["render"] = _elapsed_ms(started_at)

        started_at = time.perf_counter()
        content, filename = _poster_bytes(directory)
        timings["read"] = _elapsed_ms(started_at)
        return PosterResult(content, filename, timings)


def generate_album(request: AlbumPosterRequest) -> PosterResult:
    timings: dict[str, float] = {}
    started_at = time.perf_counter()
    metadata = _album_metadata(request)
    if request.metadata is not None and request.shuffle:
        random.shuffle(metadata.tracks)
    timings["metadata"] = _elapsed_ms(started_at)

    provider = request.provider if request.metadata is None else None
    platform_link = _selected_platform_link(
        request.platform_links,
        request.qr_platform,
        provider,
        getattr(metadata, "link", None),
    )

    with tempfile.TemporaryDirectory(prefix="beatprints-") as temp:
        directory = Path(temp)
        cover_path = directory / "cover"

        started_at = time.perf_counter()
        _download_cover(metadata.cover, cover_path)
        timings["cover"] = _elapsed_ms(started_at)

        started_at = time.perf_counter()
        qr_color = _cover_qr_color(cover_path) if platform_link is not None else None
        timings["palette"] = _elapsed_ms(started_at)

        started_at = time.perf_counter()
        with _provider_rendering(provider, platform_link, qr_color):
            poster.Poster(str(directory)).album(
                metadata=metadata,
                indexing=request.indexing,
                accent=request.accent,
                theme=request.theme,
                pcover=str(cover_path),
            )
        timings["render"] = _elapsed_ms(started_at)

        started_at = time.perf_counter()
        content, filename = _poster_bytes(directory)
        timings["read"] = _elapsed_ms(started_at)
        return PosterResult(content, filename, timings)


def search_deezer(query: str, search_type: str, limit: int) -> list[dict]:
    client = deezer.Client()
    search_fn = client.search if search_type == "track" else client.search_albums
    results = search_fn(query)[:limit]

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
