"""后台跑图：每个任务一个 asyncio 任务，消费 graph.astream 的输出并经 service 落库。

- custom 流：节点发出的事件 / 尝试记录 → particle_run_event / particle_attempt
- 流结束后读 checkpoint 快照决定状态：停在 human_review → reviewing；已入库 → published；
  放弃 → rejected；没有任何变体出图 → failed
- 取消：cancel() 取消 asyncio 任务，任务内部把状态写成 cancelled
- 关闭：shutdown() 取消全部任务并写成 interrupted（与启动时的中断标记一致）
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from langgraph.types import Command

from common.constant.run_event_type import RunEventType
from common.constant.run_status import ReviewAction, RunStatus
from common.properties.app_properties import get_app_properties
from common.properties.workflow_properties import get_workflow_properties
from server.config.client_config import get_llm_client
from server.config.database_config import get_database
from server.config.workflow_config import get_graph
from server.service.particle_run_service import ParticleRunService

log = logging.getLogger(__name__)

# 等待被取消任务收尾（写库）的最长时间（秒）
CANCEL_WAIT_SECONDS = 5.0

_tasks: dict[int, asyncio.Task] = {}
# 被 shutdown() 取消的任务 ID：这些任务写 interrupted 而不是 cancelled
_interrupted_by_shutdown: set[int] = set()


def is_running(run_id: int) -> bool:
    task = _tasks.get(run_id)
    return task is not None and not task.done()


def start(run_id: int, thread_id: str, graph_input: dict[str, Any]) -> None:
    """新任务：从头跑主图。"""
    _spawn(run_id, thread_id, graph_input)


def resume(run_id: int, thread_id: str, decision: dict[str, Any]) -> None:
    """审核后：把决定作为 interrupt 的返回值继续跑。"""
    _spawn(run_id, thread_id, Command(resume=decision))


async def cancel(run_id: int) -> bool:
    """取消运行中的任务；没有对应后台任务时返回 False（由调用方直接改状态）。"""
    task = _tasks.get(run_id)
    if task is None or task.done():
        return False
    task.cancel()
    await asyncio.wait([task], timeout=CANCEL_WAIT_SECONDS)
    return True


async def shutdown() -> None:
    pending = []
    for run_id, task in list(_tasks.items()):
        if not task.done():
            _interrupted_by_shutdown.add(run_id)
            task.cancel()
            pending.append(task)
    if pending:
        await asyncio.wait(pending, timeout=CANCEL_WAIT_SECONDS)


def _spawn(run_id: int, thread_id: str, graph_input: Any) -> None:
    if is_running(run_id):
        raise RuntimeError(f"任务 {run_id} 已在运行")
    _tasks[run_id] = asyncio.create_task(_drive(run_id, thread_id, graph_input), name=f"particle-run-{run_id}")


def _service(session) -> ParticleRunService:
    return ParticleRunService(session, get_app_properties(), get_llm_client(), get_workflow_properties())


async def _drive(run_id: int, thread_id: str, graph_input: Any) -> None:
    graph = get_graph()
    config = {"configurable": {"thread_id": thread_id}}
    session_factory = get_database().session_factory
    try:
        async for _namespace, mode, chunk in graph.astream(
            graph_input, config, stream_mode=["custom"], subgraphs=True
        ):
            if mode == "custom" and isinstance(chunk, dict):
                async with session_factory() as session:
                    await _service(session).handle_stream_chunk(run_id, chunk)
        snapshot = await graph.aget_state(config)
        async with session_factory() as session:
            await _finalize(_service(session), run_id, snapshot)
    except asyncio.CancelledError:
        status, event_type, reason = (
            (RunStatus.INTERRUPTED, RunEventType.RUN_INTERRUPTED, "服务关闭时任务仍在运行，已中断")
            if run_id in _interrupted_by_shutdown
            else (RunStatus.CANCELLED, RunEventType.RUN_CANCELLED, "任务已手动取消")
        )
        _interrupted_by_shutdown.discard(run_id)
        async with session_factory() as session:
            await _service(session).mark_finished(run_id, status, event_type, {"reason": reason}, error_message=reason)
    except Exception as exc:  # noqa: BLE001  任何异常都要落成失败状态，前端才能停止轮询
        log.exception("任务 %s 运行失败", run_id)
        reason = f"{type(exc).__name__}: {exc}"
        async with session_factory() as session:
            await _service(session).mark_finished(
                run_id, RunStatus.FAILED, RunEventType.RUN_FAILED, {"reason": reason}, error_message=reason
            )
    finally:
        _tasks.pop(run_id, None)


async def _finalize(service: ParticleRunService, run_id: int, snapshot) -> None:
    if snapshot.interrupts:
        await service.mark_reviewing(run_id, snapshot.interrupts[0].value)
        return
    values = snapshot.values or {}
    published_name = values.get("published_name")
    if published_name:
        await service.mark_finished(
            run_id,
            RunStatus.PUBLISHED,
            RunEventType.PUBLISHED,
            {"name": published_name, "warnings": values.get("publish_warnings") or []},
            published_name=published_name,
        )
        return
    review = values.get("review") or {}
    if review.get("action") == ReviewAction.REJECT:
        await service.mark_finished(run_id, RunStatus.REJECTED, RunEventType.RUN_REJECTED, {"reason": "设计者放弃"})
        return
    errors = [f"{v['variant_id']}：{v.get('error')}" for v in values.get("variants") or [] if v.get("error")]
    reason = "所有变体都失败" + (f"（{'；'.join(errors)}）" if errors else "")
    await service.mark_finished(
        run_id, RunStatus.FAILED, RunEventType.RUN_FAILED, {"reason": reason}, error_message=reason
    )
