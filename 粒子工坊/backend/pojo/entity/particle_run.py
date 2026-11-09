"""particle_run：一次生成任务。"""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from pojo.entity.base_entity import BaseEntity


class ParticleRun(BaseEntity):
    __tablename__ = "particle_run"

    # LangGraph 线程 ID（uuid），checkpoint 按它存取
    thread_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    description: Mapped[str] = mapped_column(Text)
    # 按钮选项：size / category / palette / outline / symmetry / variants
    options_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    # 拼好的完整提示词（首轮 system + user）
    prompt_text: Mapped[str] = mapped_column(Text, default="")
    prompt_notes_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(16), index=True)
    selected_variant_id: Mapped[str | None] = mapped_column(String(16), nullable=True)
    published_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
