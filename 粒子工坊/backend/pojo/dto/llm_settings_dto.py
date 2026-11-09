"""模型设置入参：前端「设置」页保存。"""

from pydantic import BaseModel, Field


class LlmSettingsDTO(BaseModel):
    # 留空 / 不传表示不改当前 Key（前端不会回显明文）
    api_key: str | None = Field(default=None, max_length=512)
    # true 时清掉页面保存的 Key，回退到 .env
    clear_api_key: bool = False
    # 留空回退 .env 的 LLM_BASE_URL
    base_url: str = Field(default="", max_length=512)
    # 留空回退 .env 的 LLM_MODEL
    model: str = Field(default="", max_length=128)
