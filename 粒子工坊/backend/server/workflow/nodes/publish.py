"""publish：把选中变体（或手改后的像素）写入粒子库，并重建总览图。

入库前再查一次重名（审核期间库里可能新增同名粒子），重名时自动加后缀并记警告。
不自动 git commit，不拷进 mod 工程 assets。
"""

from __future__ import annotations

import asyncio
import logging

from server.calc import compact_art_calc
from server.workflow.deps import WorkflowDeps
from server.workflow.state import RunState

log = logging.getLogger(__name__)


def make_publish(deps: WorkflowDeps):
    async def publish(state: RunState) -> dict:
        review = state["review"] or {}
        variant = next(item for item in state["variants"] if item["variant_id"] == review.get("variant_id"))
        final_attempt = variant["final_attempt"]
        art = review.get("edited_art") or deps.artifacts.read_json(final_attempt["art_path"])

        warnings: list[str] = []
        requested_name = review.get("publish_name") or final_attempt["name"]
        name, rename_warning = compact_art_calc.normalize_particle_name(
            requested_name, frozenset(deps.library.list_names()), fallback_name=final_attempt["name"]
        )
        if rename_warning:
            warnings.append(rename_warning)

        published = await asyncio.to_thread(deps.library.publish, name, art)
        try:
            await asyncio.to_thread(deps.library.rebuild_showcase)
        except Exception as exc:  # noqa: BLE001  总览图失败不影响入库结果
            log.warning("重建总览图失败: %s", exc, exc_info=True)
            warnings.append(f"重建总览图失败：{exc}")
        return {"published_name": published, "publish_warnings": warnings}

    return publish
