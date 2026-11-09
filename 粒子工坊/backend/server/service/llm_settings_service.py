"""模型设置：读取 / 保存前端填写的 Key、接口地址、模型名；保存后立即作用于后续模型调用。"""

from __future__ import annotations

import asyncio
from dataclasses import asdict

from pojo.dto.llm_settings_dto import LlmSettingsDTO
from pojo.vo.llm_settings_vo import LlmSettingsVO
from server.client.llm_client import LlmClient


class LlmSettingsService:
    def __init__(self, llm: LlmClient) -> None:
        self.llm = llm

    # 当前生效的设置（Key 脱敏）
    def get(self) -> LlmSettingsVO:
        return LlmSettingsVO(**asdict(self.llm.snapshot()))

    # 保存设置：写 data/llm_settings.json 并重建模型客户端
    async def update(self, dto: LlmSettingsDTO) -> LlmSettingsVO:
        snapshot = await asyncio.to_thread(
            self.llm.update,
            api_key=dto.api_key,
            clear_api_key=dto.clear_api_key,
            base_url=dto.base_url,
            model=dto.model,
        )
        return LlmSettingsVO(**asdict(snapshot))
