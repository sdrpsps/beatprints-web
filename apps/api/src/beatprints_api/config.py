import os
from dataclasses import dataclass


def _integer(name: str, default: int, minimum: int = 1) -> int:
    raw = os.getenv(name, str(default))
    try:
        value = int(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer") from exc
    if value < minimum:
        raise RuntimeError(f"{name} must be at least {minimum}")
    return value


@dataclass(frozen=True)
class Settings:
    api_key: str | None
    cors_origins: tuple[str, ...]
    metadata_cache_max_entries: int
    metadata_cache_ttl_seconds: int
    spotify_client_id: str | None
    spotify_client_secret: str | None
    spotify_market: str
    apple_music_storefront: str
    max_concurrent_jobs: int
    port: int
    workers: int


def load_settings() -> Settings:
    origins = tuple(
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "").split(",")
        if origin.strip()
    )
    return Settings(
        api_key=os.getenv("API_KEY") or None,
        cors_origins=origins,
        metadata_cache_max_entries=_integer("METADATA_CACHE_MAX_ENTRIES", 256),
        metadata_cache_ttl_seconds=_integer("METADATA_CACHE_TTL_SECONDS", 600),
        spotify_client_id=os.getenv("SPOTIFY_CLIENT_ID") or None,
        spotify_client_secret=os.getenv("SPOTIFY_CLIENT_SECRET") or None,
        spotify_market=os.getenv("SPOTIFY_MARKET", "US").upper(),
        apple_music_storefront=os.getenv("APPLE_MUSIC_STOREFRONT", "US").upper(),
        max_concurrent_jobs=_integer("MAX_CONCURRENT_JOBS", 1),
        port=_integer("PORT", 8000),
        workers=_integer("WEB_CONCURRENCY", 1),
    )


settings = load_settings()
