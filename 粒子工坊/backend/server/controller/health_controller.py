"""健康检查接口：GET /health，探活用，不访问数据库。"""

from fastapi import APIRouter

from common.properties.app_properties import get_app_properties
from common.result.result import Result

router = APIRouter(tags=["health"])


# 健康检查：返回应用状态、名称与运行环境
@router.get("/health", response_model=Result[dict])
async def health() -> Result[dict]:
    props = get_app_properties()
    return Result.success({"status": "ok", "app": props.app_name, "env": props.app_env})
