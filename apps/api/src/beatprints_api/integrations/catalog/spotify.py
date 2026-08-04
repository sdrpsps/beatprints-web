from PIL import Image

from BeatPrints import deez, image as beatprints_image
from beatprints_api.integrations.catalog.base import CatalogAdapter
from beatprints_api.integrations.catalog.registry import register
from beatprints_api.integrations.spotify_client import spotify_client


def _normalized_label(value: object) -> str:
    label = str(value or "").strip()
    return "" if label.casefold() in {"unknown", "unknown label", "unknown records"} else label


def track_metadata(catalog_id: int | str) -> deez.TrackMetadata:
    value = spotify_client.track_metadata(str(catalog_id))
    metadata = deez.TrackMetadata(
        title=value["title"], artists=value["artists"], album=value["album"],
        released=value["released"], duration=value["duration"], cover=value["cover"],
        label=_normalized_label(value["label"]),
    )
    metadata.link = value["link"]
    metadata.isrc = value.get("isrc")
    return metadata


def album_metadata(catalog_id: int | str) -> deez.AlbumMetadata:
    value = spotify_client.album_metadata(str(catalog_id))
    metadata = deez.AlbumMetadata(
        title=value["title"], artists=value["artists"], released=value["released"],
        tracks=value["tracks"], cover=value["cover"], label=_normalized_label(value["label"]),
    )
    metadata.link = value["link"]
    return metadata


def cover_renderer(_url: str, path: str | None) -> Image.Image:
    """Adapt Spotify's downloaded artwork to BeatPrints' cover hook."""

    if path is None:
        raise ValueError("Spotify rendering requires a downloaded cover")
    with Image.open(path) as source:
        cover = source.convert("RGB")
    if cover.width != cover.height:
        raise ValueError("Spotify artwork must be square and cannot be cropped")
    return cover.resize(beatprints_image.s.COVER, Image.Resampling.LANCZOS)


adapter = register(CatalogAdapter(
    key="spotify", label="Spotify", configured=lambda: spotify_client.configured,
    search=spotify_client.search, track_metadata=track_metadata, album_metadata=album_metadata,
    cover_renderer=cover_renderer,
))
