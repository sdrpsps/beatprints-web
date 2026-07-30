from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.concurrency import run_in_threadpool

from beatprints_api.api.dependencies import require_api_key
from beatprints_api.exceptions import UpstreamServiceError
from beatprints_api.models import (
    ApiResponse,
    AppleMusicMatchData,
    CatalogProvider,
    LyricsPreviewData,
    SearchProvider,
    SearchResult,
    SpotifyMatchData,
    ThemesData,
)
from beatprints_api.services import beatprints as beatprints_service
from beatprints_api.spotify import SpotifyNotConfiguredError

router = APIRouter(
    prefix="/v1",
    tags=["Catalog"],
    dependencies=[Depends(require_api_key)],
)

ERROR_RESPONSES = {
    401: {"model": ApiResponse[object], "description": "API Key 缺失或错误。"},
    422: {"model": ApiResponse[object], "description": "请求参数校验失败。"},
    502: {"model": ApiResponse[object], "description": "音乐目录请求失败。"},
    503: {
        "model": ApiResponse[object],
        "description": "服务端尚未配置指定的数据源。",
    },
}

THEMES = [
    "Light",
    "Dark",
    "Catppuccin",
    "Gruvbox",
    "Nord",
    "RosePine",
    "Everforest",
]


@router.get(
    "/themes",
    summary="获取海报主题",
    description="返回歌曲和专辑海报都支持的主题名称。",
    response_model=ApiResponse[ThemesData],
    responses={401: ERROR_RESPONSES[401]},
)
def themes() -> ApiResponse[ThemesData]:
    return ApiResponse(
        code=0,
        data=ThemesData(themes=THEMES),
        message="success",
    )


@router.get(
    "/search",
    summary="搜索歌曲或专辑",
    description=(
        "按 provider 在音乐目录中搜索，返回的 provider + id 可以直接交给海报生成接口。"
        "provider=spotify 需要服务端配置 Spotify Client Credentials；"
        "provider=all 会合并当前已启用的来源。"
    ),
    response_model=ApiResponse[list[SearchResult]],
    response_model_exclude_none=True,
    responses=ERROR_RESPONSES,
)
async def search(
    query: Annotated[
        str,
        Query(
            min_length=1,
            max_length=500,
            description="歌名、专辑名或歌手关键词，允许近似拼写。",
            examples=["Summer Breeze Piper"],
        ),
    ],
    type: Annotated[
        Literal["track", "album"],
        Query(description="搜索类型：track 表示歌曲，album 表示专辑。"),
    ] = "track",
    provider: Annotated[
        SearchProvider,
        Query(
            description="搜索数据源：deezer、spotify 或 all。",
            examples=["all"],
        ),
    ] = "spotify",
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=20,
            description="每个数据源最多返回多少条结果。",
            examples=[5],
        ),
    ] = 5,
) -> ApiResponse[list[SearchResult]]:
    try:
        results = await run_in_threadpool(
            beatprints_service.search_catalog,
            query,
            type,
            limit,
            provider,
        )
    except SpotifyNotConfiguredError as exc:
        raise UpstreamServiceError(str(exc), unavailable=True) from exc
    except beatprints_service.UpstreamError as exc:
        raise UpstreamServiceError(str(exc)) from exc
    except Exception as exc:
        raise UpstreamServiceError("Music catalog request failed") from exc

    return ApiResponse(
        code=0,
        data=[SearchResult.model_validate(item) for item in results],
        message="success",
    )


