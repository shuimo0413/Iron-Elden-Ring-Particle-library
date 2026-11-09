"""功能一端到端：经 HTTP 接口跑完整工作流（模型换成脚本化的假客户端），写临时粒子库。

覆盖：新建 → 解析失败重试 → 两个变体出图 → 待审核 → 重启服务后打回 → 再审核 → 手改像素批准入库；
以及放弃、取消、所有变体失败、各种审核前校验。
"""

from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager

import httpx
import pytest

import server.config.workflow_config as workflow_config
from server.client.llm_client import LlmReply
from server.main import app
from tests.art_factory import compact_square, compact_text
from tests.support_paths import TEST_LIBRARY_DIR

POLL_INTERVAL_SECONDS = 0.05
POLL_TIMEOUT_SECONDS = 20
STOP_EVENTS = {"review_waiting", "published", "run_rejected", "run_failed", "run_cancelled", "run_interrupted"}


class ScriptedLlm:
    """按对话内容决定返回：v1 首轮故意给 20 行（解析失败）；打回意见里含「失败」时一直返回坏 JSON。"""

    configured = True

    def __init__(self, delay_seconds: float = 0.0) -> None:
        self.calls: list[list[dict]] = []
        self.delay_seconds = delay_seconds

    async def chat_json(self, messages, *, max_tokens):
        self.calls.append(messages)
        if self.delay_seconds:
            await asyncio.sleep(self.delay_seconds)
        user_text = messages[1]["content"]
        last_text = messages[-1]["content"]
        if "全部失败" in user_text:
            return LlmReply("{broken", "stop", 10, 5)
        is_first_call = len(messages) == 2
        if is_first_call and "偏简洁" in user_text:
            bad = compact_square(name="frost_shard")
            bad["rows"] = bad["rows"][:20]
            return LlmReply(json.dumps(bad), "stop", 100, 50)
        if "设计者意见" in last_text:
            return LlmReply(compact_text(name="frost_shard", start=10, end=22), "stop", 120, 60)
        return LlmReply(compact_text(name="frost_shard"), "stop", 100, 50)


@asynccontextmanager
async def running_app(llm: ScriptedLlm):
    """启动 lifespan（建表、初始化工作流）并把模型换成假客户端。"""
    async with app.router.lifespan_context(app):
        workflow_config._graph = None
        await workflow_config.close_workflow()
        original = workflow_config.get_llm_client
        workflow_config.get_llm_client = lambda: llm
        try:
            await workflow_config.init_workflow()
        finally:
            workflow_config.get_llm_client = original
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test/api/v1") as client:
            yield client


async def _ok(response: httpx.Response):
    body = response.json()
    assert body["code"] == 0, body["message"]
    return body["data"]


async def _wait_for_stop(client: httpx.AsyncClient, run_id: int, after_seq: int = 0) -> tuple[list[dict], int]:
    events: list[dict] = []
    deadline = asyncio.get_running_loop().time() + POLL_TIMEOUT_SECONDS
    while asyncio.get_running_loop().time() < deadline:
        batch = await _ok(await client.get(f"/particle-runs/{run_id}/events", params={"after_seq": after_seq}))
        events.extend(batch)
        if batch:
            after_seq = batch[-1]["seq"]
        if any(event["type"] in STOP_EVENTS for event in batch):
            return events, after_seq
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
    raise AssertionError(f"任务 {run_id} 超时，已收到事件 {[e['type'] for e in events]}")


async def _create(client, description="一枚冰霜碎片", **options) -> int:
    payload = {"description": description, "options": {"size": 32, "variants": 2, **options}}
    return (await _ok(await client.post("/particle-runs", json=payload)))["id"]


