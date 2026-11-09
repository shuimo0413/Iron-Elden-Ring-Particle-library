"""particle_attempt：一次模型调用及其产物。

产物路径都是相对 data/runs/ 的 posix 路径，对外地址由 service 拼成 /files/runs/...。
"""

from typing import Any

from sqlalchemy import JSON, Boolean, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from pojo.entity.base_entity import BaseEntity


class ParticleAttempt(BaseEntity):
    __tablename__ = "particle_attempt"
    __table_args__ = (Index("ix_particle_attempt_run_variant", "run_id", "variant_id", "attempt_no"),)

    run_id: Mapped[int] = mapped_column(Integer, index=True)
    variant_id: Mapped[str] = mapped_column(String(16))
    attempt_no: Mapped[int] = mapped_column(Integer)
    # initial / parse_retry / check_retry / human_revise
    trigger: Mapped[str] = mapped_column(String(16))
    raw_response_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    compact_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    art_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    png_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    preview_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # {warnings: [...], items: [...规则检查...], problems: [...]}
    check_report_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    passed: Mapped[bool] = mapped_column(Boolean, default=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
