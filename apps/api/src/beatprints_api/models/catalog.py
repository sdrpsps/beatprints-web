"""DTOs returned by registered source music catalogs and lyric previews."""

from typing import Annotated, Literal

from pydantic import BaseModel, Field, HttpUrl

from beatprints_api.models.poster import CatalogProvider


class SearchAlbumSummary(BaseModel):
    id: Annotated[int | str, Field(description="目录中的专辑 ID。")]
    title: Annotated[str, Field(description="歌曲所属专辑标题。")]


class SearchResult(BaseModel):
    """A normalized source-catalog result for the selected-item journey."""

    id: int | str
    provider: Annotated[str, Field(description="已启用目录 integration 的 key。")]
    type: Literal["track", "album"]
    title: str
    artists: list[str]
    cover_url: HttpUrl
    link: HttpUrl
    release_date: str | None = None
    release_year: int | None = None
    release_date_precision: Literal["year", "month", "day"] | None = None
    album: SearchAlbumSummary | None = None
    duration_seconds: int | None = None
    duration: str | None = None
    explicit: bool | None = None
    track_count: int | None = None
    isrc: str | None = None


class LyricsLine(BaseModel):
    index: Annotated[int, Field(ge=1)]
    text: Annotated[str, Field(min_length=1, max_length=1000)]


class LyricsSourceData(BaseModel):
    key: Annotated[str, Field(min_length=1)]
    label: Annotated[str, Field(min_length=1)]
    default: bool = False


class LyricsSourcesData(BaseModel):
    sources: list[LyricsSourceData]


class LyricsPreviewData(BaseModel):
    provider: CatalogProvider
    catalog_id: int | str
    source: str
    instrumental: bool
    lines: list[LyricsLine]
