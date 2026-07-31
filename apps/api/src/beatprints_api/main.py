import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from beatprints_api.api.errors import register_exception_handlers
from beatprints_api.api.middleware import request_context_middleware
from beatprints_api.api.routes import catalog_router, posters_router, system_router
from beatprints_api.config import settings


def create_app(web_root: Path | None = None) -> FastAPI:
    app = FastAPI(
        title="BeatPrints API",
        version=settings.build_version,
        description=(
            "通过可切换的音乐平台和 LRClib 自动补全资料，或使用调用方提供的完整资料，"
            "生成 BeatPrints 风格的歌曲与专辑 PNG 海报。\n\n"
            "除 PNG 成功响应外，JSON 响应统一使用 code、data、message 结构。"
        ),
        openapi_tags=[
            {"name": "System", "description": "服务状态检查。"},
            {"name": "Catalog", "description": "搜索音乐资料和查询可用主题。"},
            {"name": "Posters", "description": "生成歌曲或专辑 PNG 海报。"},
        ],
    )

    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(settings.cors_origins),
            allow_credentials=False,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type"],
            expose_headers=["X-Request-ID", "X-Process-Time", "Server-Timing"],
        )

    register_exception_handlers(app)
    app.middleware("http")(request_context_middleware)

    app.include_router(system_router)
    app.include_router(catalog_router)
    app.include_router(posters_router)

    resolved_web_root = web_root or Path(os.getenv("WEB_DIST_DIR", "/app/web"))
    index_file = resolved_web_root / "index.html"
    if index_file.is_file():
        resolved_web_root = resolved_web_root.resolve()
        index_file = resolved_web_root / "index.html"

        @app.api_route(
            "/{path:path}",
            methods=["GET", "HEAD"],
            include_in_schema=False,
        )
        def serve_web_app(path: str) -> FileResponse:
            requested_file = (resolved_web_root / path).resolve()
            if (
                requested_file.is_relative_to(resolved_web_root)
                and requested_file.is_file()
            ):
                return FileResponse(requested_file)
            return FileResponse(index_file)

    return app


app = create_app()
