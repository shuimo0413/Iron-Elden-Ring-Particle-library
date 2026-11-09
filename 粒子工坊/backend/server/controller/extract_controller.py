"""图片逐像素取色：POST /extract（multipart）。"""

import logging
from pathlib import PurePath

from fastapi import APIRouter, File, Form, UploadFile

from common.properties.extract_properties import get_extract_properties
from common.result.result import Result
from pojo.vo.extract_vo import ExtractVO
from server.config.dependency_config import ExtractServiceDep

log = logging.getLogger(__name__)

router = APIRouter(tags=["extract"])


# 取色：上传图片，返回逐像素 RGBA（标准像素 JSON）、颜色列表与统计
@router.post("/extract", response_model=Result[ExtractVO])
async def extract(
    service: ExtractServiceDep,
    file: UploadFile = File(...),
    name: str | None = Form(default=None, max_length=64),
    min_alpha: int = Form(default=1, ge=0, le=255),
) -> Result[ExtractVO]:
    art_name = (name or "").strip() or PurePath(file.filename or "image").stem
    log.info("图片取色，filename=%s name=%s min_alpha=%s", file.filename, art_name, min_alpha)
    # 多读 1 字节即可判断是否超限，避免把超大文件整个读进内存
    data = await file.read(get_extract_properties().max_upload_bytes + 1)
    return Result.success(await service.extract(data, name=art_name, min_alpha=min_alpha))
