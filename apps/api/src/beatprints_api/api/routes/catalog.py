from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.concurrency import run_in_threadpool

from beatprints_api.api.dependencies import require_api_key
from beatprints_api.exceptions import UpstreamServiceError
from beatprints_api.models import (
    ApiResponse,
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


@router.get(
    "/platform-links/{platform}",
    summary="自动匹配目标平台链接",
    description=(
        "从用户明确选择的 provider + catalog_id 读取源条目，并保守匹配目标平台。"
        "每个平台都使用相同的请求与响应格式；匹配策略（例如 Spotify 同源复用）"
        "仅是服务端实现细节。"
    ),
    response_model=ApiResponse[SpotifyMatchData],
    response_model_exclude_none=True,
    responses={**ERROR_RESPONSES, 404: {"model": ApiResponse[object]}},
)
async def match_platform_link(
    platform: Literal["spotify", "apple_music", "qq_music", "netease_music"],
    provider: Annotated[CatalogProvider, Query(description="已选条目的元数据来源。")],
    catalog_id: Annotated[str, Query(min_length=1, description="已选条目的原始目录 ID。")],
    type: Annotated[Literal["track", "album"], Query(description="已选条目的类型。")],
) -> ApiResponse[SpotifyMatchData]:
    try:
        result = await run_in_threadpool(
            beatprints_service.match_platform_link, provider, catalog_id, type, platform
        )
    except beatprints_service.PlatformLinkNoMatchError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except beatprints_service.UpstreamError as exc:
        raise UpstreamServiceError(str(exc)) from exc
    return ApiResponse(code=0, data=result, message="success")


@router.get(
    "/platform-links/{platform}/resolve",
    summary="读取目标平台链接当前资料",
    description=(
        "解析用户手动输入或从候选中选择的公开链接。返回值只用于确认二维码目标，"
        "不会替换最初选中的 provider + catalog_id 或海报元数据。"
    ),
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
    except beatprints_service.PlatformLinkNoMatchError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SpotifyNotConfiguredError as exc:
        raise UpstreamServiceError(str(exc), unavailable=True) from exc
    except beatprints_service.UpstreamError as exc:
        raise UpstreamServiceError(str(exc)) from exc
    return ApiResponse(code=0, data=result, message="success")
