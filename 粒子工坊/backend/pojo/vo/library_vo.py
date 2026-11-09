"""粒子库出参：列表条目、单个粒子详情、总览图重建结果。"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ParticleItemVO(BaseModel):
    name: str
    # 文件名第一个下划线前的前缀，如 sigil_frost → sigil
    series: str
    width: int
    height: int
    png_url: str
    has_json: bool
    modified_at: float


class ParticleDetailVO(ParticleItemVO):
    # 标准像素 JSON：优先 tool/origin_json/<name>.json，没有则从 PNG 现取
    art: dict[str, Any]


class ShowcaseVO(BaseModel):
    url: str
    particle_count: int
