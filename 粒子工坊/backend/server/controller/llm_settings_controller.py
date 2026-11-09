"""模型设置：GET /settings/llm、PUT /settings/llm（前端填 API Key）。"""

import logging

from fastapi import APIRouter

from common.constant.message_constant import MessageConstant
from common.result.result import Result
from common.utils.log_util import to_log
from pojo.dto.llm_settings_dto import LlmSettingsDTO
from pojo.vo.llm_settings_vo import LlmSettingsVO
from server.config.dependency_config import LlmSettingsServiceDep

log = logging.getLogger(__name__)

router = APIRouter(tags=["settings"])


# 当前模型设置：Key 只返回脱敏值
@router.get("/settings/llm", response_model=Result[LlmSettingsVO])
async def get_llm_settings(service: LlmSettingsServiceDep) -> Result[LlmSettingsVO]:
    return Result.success(service.get())


# 保存模型设置：立即生效，不用重启
@router.put("/settings/llm", response_model=Result[LlmSettingsVO])
async def update_llm_settings(dto: LlmSettingsDTO, service: LlmSettingsServiceDep) -> Result[LlmSettingsVO]:
    log.info("保存模型设置，%s", to_log(dto))
    return Result.success(await service.update(dto), message=MessageConstant.LLM_SETTINGS_SAVED)
