from typing import Generic, TypeVar

from pydantic import BaseModel, Field

DataT = TypeVar("DataT")


class ApiResponse(BaseModel, Generic[DataT]):
    """所有 JSON API 共用的响应结构。"""

    code: int = Field(description="业务状态码；0 表示成功，非 0 表示失败。")
    data: DataT | None = Field(default=None, description="响应数据；失败时通常为空。")
    message: str = Field(description="面向调用方的结果说明。")


class HealthData(BaseModel):
    status: str


class ThemesData(BaseModel):
    themes: list[str]
