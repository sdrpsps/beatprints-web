from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.concurrency import run_in_threadpool

from beatprints_api.api.dependencies import require_api_key
from beatprints_api.integrations.region import use_region
from beatprints_api.exceptions import (
    IntegrationNotConfiguredError,
    LyricsNotFoundError,
    PlatformLinkNoMatchError,
    UnsupportedCatalogSourceError,
    UnsupportedDestinationError,
    UnsupportedLyricsSourceError,
    UpstreamError,
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
from beatprints_api.services import catalog as catalog_service
from beatprints_api.services import matching as matching_service

router = APIRouter(
    prefix="/v1",
    tags=["Catalog"],
    dependencies=[Depends(require_api_key)],
)

ERROR_RESPONSES = {
    401: {"model": ApiResponse[object], "description": "API Key 缺失或错误。"},
    404: {"model": ApiResponse[object], "description": "请求的来源或匹配结果不存在。"},
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
    description=(
        "以所选来源的 provider、catalog_id 和来源地区读取歌曲或专辑。"
        "若目标地区无法直接解析同平台的来源 ID，继续在目标地区搜索并返回"
        "经过保守匹配的结果与排序候选；不会自动确认低置信度候选。"
        "Apple Music 歌曲会在可用时优先使用 ISRC 查询对应录音。"
        "标题语言不同但年份和曲目数一致的专辑可作为人工候选，不会自动确认。"
        "目标平台发生真正的服务错误时返回 502。"
    ),
    response_model=ApiResponse[PlatformMatchOptionsData],
    response_model_exclude_none=True,
    responses=ERROR_RESPONSES,
)
async def platform_match_options(
    platform: str,
    provider: Annotated[CatalogProvider, Query(examples=["apple_music"])],
    catalog_id: Annotated[str, Query(min_length=1, examples=["1790520817"])],
    type: Annotated[Literal["track", "album"], Query(examples=["track"])],
    limit: Annotated[int, Query(ge=1, le=10)] = 8,
    source_region: Annotated[
        str | None,
        Query(
            pattern=r"^[A-Z]{2}$",
            examples=["US"],
            description="来源目录地区，须与所选搜索结果使用的地区一致；省略时使用 US。",
        ),
    ] = None,
    destination_region: Annotated[
        str | None,
        Query(
            pattern=r"^[A-Z]{2}$",
            examples=["JP"],
            description="目标平台检索及来源直链解析使用的地区；独立于来源地区，省略时使用 US。",
        ),
    ] = None,
) -> ApiResponse[PlatformMatchOptionsData]:
    try:
        result = await run_in_threadpool(
            matching_service.platform_match_options,
            provider,
            catalog_id,
            type,
            platform,
            limit,
            **(
                {
                    "source_region": source_region,
                    "destination_region": destination_region,
                }
                if source_region or destination_region
                else {}
            ),
        )
    except IntegrationNotConfiguredError as exc:
        raise UpstreamServiceError(str(exc), unavailable=True) from exc
    except UnsupportedCatalogSourceError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except UnsupportedDestinationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except UpstreamError as exc:
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
        "当前已配置的来源。Apple Music 使用所选地区的网页目录进行搜索，"
        "不需要用户登录 Apple Music 账号。"
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
            examples=["Summer Breeze Piper", "周杰伦 晴天"],
        ),
    ],
    provider: Annotated[
        SearchProvider,
        Query(
            description="搜索数据源：已启用的目录 integration key 或 all。",
            examples=["all"],
        ),
    ],
    type: Annotated[
        Literal["track", "album"],
        Query(description="搜索类型：track 表示歌曲，album 表示专辑。"),
    ] = "track",
    region: Annotated[
        str | None,
        Query(
            pattern=r"^[A-Z]{2}$",
            examples=["JP"],
            description="目录地区的两位大写代码；省略时使用 US。支持地区的目录由 /v1/capabilities 的 regions 列出；all 对支持地区的来源使用同一地区。",
        ),
    ] = None,
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
        with use_region(region):
            results = await run_in_threadpool(
                catalog_service.search_catalog,
                query,
                type,
                limit,
                provider,
            )
    except IntegrationNotConfiguredError as exc:
        raise UpstreamServiceError(str(exc), unavailable=True) from exc
    except UnsupportedCatalogSourceError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except UpstreamError as exc:
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
        "按搜索结果中未改变的 provider + id 获取所选歌词来源的歌词，"
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
    region: Annotated[
        str | None,
        Query(
            pattern=r"^[A-Z]{2}$",
            examples=["JP"],
            description="读取所选歌曲元数据的来源地区，应与搜索时一致；省略时使用 US。歌词来源通过 source 单独选择。",
        ),
    ] = None,
    source: Annotated[
        str | None,
        Query(
            min_length=1,
            description="歌词来源 key，必须是后端当前启用的歌词来源。",
        ),
    ] = None,
) -> ApiResponse[LyricsPreviewData]:
    try:
        with use_region(region):
            result = await run_in_threadpool(
                matching_service.preview_lyrics,
                provider,
                catalog_id,
                source,
            )
    except IntegrationNotConfiguredError as exc:
        raise UpstreamServiceError(str(exc), unavailable=True) from exc
    except UnsupportedCatalogSourceError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except UnsupportedLyricsSourceError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except LyricsNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except UpstreamError as exc:
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
    region: Annotated[
        str | None,
        Query(
            pattern=r"^[A-Z]{2}$",
            examples=["US"],
            description="目标平台读取链接当前资料的地区；与来源地区独立，省略时使用 US。",
        ),
    ] = None,
) -> ApiResponse[PlatformLinkMatchData]:
    try:
        with use_region(region):
            result = await run_in_threadpool(
                matching_service.resolve_platform_url, platform, url
            )
    except PlatformLinkNoMatchError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except UnsupportedDestinationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except IntegrationNotConfiguredError as exc:
        raise UpstreamServiceError(str(exc), unavailable=True) from exc
    except UpstreamError as exc:
        raise UpstreamServiceError(str(exc)) from exc
    return ApiResponse(code=0, data=result, message="success")
