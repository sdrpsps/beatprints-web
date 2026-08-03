"""The complete enablement list for optional catalog-label resolvers."""

from beatprints_api.integrations.labels.base import LabelResolver

_resolvers: dict[str, LabelResolver] = {}


def register(resolver: LabelResolver) -> LabelResolver:
    if resolver.key in _resolvers:
        raise ValueError(f"Label resolver already registered: {resolver.key}")
    _resolvers[resolver.key] = resolver
    return resolver


def label_resolvers() -> tuple[LabelResolver, ...]:
    return tuple(_resolvers.values())


# These imports are the complete optional label-enrichment list.
from beatprints_api.integrations.labels import spotify as _spotify  # noqa: E402, F401
