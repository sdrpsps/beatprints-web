"""The small contract every poster destination implements."""

from dataclasses import dataclass
from typing import Callable

from PIL import Image

from beatprints_api.models.dto import PlatformLinkMatchData

Scannable = Callable[[str], Image.Image]


@dataclass(frozen=True)
class DestinationAdapter:
    """Catalog and artwork behavior for one independently enabled destination."""

    search: Callable[[str, str], list[dict]]
    resolve: Callable[[str], PlatformLinkMatchData]
    key: str = ""
    label: str = ""
    scannable: Callable[[str], Scannable | None] = lambda _link: None
    supports_isrc: bool = False
    resolve_source: Callable[[str, int | str, str], PlatformLinkMatchData | None] | None = None
    reuses_source_link: Callable[[str], bool] = lambda _provider: False
