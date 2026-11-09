"""按钮清单与提示词预览：GET /options、POST /prompt/preview。"""

import logging

from fastapi import APIRouter

from common.result.result import Result
from common.utils.log_util import to_log
from pojo.dto.prompt_dto import PromptPreviewDTO
from pojo.vo.option_vo import OptionsVO
from pojo.vo.prompt_vo import PromptVO
from server.config.dependency_config import OptionServiceDep

log = logging.getLogger(__name__)

router = APIRouter(tags=["options"])


# 按钮清单：尺寸参数、各组选项、色调锚点、推荐联动
@router.get("/options", response_model=Result[OptionsVO])
async def options(service: OptionServiceDep) -> Result[OptionsVO]:
    log.info("查询按钮清单")
    return Result.success(service.options())


# 提示词预览：与新建任务同结构，不调模型
@router.post("/prompt/preview", response_model=Result[PromptVO])
async def preview(dto: PromptPreviewDTO, service: OptionServiceDep) -> Result[PromptVO]:
    log.info("预览提示词，%s", to_log(dto))
    return Result.success(service.preview(dto))
