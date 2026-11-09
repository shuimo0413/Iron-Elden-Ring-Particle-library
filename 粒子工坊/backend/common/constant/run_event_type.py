"""任务事件类型：写入 particle_run_event 表，供前端轮询时间线。"""

from enum import StrEnum


class RunEventType(StrEnum):
    PROMPT_BUILT = "prompt_built"
    MODEL_CALLED = "model_called"
    PARSE_FAILED = "parse_failed"
    CHECK_FAILED = "check_failed"
    ATTEMPT_READY = "attempt_ready"
    VARIANT_DONE = "variant_done"
    VARIANT_FAILED = "variant_failed"
    REVIEW_WAITING = "review_waiting"
    REVIEW_SUBMITTED = "review_submitted"
    PUBLISHED = "published"
    RUN_REJECTED = "run_rejected"
    RUN_FAILED = "run_failed"
    RUN_CANCELLED = "run_cancelled"
    RUN_INTERRUPTED = "run_interrupted"


# 前端收到这些事件后停止轮询并重新拉详情
TERMINAL_OR_PAUSE_EVENTS: frozenset[str] = frozenset(
    {
        RunEventType.REVIEW_WAITING,
        RunEventType.PUBLISHED,
        RunEventType.RUN_REJECTED,
        RunEventType.RUN_FAILED,
        RunEventType.RUN_CANCELLED,
        RunEventType.RUN_INTERRUPTED,
    }
)
