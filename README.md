<div align="center">

# BeatPrints Web

**Give your favorite music a physical form.**

Find the exact track or album from real music catalogs, pick lyric lines and platform destinations, and generate high-resolution PNG posters ready to download, collect, or print.

[BeatPrints Web](https://github.com/sdrpsps/beatprints-web) is built on top of
[BeatPrints by TrueMyst / elysianmyst](https://github.com/TrueMyst/BeatPrints):
the upstream project provides the core poster typography and rendering engine, while this project adds a modern web creation interface, an HTTP API, multi-platform music catalog integrations, and self-hosting capabilities.

[English](README.md) · [简体中文](README.zh-CN.md)

[Quick Start](#quick-start) · [Docker Deployment](#docker-deployment) · [API Documentation](apps/api/README.md) · [Frontend Guide](apps/web/README.md)

</div>

![BeatPrints Web Interface](https://us1.workspace.org/d/v2/yaikbaKQV0odeVqFeJ1su6GLxtf2aX-x/2BK7NEM3R11V)

## Relationship with Upstream BeatPrints

[BeatPrints](https://github.com/TrueMyst/BeatPrints) is a music poster generator created by TrueMyst (@elysianmyst), defining the poster layout, typography, themes, color palettes, and PNG rendering pipeline.
This project directly utilizes the upstream BeatPrints generator—it is neither an unrelated project with the same name nor a reimplementation of its core design.

BeatPrints Web extends the upstream generator by providing:

- A responsive React web interface to complete the entire poster creation flow in your browser;
- A FastAPI backend service for searching music catalogs, fetching lyrics, and rendering posters;
- Multi-source catalog integrations (QQ Music, NetEase Cloud Music, Spotify) and QR destination resolution;
- Production-ready Docker Compose configurations, unified multi-architecture container images, and automated release workflows.

If you only need the CLI generator or want to explore the underlying poster typography engine, please visit [TrueMyst/BeatPrints](https://github.com/TrueMyst/BeatPrints). If you want to use BeatPrints in a web browser or deploy it as an HTTP service, you can use this project directly.

## What is BeatPrints Web

BeatPrints Web is a self-hostable web application built on top of the original BeatPrints. Rather than generating fictitious content, it fetches authentic cover artwork and track metadata from QQ Music, NetEase Cloud Music, or Spotify, allowing you to select and confirm the exact release before invoking BeatPrints to render the final poster.

The creation flow for a track poster is straightforward:

```text
Search track → Select exact release → Optionally pick up to 4 lyric lines → Optionally choose a platform destination → Adjust styling → Download PNG
```

Album posters follow the same creation flow, with additional options for track indexing and tracklist shuffling. Generated posters are streamed directly to the browser; the server stores no poster images.

> [!IMPORTANT]
> **Metadata source** and **Poster platform destination** are two independent concepts: `provider` determines where catalog metadata is fetched from (QQ Music, NetEase Cloud Music, or Spotify), while `qr_platform` determines whether the poster includes a scannable code/link for Spotify, Apple Music, QQ Music, or NetEase Cloud Music. If no platform is selected, the poster will not display any platform mark or QR code.

## Features

- **Precise Release Selection**: Search for tracks or albums and verify the exact release with cover artwork, artist credits, release dates, and duration.
- **Lyric Selection & Editing**: Select 0 to 4 lyric lines for track posters, or input custom lyrics manually.
- **Scannable Platform Destinations**: Add an authentic Spotify Code, or a QR code for Apple Music, QQ Music, or NetEase Cloud Music.
- **Conservative Cross-Platform Matching**: Prioritizes stable identifiers (e.g., ISRC); falls back to ranked candidates or manual URL resolution when ambiguous—never silently chooses a weak match.
- **Customizable Appearance**: Choose from curated themes (Light, Dark, Catppuccin, Gruvbox, Nord, RosePine, Everforest) and optional cover-extracted accent colors.
- **Track & Album Modes**: Create posters for individual tracks or full albums, with album-specific options for track indexing and tracklist shuffling.
- **Multilingual Interface**: Full i18n support for English, Simplified Chinese, and Traditional Chinese.
- **All-in-One Deployment**: A single unified container image serves both the React static frontend and the FastAPI backend.

## Quick Start

### Prerequisites

- Python 3.14
- [uv](https://docs.astral.sh/uv/)
- pnpm 11

### Local Development

```bash
git clone https://github.com/sdrpsps/beatprints-web.git
cd beatprints-web

cp .env.example .env
make setup
make dev
```

Once started, you can access:

- Web: <http://localhost:5173>
- API: <http://localhost:8000>
- OpenAPI Docs: <http://localhost:8000/docs>

Spotify search is optional. When needed, configure `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET` in `.env`; without Spotify credentials, QQ Music and NetEase Cloud Music search remain fully functional.

### Common Commands

```bash
make help         # View all available make targets
make dev          # Start both API and Web concurrently
make dev:api      # Start FastAPI backend only
make dev:web      # Start Vite frontend only
make test:api     # Run API tests
make lint:api     # Run Python code formatting and lint checks
make build        # Build both API and Web
```

Full frontend verification:

```bash
pnpm --filter @beatprints/web lint
pnpm --filter @beatprints/web build
```

## Docker Deployment

This project provides a single-container deployment where frontend static assets are bundled and served directly by FastAPI, exposing only port `8000`.

```bash
cp .env.example .env
docker compose up -d --build
docker compose ps
```

Check service health:

```bash
curl http://localhost:8000/health
```

Update and view logs:

```bash
git pull
docker compose up -d --build
docker compose logs -f beatprints-api
```

We recommend using Nginx, Caddy, or Traefik as a reverse proxy targeting container port `8000`. Rendering a `2280 × 3480` high-resolution poster consumes significant memory; for a server with 1 GB RAM, we recommend keeping the default concurrency settings:

```dotenv
WEB_CONCURRENCY=1
MAX_CONCURRENT_JOBS=1
```

### Authentication

When `API_KEY` is left blank, both the web interface and API endpoints are publicly accessible. When `API_KEY` is configured, protected `/v1` endpoints require a Bearer Token.

Do not embed a long-lived API key into a publicly accessible Vite frontend build. For production deployments requiring access control, add an authentication layer, reverse proxy, or API gateway in front of the application. If making the API public, ensure proper rate limiting and abuse prevention are configured.

## Configuration

Key environment variables are documented in [`.env.example`](.env.example):

| Variable | Description | Default |
| --- | --- | --- |
| `PORT` | API listen port | `8000` |
| `API_KEY` | Optional Bearer Token for `/v1` endpoints | Blank |
| `CORS_ORIGINS` | Allowed CORS origins, comma-separated | Blank |
| `SPOTIFY_CLIENT_ID` / `SPOTIFY_CLIENT_SECRET` | Enable Spotify search and metadata | Blank |
| `SPOTIFY_MARKET` | Spotify market code | `US` |
| `APPLE_MUSIC_STOREFRONT` | Apple Music storefront code | `US` |
| `METADATA_CACHE_TTL_SECONDS` | Metadata cache expiration time in seconds | `600` |
| `MAX_CONCURRENT_JOBS` | Maximum concurrent poster rendering jobs per worker | `1` |

## Project Structure

```text
.
├── apps/
│   ├── api/          # FastAPI backend, music catalog integrations, and poster rendering
│   └── web/          # React, Vite, Tailwind CSS, and shadcn/ui frontend
├── docs/             # Product flows and architecture documentation
├── packages/         # Shared frontend packages
├── Makefile          # Unified development, testing, build, and deployment targets
├── pyproject.toml    # Python project configuration and dependencies
├── pnpm-workspace.yaml
└── docker-compose.yml
```

Dependency boundaries:

- Python dependencies are managed in the root `pyproject.toml` and locked via `uv.lock`.
- Web dependencies are managed via pnpm workspace and `pnpm-lock.yaml`.
- The `Makefile` orchestrates unified cross-package commands.

Further reading:

- [Frontend Development Guide](apps/web/README.md)
- [API Deployment & Examples](apps/api/README.md)
- [Frontend Product Journey & API Mapping](docs/frontend-product-brief.md)

## API Overview

Except for poster rendering endpoints that directly return `image/png`, all JSON responses follow a consistent envelope:

```json
{
  "code": 0,
  "data": {},
  "message": "success"
}
```

Primary endpoints include:

```http
GET  /v1/search
GET  /v1/lyrics
GET  /v1/platform-links/{platform}
POST /v1/posters/track
POST /v1/posters/album
```

For complete request schemas, cross-platform matching logic, error handling, and `curl` examples, please refer to the [BeatPrints API Documentation](apps/api/README.md) or visit `/docs` after launching the server.

## Build & Release

GitHub Actions automatically builds multi-architecture container images containing both the Web UI and API:

```text
ghcr.io/sdrpsps/beatprints-web:latest
```

- Pull Requests build `linux/amd64` images for CI validation without pushing.
- `vX.Y.Z` tags publish both `linux/amd64` and `linux/arm64` images.
- Release Please maintains semantic versions, changelogs, and GitHub Releases based on Conventional Commits.

Versioning follows standard rules: `fix:` bumps patch, `feat:` bumps minor, and commits containing `!` or `BREAKING CHANGE:` bump major.

## Attribution & License

This project is built on top of [BeatPrints](https://github.com/TrueMyst/BeatPrints) created by TrueMyst / elysianmyst, with all original attribution preserved.

This project is licensed under [CC BY-NC-SA 4.0](LICENSE) for non-commercial use only. When using, distributing, or creating derivative works, please retain attribution and share under the same license; obtain commercial authorization from the original author prior to any commercial use.