@router.get(
    "/lyrics",
    summary="预览歌曲歌词",
    description=(
        "按搜索结果中未改变的 provider + id 获取 LRClib 歌词，"
        "返回规范化非空行供前端任选四行。纯音乐返回 instrumental=true 和空行列表。"
    ),
    response_model=ApiResponse[LyricsPreviewData],
    response_model_exclude_none=True,
    responses=ERROR_RESPONSES,
)
async def preview_lyrics(
    provider: Annotated[
        CatalogProvider,
        Query(description="所选歌曲的元数据来源，必须与搜索结果一致。"),
    ],
    catalog_id: Annotated[
        str,
        Query(
            min_length=1,
            description="所选歌曲在 provider 中的 ID，来自 /v1/search。",
        ),
    ],
) -> ApiResponse[LyricsPreviewData]:
    try:
        result = await run_in_threadpool(
            beatprints_service.preview_lyrics,
            provider,
            catalog_id,
        )
    except SpotifyNotConfiguredError as exc:
        raise UpstreamServiceError(str(exc), unavailable=True) from exc
    except beatprints_service.UpstreamError as exc:
        raise UpstreamServiceError(str(exc)) from exc
    except Exception as exc:
        raise UpstreamServiceError("Lyrics request failed") from exc

    return ApiResponse(code=0, data=result, message="success")


@router.get(
    "/platform-links/apple-music",
    summary="自动匹配 Apple Music 链接",
    description=(
        "使用已选 Spotify 或 Deezer 条目的 provider + catalog_id 获取原始资料，"
        "再按标题、艺人、专辑和时长（或发行年份）保守匹配 Apple Music。"
    ),
    response_model=ApiResponse[AppleMusicMatchData],
    response_model_exclude_none=True,
    responses={**ERROR_RESPONSES, 404: {"model": ApiResponse[object]}},
)
async def match_apple_music(
    provider: Annotated[
        CatalogProvider, Query(description="已选条目的元数据来源。")
    ],
    catalog_id: Annotated[
        str, Query(min_length=1, description="已选条目的原始目录 ID。")
    ],
    type: Annotated[
        Literal["track", "album"], Query(description="已选条目的类型。")
    ],
) -> ApiResponse[AppleMusicMatchData]:
    try:
        result = await run_in_threadpool(
            beatprints_service.match_apple_music,
            provider,
            catalog_id,
            type,
        )
    except beatprints_service.AppleMusicNoMatchError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SpotifyNotConfiguredError as exc:
        raise UpstreamServiceError(str(exc), unavailable=True) from exc
    except beatprints_service.UpstreamError as exc:
        raise UpstreamServiceError(str(exc)) from exc
    except Exception as exc:
        raise UpstreamServiceError("Apple Music matching failed") from exc
    return ApiResponse(code=0, data=result, message="success")


@router.get(
    "/platform-links/apple-music/resolve",
    summary="读取 Apple Music 链接资料",
    response_model=ApiResponse[AppleMusicMatchData],
    response_model_exclude_none=True,
    responses={**ERROR_RESPONSES, 404: {"model": ApiResponse[object]}},
)
async def resolve_apple_music_url(
    url: Annotated[str, Query(min_length=1, max_length=2000, description="Apple Music 公开链接。")],
) -> ApiResponse[AppleMusicMatchData]:
    try:
        result = await run_in_threadpool(beatprints_service.resolve_apple_music_url, url)
    except beatprints_service.AppleMusicNoMatchError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except beatprints_service.UpstreamError as exc:
        raise UpstreamServiceError(str(exc)) from exc
    return ApiResponse(code=0, data=result, message="success")


@router.get(
    "/platform-links/spotify",
    summary="自动匹配 Spotify 链接",
    description="使用已选 Deezer 条目的 provider + catalog_id 保守匹配 Spotify。",
    response_model=ApiResponse[SpotifyMatchData],
    response_model_exclude_none=True,
    responses={**ERROR_RESPONSES, 404: {"model": ApiResponse[object]}},
)
async def match_spotify(
    provider: Annotated[
        Literal["deezer"], Query(description="已选条目的元数据来源。")
    ],
    catalog_id: Annotated[
        str, Query(min_length=1, description="已选 Deezer 条目的原始目录 ID。")
    ],
    type: Annotated[
        Literal["track", "album"], Query(description="已选条目的类型。")
    ],
) -> ApiResponse[SpotifyMatchData]:
    try:
        result = await run_in_threadpool(
            beatprints_service.match_deezer_to_spotify, catalog_id, type
        )
    except beatprints_service.AppleMusicNoMatchError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SpotifyNotConfiguredError as exc:
        raise UpstreamServiceError(str(exc), unavailable=True) from exc
    except beatprints_service.UpstreamError as exc:
        raise UpstreamServiceError(str(exc)) from exc
    return ApiResponse(code=0, data=result, message="success")


