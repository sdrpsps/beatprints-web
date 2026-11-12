from fastapi import APIRouter
from pydantic import BaseModel

from beatprints_api.config import settings
from beatprints_api.models import ApiResponse, HealthData

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


class CapabilitiesData(BaseModel):
    wechat_qr: bool


@router.get("/capabilities", response_model=ApiResponse[CapabilitiesData], summary="查询可用功能")
def capabilities() -> ApiResponse[CapabilitiesData]:
    return ApiResponse(code=0, data=CapabilitiesData(wechat_qr=bool(settings.wechat_qr_base_url)), message="success")
