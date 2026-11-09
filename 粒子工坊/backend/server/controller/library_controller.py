"""粒子库接口：列表、单个粒子、重建总览图、总览图文件。"""

import logging

from fastapi import APIRouter, Query
from fastapi.responses import FileResponse

from common.constant.library_constant import SHOWCASE_URL_PATH
from common.constant.message_constant import MessageConstant
from common.exception.biz_exceptions import NotFoundException
from common.result.result import Result
from pojo.vo.library_vo import ParticleDetailVO, ParticleItemVO, ShowcaseVO
from server.config.dependency_config import LibraryServiceDep

log = logging.getLogger(__name__)

router = APIRouter(tags=["library"])


# 粒子库列表：q 名称关键字，series 文件名前缀
@router.get("/library", response_model=Result[list[ParticleItemVO]])
async def list_particles(
    service: LibraryServiceDep,
    q: str | None = Query(default=None, max_length=64),
    series: str | None = Query(default=None, max_length=64),
) -> Result[list[ParticleItemVO]]:
    log.info("查询粒子库，q=%s series=%s", q, series)
    return Result.success(await service.list(q, series or None))


# 手动重建总览图
@router.post("/library/showcase", response_model=Result[ShowcaseVO])
async def rebuild_showcase(service: LibraryServiceDep) -> Result[ShowcaseVO]:
    log.info("重建粒子库总览图")
    return Result.success(await service.rebuild_showcase(), message=MessageConstant.SHOWCASE_REBUILT)


# 单个粒子：PNG 地址、尺寸、标准 JSON
@router.get("/library/{name}", response_model=Result[ParticleDetailVO])
async def particle_detail(name: str, service: LibraryServiceDep) -> Result[ParticleDetailVO]:
    log.info("查询粒子详情，name=%s", name)
    return Result.success(await service.detail(name))


# 总览图文件（不包 Result，直接返回图片）
@router.get(SHOWCASE_URL_PATH, include_in_schema=False)
async def showcase_file(service: LibraryServiceDep) -> FileResponse:
    path = service.showcase_path()
    if not path.is_file():
        raise NotFoundException(MessageConstant.PARTICLE_NOT_FOUND)
    return FileResponse(path, media_type="image/png", headers={"Cache-Control": "no-cache"})