async def test_full_flow_with_restart_revise_and_edited_approve():
    llm = ScriptedLlm()
    async with running_app(llm) as client:
        run_id = await _create(client)
        events, last_seq = await _wait_for_stop(client, run_id)
        types = [event["type"] for event in events]
        assert types[0] == "prompt_built"
        assert "parse_failed" in types and types[-1] == "review_waiting"
        assert types.count("variant_done") == 2

        detail = await _ok(await client.get(f"/particle-runs/{run_id}"))
        assert detail["run"]["status"] == "reviewing"
        variants = {variant["variant_id"]: variant for variant in detail["variants"]}
        assert [a["trigger"] for a in variants["v1"]["attempts"]] == ["initial", "parse_retry"]
        assert variants["v1"]["final_attempt_no"] == 2
        assert detail["usage"]["model_calls"] == 3
        preview_url = variants["v2"]["attempts"][0]["preview_url"]
        preview = await client.get(preview_url.removeprefix("/api/v1"))
        assert preview.status_code == 200 and preview.headers["content-type"] == "image/png"

    # 重启服务：待审核任务靠 checkpoint 继续
    async with running_app(llm) as client:
        detail = await _ok(await client.get(f"/particle-runs/{run_id}"))
        assert detail["run"]["status"] == "reviewing"
        await _ok(
            await client.post(
                f"/particle-runs/{run_id}/resume",
                json={"action": "revise", "variant_id": "v2", "feedback": "整体再大一圈"},
            )
        )
        events, last_seq = await _wait_for_stop(client, run_id, last_seq)
        assert events[-1]["type"] == "review_waiting"
        revise_call = llm.calls[-1]
        assert "设计者意见（优先）：整体再大一圈" in revise_call[-1]["content"]
        detail = await _ok(await client.get(f"/particle-runs/{run_id}"))
        v2 = next(variant for variant in detail["variants"] if variant["variant_id"] == "v2")
        assert v2["attempts"][-1]["trigger"] == "human_revise" and v2["final_attempt_no"] == 2

        edited_art = {
            "name": "frost_shard",
            "width": 32,
            "height": 32,
            "pixels": [{"x": x, "y": 16, "rgba": [255, 255, 255, 255]} for x in range(8, 24)],
        }
        await _ok(
            await client.post(
                f"/particle-runs/{run_id}/resume",
                json={"action": "approve", "variant_id": "v2", "edited_art": edited_art, "publish_name": "frost_edit"},
            )
        )
        events, _ = await _wait_for_stop(client, run_id, last_seq)
        assert events[-1]["type"] == "published"
        assert events[-1]["payload"]["name"] == "frost_edit"
        detail = await _ok(await client.get(f"/particle-runs/{run_id}"))
        assert detail["run"]["status"] == "published" and detail["run"]["published_name"] == "frost_edit"

        stored = json.loads((TEST_LIBRARY_DIR / "tool" / "origin_json" / "frost_edit.json").read_text("utf-8"))
        assert stored["pixels"] == edited_art["pixels"]
        assert (TEST_LIBRARY_DIR / "images" / "frost_edit.png").is_file()
        assert (TEST_LIBRARY_DIR / "粒子库预览.png").is_file()

        library = await _ok(await client.get("/library", params={"q": "frost"}))
        assert [item["name"] for item in library] == ["frost_edit"]
        particle = await _ok(await client.get("/library/frost_edit"))
        assert particle["has_json"] and len(particle["art"]["pixels"]) == 16

        # 已入库的任务不能再审核
        again = (await client.post(f"/particle-runs/{run_id}/resume", json={"action": "reject"})).json()
        assert again["code"] == 1 and again["message"] == "任务当前不在待审核状态，无法继续"


async def test_reject_and_resume_validation():
    async with running_app(ScriptedLlm()) as client:
        run_id = await _create(client, variants=1)
        _, last_seq = await _wait_for_stop(client, run_id)
        missing_variant = (await client.post(f"/particle-runs/{run_id}/resume", json={"action": "approve"})).json()
        assert missing_variant["code"] == 1
        wrong_variant = (
            await client.post(f"/particle-runs/{run_id}/resume", json={"action": "approve", "variant_id": "v9"})
        ).json()
        assert wrong_variant["message"] == "所选变体不存在或没有可用的出图结果"
        no_feedback = (
            await client.post(f"/particle-runs/{run_id}/resume", json={"action": "revise", "variant_id": "v1"})
        ).json()
        assert no_feedback["message"] == "打回时请填写修改意见"
        bad_edit = (
            await client.post(
                f"/particle-runs/{run_id}/resume",
                json={"action": "approve", "variant_id": "v1", "edited_art": {"width": 8, "height": 8, "pixels": []}},
            )
        ).json()
        assert bad_edit["code"] == 1 and "手改后的像素数据不合法" in bad_edit["message"]

        await _ok(await client.post(f"/particle-runs/{run_id}/resume", json={"action": "reject"}))
        events, _ = await _wait_for_stop(client, run_id, last_seq)
        assert events[-1]["type"] == "run_rejected"
        page = await _ok(await client.get("/particle-runs", params={"status": "rejected"}))
        assert run_id in [item["id"] for item in page["items"]]


async def test_all_variants_failed():
    async with running_app(ScriptedLlm()) as client:
        run_id = await _create(client, description="全部失败", variants=2)
        events, _ = await _wait_for_stop(client, run_id)
        assert events[-1]["type"] == "run_failed"
        assert [event["type"] for event in events].count("parse_failed") == 6
        detail = await _ok(await client.get(f"/particle-runs/{run_id}"))
        assert detail["run"]["status"] == "failed" and "所有变体都失败" in detail["run"]["error_message"]


async def test_cancel_running_run():
    async with running_app(ScriptedLlm(delay_seconds=5)) as client:
        run_id = await _create(client)
        await asyncio.sleep(0.2)
        cancelled = await _ok(await client.post(f"/particle-runs/{run_id}/cancel"))
        assert cancelled["status"] == "cancelled"
        again = (await client.post(f"/particle-runs/{run_id}/cancel")).json()
        assert again["code"] == 1


async def test_options_and_prompt_preview():
    async with running_app(ScriptedLlm()) as client:
        options = await _ok(await client.get("/options"))
        assert [size["size"] for size in options["sizes"]] == [64, 32, 16, 8]
        assert options["recommendations"]["category"]["sigil"]["size"] == 64
        assert options["llm_configured"] is True
        preview = await _ok(
            await client.post("/prompt/preview", json={"description": "画个 64x64 法阵", "options": {"size": 32}})
        )
        assert "尺寸：32×32" in preview["user"] and preview["notes"]
        invalid = (await client.post("/prompt/preview", json={"description": "x", "options": {"size": 24}})).json()
        assert invalid["code"] == 1


@pytest.mark.parametrize("name", ["../etc", "a b"])
async def test_library_rejects_bad_names(name):
    async with running_app(ScriptedLlm()) as client:
        body = (await client.get(f"/library/{name}")).json()
        assert body["code"] == 1
