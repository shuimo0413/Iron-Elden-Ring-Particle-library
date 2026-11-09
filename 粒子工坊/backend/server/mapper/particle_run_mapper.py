"""particle_run 表：分页查询、按状态批量查询。"""

from __future__ import annotations

from sqlalchemy import func, select

from pojo.entity.particle_run import ParticleRun
from server.mapper.base_mapper import BaseMapper


class ParticleRunMapper(BaseMapper[ParticleRun]):
    entity = ParticleRun

    # 分页查询任务，按创建时间倒序；status 为空则不过滤
    async def select_page(self, *, page: int, page_size: int, status: str | None) -> tuple[list[ParticleRun], int]:
        conditions = [ParticleRun.status == status] if status else []
        total = await self.session.scalar(select(func.count()).select_from(ParticleRun).where(*conditions))
        rows = await self.session.scalars(
            select(ParticleRun)
            .where(*conditions)
            .order_by(ParticleRun.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(rows), int(total or 0)

    # 查询处于某状态的全部任务
    async def select_by_status(self, status: str) -> list[ParticleRun]:
        rows = await self.session.scalars(select(ParticleRun).where(ParticleRun.status == status))
        return list(rows)
