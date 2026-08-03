import os
import subprocess
from dataclasses import dataclass
from pathlib import Path


def _project_root() -> Path | None:
    for directory in Path(__file__).resolve().parents:
        if (directory / "VERSION").is_file():
            return directory
    return None


def _version_file() -> str:
    project_root = _project_root()
    if project_root is None:
        return "0.0.0-dev"
    try:
        return (project_root / "VERSION").read_text(encoding="utf-8").strip()
    except OSError:
        return "0.0.0-dev"


def _git_sha() -> str:
    project_root = _project_root()
    if project_root is None:
        return "local"
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=project_root,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=1,
        ).strip()
    except OSError, subprocess.SubprocessError:
        return "local"


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
    lrc_api_base_url: str
    lrc_api_auth: str | None
    max_concurrent_jobs: int
    port: int
    workers: int
    build_version: str
    build_git_sha: str


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
        lrc_api_base_url=(os.getenv("LRC_API_BASE_URL") or "https://api.lrc.cx").rstrip("/"),
        lrc_api_auth=os.getenv("LRC_API_AUTH") or None,
        max_concurrent_jobs=_integer("MAX_CONCURRENT_JOBS", 1),
        port=_integer("PORT", 8000),
        workers=_integer("WEB_CONCURRENCY", 1),
        build_version=(os.getenv("BEATPRINTS_VERSION") or _version_file()).removeprefix(
            "v"
        ),
        build_git_sha=os.getenv("BEATPRINTS_GIT_SHA") or _git_sha(),
    )


settings = load_settings()
