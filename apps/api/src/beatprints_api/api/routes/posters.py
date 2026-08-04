import asyncio
import logging
import time
from urllib.parse import quote
from typing import Annotated

from fastapi import APIRouter, Body, Depends
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import Response

from beatprints_api.api.dependencies import require_api_key
from beatprints_api.config import settings
from beatprints_api.exceptions import (
    IntegrationNotConfiguredError,
    InvalidInputError,
    UpstreamError,
    UpstreamServiceError,
)
from beatprints_api.logging import log_event
from beatprints_api.models import ApiResponse, AlbumPosterRequest, TrackPosterRequest
from beatprints_api.services import posters as poster_service
from beatprints_api.services.rendering import PosterResult

router = APIRouter(
    prefix="/v1/posters",
    tags=["Posters"],
    dependencies=[Depends(require_api_key)],
)
logger = logging.getLogger(__name__)
poster_slots = asyncio.Semaphore(settings.max_concurrent_jobs)
ERROR_RESPONSES = {
    401: {"model": ApiResponse[object], "description": "API Key 缺失或错误。"},
    422: {"model": ApiResponse[object], "description": "请求参数或输入组合不合法。"},
    502: {"model": ApiResponse[object], "description": "上游数据或封面服务失败。"},
    503: {"model": ApiResponse[object], "description": "指定的音乐平台尚未配置。"},
    500: {"model": ApiResponse[object], "description": "服务内部错误。"},
}

TRACK_EXAMPLES = {
    "catalog_no_qr": {
        "summary": "使用已选歌曲生成，不显示平台二维码",
        "description": "未提供 qr_platform，因此左下角不显示任何平台标识或二维码。",
        "value": {
            "provider": "spotify",
            "catalog_id": "7lp5evZr7qEDwlv5PS8b6i",
            "theme": "Light",
            "accent": True,
        },
    },
    "spotify_qr_auto": {
        "summary": "显示 Spotify 二维码，自动使用源链接",
        "description": (
            "元数据来源和二维码平台都是 Spotify，可以省略 platform_links.spotify。"
        ),
        "value": {
            "provider": "spotify",
            "catalog_id": "7lp5evZr7qEDwlv5PS8b6i",
            "qr_platform": "spotify",
            "theme": "Light",
            "accent": True,
        },
    },
    "apple_music_qr": {
        "summary": "用 Spotify 资料生成 Apple Music 版本",
        "description": (
            "provider 只决定元数据来源；qr_platform 单独指定海报二维码平台。"
        ),
        "value": {
            "provider": "spotify",
            "catalog_id": "7lp5evZr7qEDwlv5PS8b6i",
            "platform_links": {
                "apple_music": (
                    "https://music.apple.com/us/album/summer-breeze/1790520587"
                ),
                "qq_music": "https://y.qq.com/n/ryqq/songDetail/001example",
                "netease_music": "https://music.163.com/song?id=123456",
            },
            "qr_platform": "apple_music",
            "theme": "Light",
            "accent": True,
        },
    },
    "qq_music_qr": {
        "summary": "用 Spotify 资料生成 QQ 音乐版本",
        "description": "QQ 音乐不是元数据源，因此需要显式提供对应歌曲链接。",
        "value": {
            "provider": "spotify",
            "catalog_id": "7lp5evZr7qEDwlv5PS8b6i",
            "platform_links": {
                "qq_music": "https://y.qq.com/n/ryqq/songDetail/001example",
            },
            "qr_platform": "qq_music",
            "theme": "Light",
            "accent": True,
        },
    },
    "custom": {
        "summary": "使用完全自定义资料",
        "value": {
            "metadata": {
                "title": "Summer Breeze",
                "artists": ["Piper"],
                "album": "Summer Breeze",
                "released": "1983",
                "duration": "03:23",
                "cover_url": "https://example.com/cover.jpg",
                "label": "Light In The Attic Records",
            },
            "lyrics": "First line\nSecond line\nThird line\nFourth line",
            "theme": "Light",
            "accent": True,
        },
    },
}

ALBUM_EXAMPLES = {
    "catalog_no_qr": {
        "summary": "使用已选专辑生成，不显示平台二维码",
        "description": "未提供 qr_platform，因此左下角不显示任何平台标识或二维码。",
        "value": {
            "provider": "spotify",
            "catalog_id": "614LGcMwiEpyQ5SVg6S5Im",
            "theme": "Light",
            "accent": True,
            "indexing": True,
        },
    },
    "spotify_qr_auto": {
        "summary": "显示 Spotify 二维码，自动使用源链接",
        "description": (
            "明确选择 spotify 后，服务会使用 Spotify 专辑元数据中的跳转链接。"
        ),
        "value": {
            "provider": "spotify",
            "catalog_id": "614LGcMwiEpyQ5SVg6S5Im",
            "qr_platform": "spotify",
            "theme": "Light",
            "accent": True,
            "indexing": True,
            "shuffle": False,
        },
    },
    "netease_music_qr": {
        "summary": "用 Spotify 资料生成网易云音乐版本",
        "description": "网易云音乐不是元数据源，因此需要显式提供对应专辑链接。",
        "value": {
            "provider": "spotify",
            "catalog_id": "614LGcMwiEpyQ5SVg6S5Im",
            "platform_links": {
                "netease_music": "https://music.163.com/album?id=123456",
            },
            "qr_platform": "netease_music",
            "theme": "Light",
            "accent": True,
            "indexing": True,
            "shuffle": False,
        },
    },
    "custom": {
        "summary": "使用完全自定义资料",
        "value": {
            "metadata": {
                "title": "Summer Breeze",
                "artists": ["Piper"],
                "released": "1983",
                "tracks": [
                    "Shine On",
                    "Summer Breeze",
                    "Hot Sand",
                    "Gentle Shower",
                ],
                "cover_url": "https://example.com/cover.jpg",
                "label": "Light In The Attic Records",
            },
            "theme": "Light",
            "accent": True,
            "indexing": True,
            "shuffle": False,
        },
    },
}


