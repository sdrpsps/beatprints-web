"""DTOs used by independently registered QR destinations."""

from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


class PlatformLinkMatchData(BaseModel):
    """Current metadata for a canonical public destination link."""

    url: HttpUrl
    title: str
    artists: list[str]
    type: Literal["track", "album"]
    album: str | None = None
    release_year: int | None = None
    duration_seconds: int | None = None
    track_count: int | None = None
    cover_url: HttpUrl | None = None


class PlatformMatchOptionsData(BaseModel):
    match: PlatformLinkMatchData | None = None
    candidates: list[PlatformLinkMatchData] = Field(default_factory=list)
