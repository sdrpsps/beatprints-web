from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.concurrency import run_in_threadpool

from beatprints_api.api.dependencies import require_api_key
from beatprints_api.exceptions import (
    IntegrationNotConfiguredError,
    UnsupportedCatalogSourceError,
    UnsupportedDestinationError,
    UpstreamServiceError,
)
from beatprints_api.models import (
    ApiResponse,
    CatalogProvider,
    LyricsPreviewData,
    SearchProvider,
    SearchResult,
    PlatformLinkMatchData,
    PlatformMatchOptionsData,
    ThemesData,
)
from beatprints_api.services import beatprints as beatprints_service

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


@router.get(
    "/platform-links/{platform}/options",
    summary="匹配目标平台并返回候选",
    response_model=ApiResponse[PlatformMatchOptionsData],
    response_model_exclude_none=True,
    responses=ERROR_RESPONSES,
)
async def platform_match_options(
    platform: str,
    provider: Annotated[CatalogProvider, Query()],
    catalog_id: Annotated[str, Query(min_length=1)],
    type: Annotated[Literal["track", "album"], Query()],
    limit: Annotated[int, Query(ge=1, le=10)] = 8,
) -> ApiResponse[PlatformMatchOptionsData]:
    try:
        result = await run_in_threadpool(
            beatprints_service.platform_match_options,
            provider, catalog_id, type, platform, limit,
        )
    except IntegrationNotConfiguredError as exc:
        raise UpstreamServiceError(str(exc), unavailable=True) from exc
    except UnsupportedCatalogSourceError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except UnsupportedDestinationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except beatprints_service.UpstreamError as exc:
        raise UpstreamServiceError(str(exc)) from exc
    return ApiResponse(code=0, data=result, message="success")

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
        "provider 使用已启用的目录 integration key；provider=all 会合并"
        "当前已配置的来源。"
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
            description="搜索数据源：已启用的目录 integration key 或 all。",
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
    except IntegrationNotConfiguredError as exc:
        raise UpstreamServiceError(str(exc), unavailable=True) from exc
    except UnsupportedCatalogSourceError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
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
        "返回规范化非空行供前端选择最多四行。纯音乐返回 instrumental=true 和空行列表。"
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
    except IntegrationNotConfiguredError as exc:
        raise UpstreamServiceError(str(exc), unavailable=True) from exc
    except UnsupportedCatalogSourceError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except beatprints_service.UpstreamError as exc:
        raise UpstreamServiceError(str(exc)) from exc
    except Exception as exc:
        raise UpstreamServiceError("Lyrics request failed") from exc

    return ApiResponse(code=0, data=result, message="success")


@router.get(
    "/platform-links/{platform}/resolve",
    summary="读取目标平台链接当前资料",
    description=(
        "解析用户手动输入或从候选中选择的公开链接。返回值只用于确认二维码目标，"
        "不会替换最初选中的 provider + catalog_id 或海报元数据。"
    ),
    response_model=ApiResponse[PlatformLinkMatchData],
    response_model_exclude_none=True,
)
async def resolve_platform_url(
    platform: str,
    url: Annotated[str, Query(min_length=1, max_length=2000)],
) -> ApiResponse[PlatformLinkMatchData]:
    try:
        result = await run_in_threadpool(
            beatprints_service.resolve_platform_url, platform, url
        )
    except beatprints_service.PlatformLinkNoMatchError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except UnsupportedDestinationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except IntegrationNotConfiguredError as exc:
        raise UpstreamServiceError(str(exc), unavailable=True) from exc
    except beatprints_service.UpstreamError as exc:
        raise UpstreamServiceError(str(exc)) from exc
    return ApiResponse(code=0, data=result, message="success")