def _image_response(
    result: tuple[bytes, str] | PosterResult,
    queue_ms: float,
) -> Response:
    timings = {"queue": queue_ms}
    if isinstance(result, PosterResult):
        content = result.content
        filename = result.filename
        timings.update(result.timings_ms)
    else:
        content, filename = result

    server_timing = ", ".join(
        f"{name};dur={duration:.0f}" for name, duration in timings.items()
    )
    safe_filename = (
        filename
        if filename.isascii() and all(character not in '"\\;' for character in filename)
        else "beatprints-poster.png"
    )
    content_disposition = (
        f'inline; filename="{safe_filename}"; ' f"filename*=UTF-8''{quote(filename)}"
    )
    return Response(
        content=content,
        media_type="image/png",
        headers={
            "Content-Disposition": content_disposition,
            "Server-Timing": server_timing,
        },
    )


async def _generate(
    generator,
    request: TrackPosterRequest | AlbumPosterRequest,
) -> Response:
    queue_started_at = time.perf_counter()
    try:
        async with poster_slots:
            queue_ms = (time.perf_counter() - queue_started_at) * 1000
            result = await run_in_threadpool(generator, request)
    except ValueError as exc:
        raise InvalidInputError(str(exc)) from exc
    except IntegrationNotConfiguredError as exc:
        raise UpstreamServiceError(str(exc), unavailable=True) from exc
    except UpstreamError as exc:
        raise UpstreamServiceError(str(exc)) from exc

    timings = (
        result.timings_ms if isinstance(result, PosterResult) else {}
    )
    log_event(
        logger,
        logging.INFO,
        "poster_generated",
        "Poster generated",
        poster_type="track" if isinstance(request, TrackPosterRequest) else "album",
        provider=request.provider,
        theme=request.theme,
        qr_platform=request.qr_platform or "none",
        response_bytes=(
            len(result.content)
            if isinstance(result, PosterResult)
            else len(result[0])
        ),
        queue_ms=round(queue_ms),
        timings_ms={name: round(duration) for name, duration in timings.items()},
    )
    return _image_response(result, queue_ms)


@router.post(
    "/track",
    summary="生成歌曲海报",
    description=(
        "生成包含歌曲标题、歌手、时长、歌词、封面和调色板的 PNG。\n\n"
        "`provider` 只控制元数据来源；`qr_platform` 单独控制"
        "左下角显示哪个音乐平台。未提供 `qr_platform` 时不显示平台标识或二维码。"
        "每张海报最多显示一个二维码，其颜色从封面提取，并在白色背景上保持安全"
        "对比度。"
    ),
    responses={
        200: {
            "description": (
                "生成成功，响应体是 PNG 图片。只有请求明确提供 qr_platform 时，"
                "图片左下角才包含对应平台的封面取色二维码。"
            ),
            "content": {"image/png": {}},
        },
        **ERROR_RESPONSES,
    },
    response_class=Response,
)
async def track_poster(
    request: Annotated[
        TrackPosterRequest,
        Body(
            description=(
                "`catalog_id`、`metadata` 必须且只能填写其中一个；"
                "`provider` 选择元数据来源；`qr_platform` 可选，并明确选择唯一的"
                "二维码平台。不填 `qr_platform` 就不显示。是否可复用来源链接由"
                "已选择的目的地 integration 决定；否则须在 `platform_links` 中提供链接。"
            ),
            openapi_examples=TRACK_EXAMPLES,
        ),
    ],
) -> Response:
    return await _generate(poster_service.generate_track, request)


@router.post(
    "/album",
    summary="生成专辑海报",
    description=(
        "生成包含专辑标题、歌手、曲目列表、封面和调色板的 PNG。\n\n"
        "`provider` 只控制元数据来源；`qr_platform` 单独控制"
        "左下角显示哪个音乐平台。未提供 `qr_platform` 时不显示平台标识或二维码。"
        "每张海报最多显示一个二维码，其颜色从封面提取，并在白色背景上保持安全"
        "对比度。"
    ),
    responses={
        200: {
            "description": (
                "生成成功，响应体是 PNG 图片。只有请求明确提供 qr_platform 时，"
                "图片左下角才包含对应平台的封面取色二维码。"
            ),
            "content": {"image/png": {}},
        },
        **ERROR_RESPONSES,
    },
    response_class=Response,
)
async def album_poster(
    request: Annotated[
        AlbumPosterRequest,
        Body(
            description=(
                "`catalog_id`、`metadata` 必须且只能填写其中一个；"
                "`provider` 选择元数据来源；`qr_platform` 可选，并明确选择唯一的"
                "二维码平台。不填 `qr_platform` 就不显示。是否可复用来源链接由"
                "已选择的目的地 integration 决定；否则须在 `platform_links` 中提供链接。"
            ),
            openapi_examples=ALBUM_EXAMPLES,
        ),
    ],
) -> Response:
    return await _generate(poster_service.generate_album, request)