@router.get(
    "/platform-links/spotify/resolve",
    summary="读取 Spotify 链接资料",
    response_model=ApiResponse[SpotifyMatchData],
    response_model_exclude_none=True,
    responses={**ERROR_RESPONSES, 404: {"model": ApiResponse[object]}},
)
async def resolve_spotify_url(
    url: Annotated[str, Query(min_length=1, max_length=2000, description="Spotify 公开链接。")],
) -> ApiResponse[SpotifyMatchData]:
    try:
        result = await run_in_threadpool(beatprints_service.resolve_spotify_url, url)
    except beatprints_service.AppleMusicNoMatchError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SpotifyNotConfiguredError as exc:
        raise UpstreamServiceError(str(exc), unavailable=True) from exc
    except beatprints_service.UpstreamError as exc:
        raise UpstreamServiceError(str(exc)) from exc
    return ApiResponse(code=0, data=result, message="success")


@router.get(
    "/platform-links/{platform}/candidates",
    summary="搜索目标平台候选版本",
    description=(
        "从用户准确选择的 provider + catalog_id 获取源资料，"
        "返回按标题、艺人、专辑、年份、时长或歌曲数量排序的目标平台候选。"
        "候选不会被自动确认，用户选择后应再调用 resolve 获取当前资料。"
    ),
    response_model=ApiResponse[list[SpotifyMatchData]],
    response_model_exclude_none=True,
    responses=ERROR_RESPONSES,
)
async def platform_link_candidates(
    platform: Literal[
        "spotify", "apple_music", "qq_music", "netease_music"
    ],
    provider: Annotated[CatalogProvider, Query()],
    catalog_id: Annotated[str, Query(min_length=1)],
    type: Annotated[Literal["track", "album"], Query()],
    limit: Annotated[int, Query(ge=1, le=10)] = 8,
) -> ApiResponse[list[SpotifyMatchData]]:
    try:
        result = await run_in_threadpool(
            beatprints_service.platform_link_candidates,
            provider,
            catalog_id,
            type,
            platform,
            limit,
        )
    except SpotifyNotConfiguredError as exc:
        raise UpstreamServiceError(str(exc), unavailable=True) from exc
    except beatprints_service.UpstreamError as exc:
        raise UpstreamServiceError(str(exc)) from exc
    return ApiResponse(code=0, data=result, message="success")


@router.get("/platform-links/{platform}", response_model=ApiResponse[SpotifyMatchData])
async def match_china_platform(
    platform: Literal["qq_music", "netease_music"],
    provider: Annotated[CatalogProvider, Query()],
    catalog_id: Annotated[str, Query(min_length=1)],
    type: Annotated[Literal["track", "album"], Query()],
) -> ApiResponse[SpotifyMatchData]:
    try:
        result = await run_in_threadpool(
            beatprints_service.match_china_platform, provider, catalog_id, type, platform
        )
    except beatprints_service.AppleMusicNoMatchError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except beatprints_service.UpstreamError as exc:
        raise UpstreamServiceError(str(exc)) from exc
    return ApiResponse(code=0, data=result, message="success")


@router.get(
    "/platform-links/{platform}/resolve",
    response_model=ApiResponse[SpotifyMatchData],
    response_model_exclude_none=True,
)
async def resolve_platform_url(
    platform: Literal[
        "spotify", "apple_music", "qq_music", "netease_music"
    ],
    url: Annotated[str, Query(min_length=1, max_length=2000)],
) -> ApiResponse[SpotifyMatchData]:
    try:
        result = await run_in_threadpool(
            beatprints_service.resolve_platform_url, platform, url
        )
    except beatprints_service.AppleMusicNoMatchError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SpotifyNotConfiguredError as exc:
        raise UpstreamServiceError(str(exc), unavailable=True) from exc
    except beatprints_service.UpstreamError as exc:
        raise UpstreamServiceError(str(exc)) from exc
    return ApiResponse(code=0, data=result, message="success")
