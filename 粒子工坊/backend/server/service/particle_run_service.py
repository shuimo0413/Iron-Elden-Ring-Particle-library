"""生成任务业务：建任务、查询、事件与尝试落库、审核前校验、状态流转、启动时标记中断。

工作流节点不碰数据库；run_runner 把流式输出交给本 service 写库。
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from common.constant.library_constant import PARTICLE_NAME_PATTERN, RUNS_URL_SEGMENT
from common.constant.message_constant import MessageConstant
from common.constant.run_event_type import RunEventType
from common.constant.run_status import ReviewAction, RunStatus
from common.exception.biz_exceptions import (
    ConflictException,
    InvalidParamException,
    NotConfiguredException,
    NotFoundException,
)
from common.properties.app_properties import AppProperties
from common.properties.workflow_properties import WorkflowProperties
from common.result.page_result import PageResult
from pojo.dto.particle_run_dto import RunCreateDTO, RunQueryDTO, RunResumeDTO
from pojo.entity.base_entity import local_now
from pojo.entity.particle_attempt import ParticleAttempt
from pojo.entity.particle_run import ParticleRun
from pojo.entity.particle_run_event import ParticleRunEvent
from pojo.vo.particle_run_vo import AttemptVO, RunDetailVO, RunEventVO, RunVO, UsageVO, VariantVO
from server.calc import compact_art_calc, prompt_calc
from server.client.llm_client import LlmClient
from server.mapper.particle_attempt_mapper import ParticleAttemptMapper
from server.mapper.particle_run_event_mapper import ParticleRunEventMapper
from server.mapper.particle_run_mapper import ParticleRunMapper

# 单次轮询最多返回的事件数
MAX_EVENTS_PER_POLL = 200
STREAM_EVENT_KIND = "event"
STREAM_ATTEMPT_KIND = "attempt"


class ParticleRunService:
    def __init__(
        self,
        session: AsyncSession,
        app_props: AppProperties,
        llm: LlmClient,
        workflow_props: WorkflowProperties,
    ) -> None:
        self.session = session
        self.app_props = app_props
        self.llm = llm
        self.workflow_props = workflow_props
        self.run_mapper = ParticleRunMapper(session)
        self.attempt_mapper = ParticleAttemptMapper(session)
        self.event_mapper = ParticleRunEventMapper(session)

    # —— 建任务 ——

    # 新建任务：校验模型已配置 → 拼首轮提示词 → 写任务记录（状态 running）
    async def create(self, dto: RunCreateDTO) -> ParticleRun:
        if not self.llm.configured:
            raise NotConfiguredException(MessageConstant.LLM_NOT_CONFIGURED)
        options = dto.options.model_dump()
        bundle = prompt_calc.build_prompt(dto.description, options)
        run = ParticleRun(
            thread_id=uuid.uuid4().hex,
            description=dto.description,
            options_json=options,
            prompt_text=prompt_calc.render_messages_text(
                [{"role": "system", "content": bundle.system}, {"role": "user", "content": bundle.user}]
            ),
            prompt_notes_json=bundle.notes,
            status=RunStatus.RUNNING,
        )
        run = await self.run_mapper.insert(run)
        await self.session.commit()
        return run

    # 主图的初始输入
    def graph_input(self, run: ParticleRun) -> dict[str, Any]:
        return {
            "run_id": run.id,
            "description": run.description,
            "options": run.options_json,
            "max_attempts": self.workflow_props.workflow_max_attempts,
            "variants": [],
            "review": None,
            "published_name": None,
            "publish_warnings": [],
        }

    # —— 查询 ——

    # 按 ID 取任务，不存在抛 RUN_NOT_FOUND
    async def get(self, run_id: int) -> ParticleRun:
        run = await self.run_mapper.select_by_id(run_id)
        if run is None:
            raise NotFoundException(MessageConstant.RUN_NOT_FOUND)
        return run

    # 丢弃本会话缓存后重新读取（后台任务用另一个会话改过状态时使用）
    async def reload(self, run_id: int) -> ParticleRun:
        self.session.expire_all()
        return await self.get(run_id)

    # 分页历史
    async def page(self, query: RunQueryDTO) -> PageResult[RunVO]:
        rows, total = await self.run_mapper.select_page(page=query.page, page_size=query.page_size, status=query.status)
        return PageResult(total=total, page=query.page, page_size=query.page_size, items=[to_run_vo(r) for r in rows])

    # 详情：任务信息 + 各变体全部尝试 + 用量 + 当前最大事件序号
    async def detail(self, run_id: int) -> RunDetailVO:
        run = await self.get(run_id)
        attempts = await self.attempt_mapper.select_by_run(run_id)
        variants: dict[str, VariantVO] = {}
        for attempt in attempts:
            variant = variants.setdefault(attempt.variant_id, VariantVO(variant_id=attempt.variant_id))
            variant.attempts.append(self._attempt_vo(attempt))
            if attempt.png_path:
                variant.final_attempt_no = attempt.attempt_no
        prompt_tokens, completion_tokens, calls = await self.attempt_mapper.sum_usage(run_id)
        return RunDetailVO(
            run=to_run_vo(run),
            prompt_text=run.prompt_text,
            prompt_notes=run.prompt_notes_json or [],
            variants=sorted(variants.values(), key=lambda v: v.variant_id),
            usage=UsageVO(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens, model_calls=calls),
            last_seq=await self.event_mapper.select_max_seq(run_id),
        )

    # 轮询增量事件
    async def events(self, run_id: int, after_seq: int) -> list[RunEventVO]:
        await self.get(run_id)
        rows = await self.event_mapper.select_after(run_id, after_seq, MAX_EVENTS_PER_POLL)
        return [
            RunEventVO(
                seq=row.seq,
                type=row.type,
                variant_id=row.variant_id,
                payload=row.payload_json,
                created_at=row.created_at,
            )
            for row in rows
        ]

    # —— 审核 / 取消前校验 ——

    # 审核恢复前校验：状态必须是 reviewing，变体须有出图，手改像素须合法；通过后改回 running
    async def prepare_resume(self, run_id: int, dto: RunResumeDTO) -> tuple[ParticleRun, dict[str, Any]]:
        run = await self.get(run_id)
        if run.status != RunStatus.REVIEWING:
            raise ConflictException(MessageConstant.RUN_NOT_WAITING_REVIEW)
        action = dto.review_action
        if action in (ReviewAction.APPROVE, ReviewAction.REVISE):
            if not dto.variant_id:
                raise InvalidParamException(MessageConstant.RUN_VARIANT_REQUIRED)
            if await self.attempt_mapper.select_last_rendered(run_id, dto.variant_id) is None:
                raise InvalidParamException(MessageConstant.RUN_VARIANT_NOT_FOUND)
        if action == ReviewAction.REVISE and not (dto.feedback or "").strip():
            raise InvalidParamException(MessageConstant.RUN_FEEDBACK_REQUIRED)
        if action == ReviewAction.APPROVE:
            if dto.edited_art is not None:
                problems = compact_art_calc.validate_standard_art(dto.edited_art, size=int(run.options_json["size"]))
                if problems:
                    raise InvalidParamException(f"{MessageConstant.RUN_EDITED_ART_INVALID}：{problems[0]}")
            if dto.publish_name and not PARTICLE_NAME_PATTERN.match(dto.publish_name):
                raise InvalidParamException(MessageConstant.PARTICLE_NAME_INVALID)

        decision = {
            "action": action.value,
            "variant_id": dto.variant_id,
            "feedback": (dto.feedback or "").strip() or None,
            "edited_art": dto.edited_art if action == ReviewAction.APPROVE else None,
            "publish_name": dto.publish_name if action == ReviewAction.APPROVE else None,
        }
        run.status = RunStatus.RUNNING
        if dto.variant_id:
            run.selected_variant_id = dto.variant_id
        await self._append_event(
            run_id,
            RunEventType.REVIEW_SUBMITTED,
            {
                "action": decision["action"],
                "feedback": decision["feedback"],
                "edited": decision["edited_art"] is not None,
                "publish_name": decision["publish_name"],
            },
            dto.variant_id,
        )
        await self.session.commit()
        return run, decision

    # 取消前校验：只有运行中的任务能取消
    async def ensure_running(self, run_id: int) -> ParticleRun:
        run = await self.get(run_id)
        if run.status != RunStatus.RUNNING:
            raise ConflictException(MessageConstant.RUN_NOT_RUNNING)
        return run

    # —— run_runner 回调 ——

    # 落一条工作流流式输出：事件写 particle_run_event，尝试写 particle_attempt
    async def handle_stream_chunk(self, run_id: int, chunk: dict[str, Any]) -> None:
        kind = chunk.get("kind")
        if kind == STREAM_EVENT_KIND:
            await self._append_event(run_id, chunk["type"], chunk.get("payload") or {}, chunk.get("variant_id"))
        elif kind == STREAM_ATTEMPT_KIND:
            await self._insert_attempt(chunk["record"])
        await self.session.commit()

    # 任务进入待审核
    async def mark_reviewing(self, run_id: int, summary: dict[str, Any]) -> None:
        run = await self.get(run_id)
        run.status = RunStatus.REVIEWING
        await self._append_event(run_id, RunEventType.REVIEW_WAITING, summary)
        await self.session.commit()

    # 任务结束：写最终状态、结束时间与对应事件
    async def mark_finished(
        self,
        run_id: int,
        status: RunStatus,
        event_type: RunEventType,
        payload: dict[str, Any] | None = None,
        *,
        error_message: str | None = None,
        published_name: str | None = None,
    ) -> None:
        run = await self.get(run_id)
        run.status = status
        run.finished_at = local_now()
        if error_message:
            run.error_message = error_message
        if published_name:
            run.published_name = published_name
        await self._append_event(run_id, event_type, payload or {})
        await self.session.commit()

    # 启动时：仍为 running 的任务后台已随进程消失，标记为 interrupted；reviewing 不受影响
    async def mark_interrupted_on_startup(self) -> int:
        runs = await self.run_mapper.select_by_status(RunStatus.RUNNING)
        for run in runs:
            run.status = RunStatus.INTERRUPTED
            run.finished_at = local_now()
            run.error_message = "服务重启时任务仍在运行，已中断"
            await self._append_event(run.id, RunEventType.RUN_INTERRUPTED, {"reason": run.error_message})
        await self.session.commit()
        return len(runs)

    # —— 内部 ——

    async def _append_event(
        self, run_id: int, event_type: str, payload: dict[str, Any], variant_id: str | None = None
    ) -> None:
        seq = await self.event_mapper.select_max_seq(run_id) + 1
        await self.event_mapper.insert(
            ParticleRunEvent(run_id=run_id, seq=seq, type=str(event_type), variant_id=variant_id, payload_json=payload)
        )

    async def _insert_attempt(self, record: dict[str, Any]) -> None:
        await self.attempt_mapper.insert(
            ParticleAttempt(
                run_id=record["run_id"],
                variant_id=record["variant_id"],
                attempt_no=record["attempt_no"],
                trigger=record.get("trigger") or "initial",
                raw_response_path=record.get("raw_response_path"),
                compact_path=record.get("compact_path"),
                art_path=record.get("art_path"),
                png_path=record.get("png_path"),
                preview_path=record.get("preview_path"),
                check_report_json=record.get("check_report") or {},
                passed=bool(record.get("passed")),
                error_message=record.get("error_message"),
                prompt_tokens=int(record.get("prompt_tokens") or 0),
                completion_tokens=int(record.get("completion_tokens") or 0),
            )
        )

    def _file_url(self, relative_path: str | None) -> str | None:
        if not relative_path:
            return None
        return f"{self.app_props.api_prefix}{RUNS_URL_SEGMENT}/{relative_path}"

    def _attempt_vo(self, attempt: ParticleAttempt) -> AttemptVO:
        return AttemptVO(
            id=attempt.id,
            variant_id=attempt.variant_id,
            attempt_no=attempt.attempt_no,
            trigger=attempt.trigger,
            passed=attempt.passed,
            error_message=attempt.error_message,
            check_report=attempt.check_report_json or {},
            prompt_tokens=attempt.prompt_tokens,
            completion_tokens=attempt.completion_tokens,
            raw_response_url=self._file_url(attempt.raw_response_path),
            compact_url=self._file_url(attempt.compact_path),
            art_url=self._file_url(attempt.art_path),
            png_url=self._file_url(attempt.png_path),
            preview_url=self._file_url(attempt.preview_path),
            created_at=attempt.created_at,
        )


def to_run_vo(run: ParticleRun) -> RunVO:
    return RunVO(
        id=run.id,
        thread_id=run.thread_id,
        description=run.description,
        options=run.options_json,
        status=run.status,
        selected_variant_id=run.selected_variant_id,
        published_name=run.published_name,
        error_message=run.error_message,
        created_at=run.created_at,
        updated_at=run.updated_at,
        finished_at=run.finished_at,
    )
