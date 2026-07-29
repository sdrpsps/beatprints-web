import asyncio
from typing import Annotated

from fastapi import APIRouter, Body, Depends
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import Response

from beatprints_api.api.dependencies import require_api_key
from beatprints_api.config import settings
from beatprints_api.exceptions import InvalidInputError, UpstreamServiceError
from beatprints_api.models import ApiResponse, AlbumPosterRequest, TrackPosterRequest
from beatprints_api.services import beatprints as beatprints_service
from beatprints_api.spotify import SpotifyError, SpotifyNotConfiguredError

router = APIRouter(
    prefix="/v1/posters",
    tags=["Posters"],
    dependencies=[Depends(require_api_key)],
)
poster_slots = asyncio.Semaphore(settings.max_concurrent_jobs)
ERROR_RESPONSES = {
    401: {"model": ApiResponse[object], "description": "API Key 缺失或错误。"},
    422: {"model": ApiResponse[object], "description": "请求参数或输入组合不合法。"},
    502: {"model": ApiResponse[object], "description": "上游数据或封面服务失败。"},
    503: {"model": ApiResponse[object], "description": "指定的音乐平台尚未配置。"},
    500: {"model": ApiResponse[object], "description": "服务内部错误。"},
}

TRACK_EXAMPLES = {
    "search": {
        "summary": "在 Spotify 搜索并自动生成",
        "value": {
            "provider": "spotify",
            "query": "Summer Breeze Seals and Crofts",
            "theme": "Light",
            "accent": True,
        },
    },
    "catalog_id": {
        "summary": "使用 Spotify 搜索结果生成（推荐）",
        "value": {
            "provider": "spotify",
            "catalog_id": "3B0ms7Xlxl16tRztKHpcu9",
            "theme": "Light",
            "accent": True,
        },
    },
    "custom": {
        "summary": "使用完全自定义资料",
        "value": {
            "metadata": {
                "title": "Summer Breeze",
                "artists": ["Seals and Crofts"],
                "album": "Seals & Crofts' Greatest Hits",
                "released": "October 11, 1977",
                "duration": "03:25",
                "cover_url": "https://example.com/cover.jpg",
                "label": "Warner Records",
            },
            "lyrics": "First line\nSecond line\nThird line\nFourth line",
            "theme": "Light",
            "accent": True,
        },
    },
}

ALBUM_EXAMPLES = {
    "search": {
        "summary": "在 Spotify 搜索并自动生成",
        "value": {
            "provider": "spotify",
            "query": "Summer Breeze Seals and Crofts",
            "theme": "Light",
            "accent": True,
            "indexing": True,
        },
    },
    "catalog_id": {
        "summary": "使用 Spotify 搜索结果生成（推荐）",
        "value": {
            "provider": "spotify",
            "catalog_id": "1Ugdi2OTxKopVVqsprp5pb",
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
                "artists": ["Seals & Crofts"],
                "released": "June 10, 1981",
                "tracks": ["Hummingbird", "Funny Little Man", "Say", "Summer Breeze"],
                "cover_url": "https://example.com/cover.jpg",
                "label": "Warner Records",
            },
            "theme": "Light",
            "accent": True,
            "indexing": True,
            "shuffle": False,
        },
    },
}


def _image_response(result: tuple[bytes, str]) -> Response:
    content, filename = result
    return Response(
        content=content,
        media_type="image/png",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


async def _generate(
    generator,
    request: TrackPosterRequest | AlbumPosterRequest,
) -> Response:
    try:
        async with poster_slots:
            result = await run_in_threadpool(generator, request)
    except ValueError as exc:
        raise InvalidInputError(str(exc)) from exc
    except SpotifyNotConfiguredError as exc:
        raise UpstreamServiceError(str(exc), unavailable=True) from exc
    except SpotifyError as exc:
        raise UpstreamServiceError(str(exc)) from exc
    except beatprints_service.UpstreamError as exc:
        raise UpstreamServiceError(str(exc)) from exc
    return _image_response(result)


@router.post(
    "/track",
    summary="生成歌曲海报",
    description="生成包含歌曲标题、歌手、时长、歌词、封面和调色板的 PNG。",
    responses={
        200: {
            "description": "生成成功，响应体是 PNG 图片。",
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
                "`query`、`catalog_id`、`metadata` 必须且只能填写其中一个；"
                "Deezer 和 Spotify 都通过 provider 选择。"
            ),
            openapi_examples=TRACK_EXAMPLES,
        ),
    ],
) -> Response:
    return await _generate(beatprints_service.generate_track, request)


@router.post(
    "/album",
    summary="生成专辑海报",
    description="生成包含专辑标题、歌手、曲目列表、封面和调色板的 PNG。",
    responses={
        200: {
            "description": "生成成功，响应体是 PNG 图片。",
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
                "`query`、`catalog_id`、`metadata` 必须且只能填写其中一个；"
                "Deezer 和 Spotify 都通过 provider 选择。"
            ),
            openapi_examples=ALBUM_EXAMPLES,
        ),
    ],
) -> Response:
    return await _generate(beatprints_service.generate_album, request)
