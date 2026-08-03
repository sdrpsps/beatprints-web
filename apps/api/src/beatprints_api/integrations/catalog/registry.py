"""The one enablement list for source catalog integrations."""

from beatprints_api.exceptions import UnsupportedCatalogSourceError
from beatprints_api.integrations.catalog.base import CatalogAdapter

_adapters: dict[str, CatalogAdapter] = {}


def register(adapter: CatalogAdapter) -> CatalogAdapter:
    if not adapter.key:
        raise ValueError("Catalog adapters require a stable key")
    if adapter.key in _adapters:
        raise ValueError(f"Catalog adapter already registered: {adapter.key}")
    _adapters[adapter.key] = adapter
    return adapter


def get_catalog_adapter(key: str) -> CatalogAdapter:
    try:
        return _adapters[key]
    except KeyError as exc:
        available = ", ".join(sorted(_adapters)) or "none"
        raise UnsupportedCatalogSourceError(
            f"Unsupported or disabled catalog source: {key}. Enabled sources: {available}"
        ) from exc


def catalog_adapters() -> tuple[CatalogAdapter, ...]:
    return tuple(_adapters[key] for key in sorted(_adapters))


# Importing an adapter is the sole enablement mechanism.  Temporarily removing a
# catalog requires commenting out one import here; no core service changes.
from beatprints_api.integrations.catalog import deezer  # noqa: E402, F401
from beatprints_api.integrations.catalog import spotify  # noqa: E402, F401

