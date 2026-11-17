from typing import Annotated

from fastapi import APIRouter, Query, Response
from pydantic import BaseModel

from beatprints_api.config import settings
from beatprints_api.models import ApiResponse, HealthData
from beatprints_api.services.release_notes import get_release_notes
from beatprints_api.integrations.catalog import catalog_adapters
from beatprints_api.integrations.destinations.registry import destination_adapters
from beatprints_api.integrations.lyrics.registry import lyrics_sources, default_lyrics_source_key

router = APIRouter(tags=["System"])


@router.get(
    "/health",
    summary="检查服务状态",
    description="不需要鉴权。返回 ok 表示 API 进程已经正常启动。",
    response_model=ApiResponse[HealthData],
)
def health() -> ApiResponse[HealthData]:
    return ApiResponse(
        code=0,
        data=HealthData(
            status="ok",
            version=settings.build_version,
            git_sha=settings.build_git_sha,
        ),
        message="success",
    )


class IntegrationCapability(BaseModel):
    key: str
    label: str
    available: bool = True
    reason: str | None = None
    default: bool = False
    fixed_code: bool = False
    reuses_source_links: list[str] = []


class CapabilitiesData(BaseModel):
    wechat_qr: bool
    catalogs: list[IntegrationCapability]
    lyrics: list[IntegrationCapability]
    destinations: list[IntegrationCapability]


@router.get("/v1/capabilities", response_model=ApiResponse[CapabilitiesData], summary="查询可用功能")
def capabilities(response: Response) -> ApiResponse[CapabilitiesData]:
    response.headers["Cache-Control"] = "no-store"
    catalogs = catalog_adapters()
    destinations = destination_adapters()
    return ApiResponse(code=0, data=CapabilitiesData(
        wechat_qr=bool(settings.wechat_qr_base_url),
        catalogs=[IntegrationCapability(key=a.key, label=a.label, available=a.configured(),
                    reason=None if a.configured() else "not_configured") for a in catalogs],
        lyrics=[IntegrationCapability(key=a.key, label=a.label, default=a.key == default_lyrics_source_key())
                for a in lyrics_sources()],
        destinations=[IntegrationCapability(key=a.key, label=a.label, available=a.configured(),
                      reason=None if a.configured() else "not_configured", fixed_code=a.fixed_code,
                      reuses_source_links=[c.key for c in catalogs if a.reuses_source_link(c.key)])
                      for a in destinations],
    ), message="success")


class ReleaseNotesData(BaseModel):
    body: str


@router.get("/v1/release-notes", response_model=ApiResponse[ReleaseNotesData], summary="获取版本更新内容")
def release_notes(version: Annotated[str, Query(pattern=r"^\d{1,6}\.\d{1,6}\.\d{1,6}$")]) -> ApiResponse[ReleaseNotesData]:
    return ApiResponse(code=0, data=ReleaseNotesData(body=get_release_notes(version)), message="success")
