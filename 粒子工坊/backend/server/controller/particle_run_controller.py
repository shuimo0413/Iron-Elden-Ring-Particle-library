"""生成任务接口：新建、分页历史、详情、轮询事件、审核恢复、取消。"""

import logging

from fastapi import APIRouter, Query

from common.constant.message_constant import MessageConstant
from common.constant.run_event_type import RunEventType
from common.constant.run_status import RunStatus
from common.result.page_result import PageResult
from common.result.result import Result
from common.utils.log_util import to_log
from pojo.dto.particle_run_dto import RunCreateDTO, RunQueryDTO, RunResumeDTO
from pojo.vo.particle_run_vo import RunDetailVO, RunEventVO, RunVO
from server.config.dependency_config import ParticleRunServiceDep
from server.service.particle_run_service import to_run_vo
from server.task import run_runner

log = logging.getLogger(__name__)

router = APIRouter(prefix="/particle-runs", tags=["particle-runs"])


# 新建任务：写任务记录后交给后台执行，立即返回任务 ID
@router.post("", response_model=Result[RunVO])
async def create_run(dto: RunCreateDTO, service: ParticleRunServiceDep) -> Result[RunVO]:
    log.info("新建生成任务，%s", to_log(dto))
    run = await service.create(dto)
    run_runner.start(run.id, run.thread_id, service.graph_input(run))
    return Result.success(to_run_vo(run))


# 分页历史：page、page_size、status
@router.get("", response_model=Result[PageResult[RunVO]])
async def page_runs(
    service: ParticleRunServiceDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: str | None = Query(default=None),
) -> Result[PageResult[RunVO]]:
    query = RunQueryDTO(page=page, page_size=page_size, status=status or None)
    log.info("分页查询生成任务，%s", to_log(query))
    return Result.success(await service.page(query))


# 详情：任务信息 + 各变体的全部尝试 + 用量
@router.get("/{run_id}", response_model=Result[RunDetailVO])
async def run_detail(run_id: int, service: ParticleRunServiceDep) -> Result[RunDetailVO]:
    log.info("查询生成任务详情，run_id=%s", run_id)
    return Result.success(await service.detail(run_id))


# 轮询事件：返回 seq 大于 after_seq 的事件（最多 200 条）；每秒一次，不打业务日志
@router.get("/{run_id}/events", response_model=Result[list[RunEventVO]])
async def run_events(
    run_id: int, service: ParticleRunServiceDep, after_seq: int = Query(default=0, ge=0)
) -> Result[list[RunEventVO]]:
    return Result.success(await service.events(run_id, after_seq))


# 审核：批准（可带手改像素 / 入库名）/ 打回附意见 / 放弃
@router.post("/{run_id}/resume", response_model=Result[RunVO])
async def resume_run(run_id: int, dto: RunResumeDTO, service: ParticleRunServiceDep) -> Result[RunVO]:
    log.info("审核生成任务，run_id=%s，%s", run_id, to_log(dto))
    run, decision = await service.prepare_resume(run_id, dto)
    run_runner.resume(run.id, run.thread_id, decision)
    return Result.success(to_run_vo(run))


# 取消运行中的任务
@router.post("/{run_id}/cancel", response_model=Result[RunVO])
async def cancel_run(run_id: int, service: ParticleRunServiceDep) -> Result[RunVO]:
    log.info("取消生成任务，run_id=%s", run_id)
    await service.ensure_running(run_id)
    if not await run_runner.cancel(run_id):
        await service.mark_finished(
            run_id,
            RunStatus.CANCELLED,
            RunEventType.RUN_CANCELLED,
            {"reason": MessageConstant.RUN_CANCELLED},
            error_message=MessageConstant.RUN_CANCELLED,
        )
    return Result.success(to_run_vo(await service.reload(run_id)), message=MessageConstant.RUN_CANCELLED)
