"""particle_run_event 表：取最大序号、增量查询事件。"""

from __future__ import annotations

from sqlalchemy import func, select

from pojo.entity.particle_run_event import ParticleRunEvent
from server.mapper.base_mapper import BaseMapper


class ParticleRunEventMapper(BaseMapper[ParticleRunEvent]):
    entity = ParticleRunEvent

    # 任务当前最大事件序号；没有事件时为 0
    async def select_max_seq(self, run_id: int) -> int:
        value = await self.session.scalar(
            select(func.max(ParticleRunEvent.seq)).where(ParticleRunEvent.run_id == run_id)
        )
        return int(value or 0)

    # 查询 seq 大于 after_seq 的事件，按 seq 升序，最多 limit 条
    async def select_after(self, run_id: int, after_seq: int, limit: int) -> list[ParticleRunEvent]:
        rows = await self.session.scalars(
            select(ParticleRunEvent)
            .where(ParticleRunEvent.run_id == run_id, ParticleRunEvent.seq > after_seq)
            .order_by(ParticleRunEvent.seq)
            .limit(limit)
        )
        return list(rows)
