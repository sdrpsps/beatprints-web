"""Request-local regional settings for catalog and destination adapters."""

from contextlib import contextmanager
from contextvars import ContextVar

DEFAULT_REGION = "US"

_region: ContextVar[str | None] = ContextVar("music_region", default=None)


def current_region() -> str:
    return _region.get() or DEFAULT_REGION


@contextmanager
def use_region(region: str | None):
    token = _region.set(region)
    try:
        yield
    finally:
        _region.reset(token)
