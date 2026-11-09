"""生成任务状态。"""

from enum import StrEnum


class RunStatus(StrEnum):
    # 后台图正在执行
    RUNNING = "running"
    # 停在 human_review，等待批准 / 打回 / 放弃
    REVIEWING = "reviewing"
    # 已写入粒子库
    PUBLISHED = "published"
    # 设计者放弃
    REJECTED = "rejected"
    # 所有变体都失败，或运行异常
    FAILED = "failed"
    # 运行中被手动取消
    CANCELLED = "cancelled"
    # 服务重启时仍在运行，后台任务随进程消失
    INTERRUPTED = "interrupted"


# 已结束、不会再变化的状态
FINISHED_STATUSES: frozenset[str] = frozenset(
    {RunStatus.PUBLISHED, RunStatus.REJECTED, RunStatus.FAILED, RunStatus.CANCELLED, RunStatus.INTERRUPTED}
)


class AttemptTrigger(StrEnum):
    INITIAL = "initial"
    PARSE_RETRY = "parse_retry"
    CHECK_RETRY = "check_retry"
    HUMAN_REVISE = "human_revise"


class ReviewAction(StrEnum):
    APPROVE = "approve"
    REVISE = "revise"
    REJECT = "reject"
