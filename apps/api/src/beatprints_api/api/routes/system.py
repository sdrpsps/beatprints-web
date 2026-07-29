from fastapi import APIRouter

from beatprints_api.models import ApiResponse, HealthData

router = APIRouter(tags=["System"])


@router.get(
    "/health",
    summary="检查服务状态",
    description="不需要鉴权。返回 ok 表示 API 进程已经正常启动。",
    response_model=ApiResponse[HealthData],
)
def health() -> ApiResponse[HealthData]:
    return ApiResponse(code=0, data=HealthData(status="ok"), message="success")
