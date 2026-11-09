"""particle_run_event：给前端轮询的事件流，(run_id, seq) 唯一递增。"""

from typing import Any

from sqlalchemy import JSON, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from pojo.entity.base_entity import BaseEntity


class ParticleRunEvent(BaseEntity):
    __tablename__ = "particle_run_event"
    __table_args__ = (UniqueConstraint("run_id", "seq", name="uq_particle_run_event_run_seq"),)

    run_id: Mapped[int] = mapped_column(Integer, index=True)
    seq: Mapped[int] = mapped_column(Integer)
    type: Mapped[str] = mapped_column(String(32))
    variant_id: Mapped[str | None] = mapped_column(String(16), nullable=True)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
