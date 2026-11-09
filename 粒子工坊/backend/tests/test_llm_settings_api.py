"""GET/PUT /settings/llm：页面 Key 优先于 .env、脱敏返回、落盘、清除后回退 .env。"""

import json

import httpx

from server.config.client_config import get_llm_client
from server.main import app

SETTINGS_URL = "/api/v1/settings/llm"


async def _call(method: str, json_body: dict | None = None) -> dict:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.request(method, SETTINGS_URL, json=json_body)
    assert response.status_code == 200
    return response.json()


async def test_page_key_overrides_env_and_can_be_cleared():
    llm = get_llm_client()
    try:
        initial = (await _call("GET"))["data"]
        assert initial["configured"] is True
        assert initial["api_key_source"] == "env"
        assert "test-key" not in json.dumps(initial)

        saved = await _call(
            "PUT", {"api_key": "sk-page-secret-1234", "base_url": "https://example.com/v1", "model": "my-model"}
        )
        assert saved["code"] == 0
        data = saved["data"]
        assert data["api_key_source"] == "page"
        assert data["api_key_masked"] == "sk-****1234"
        assert data["base_url"] == "https://example.com/v1"
        assert data["model"] == "my-model"
        assert llm.api_key == "sk-page-secret-1234"
        stored = json.loads(llm.settings_path.read_text(encoding="utf-8"))
        assert stored["api_key"] == "sk-page-secret-1234"

        # 不传 Key 只改模型：Key 保持不变
        kept = (await _call("PUT", {"model": "other-model"}))["data"]
        assert kept["api_key_masked"] == "sk-****1234"
        assert kept["model"] == "other-model"
        assert kept["base_url"] == llm.props.llm_base_url

        cleared = (await _call("PUT", {"clear_api_key": True}))["data"]
        assert cleared["api_key_source"] == "env"
        assert cleared["configured"] is True
        assert llm.api_key == "test-key"
    finally:
        llm.update(api_key=None, clear_api_key=True, base_url="", model="")
