"""particle_attempt 表：按任务查全部尝试、按变体查出图尝试、用量汇总。"""

from __future__ import annotations

from sqlalchemy import func, select

from pojo.entity.particle_attempt import ParticleAttempt
from server.mapper.base_mapper import BaseMapper


class ParticleAttemptMapper(BaseMapper[ParticleAttempt]):
    entity = ParticleAttempt

    # 查询任务的全部尝试，按变体、尝试编号排序
    async def select_by_run(self, run_id: int) -> list[ParticleAttempt]:
        rows = await self.session.scalars(
            select(ParticleAttempt)
            .where(ParticleAttempt.run_id == run_id)
            .order_by(ParticleAttempt.variant_id, ParticleAttempt.attempt_no)
        )
        return list(rows)

    # 查询变体最后一次出图（有 PNG）的尝试
    async def select_last_rendered(self, run_id: int, variant_id: str) -> ParticleAttempt | None:
        return await self.session.scalar(
            select(ParticleAttempt)
            .where(
                ParticleAttempt.run_id == run_id,
                ParticleAttempt.variant_id == variant_id,
                ParticleAttempt.png_path.is_not(None),
            )
            .order_by(ParticleAttempt.attempt_no.desc())
            .limit(1)
        )

    # 汇总任务的 token 用量与模型调用次数
    async def sum_usage(self, run_id: int) -> tuple[int, int, int]:
        row = (
            await self.session.execute(
                select(
                    func.coalesce(func.sum(ParticleAttempt.prompt_tokens), 0),
                    func.coalesce(func.sum(ParticleAttempt.completion_tokens), 0),
                    func.count(ParticleAttempt.id),
                ).where(ParticleAttempt.run_id == run_id)
            )
        ).one()
        return int(row[0]), int(row[1]), int(row[2])
