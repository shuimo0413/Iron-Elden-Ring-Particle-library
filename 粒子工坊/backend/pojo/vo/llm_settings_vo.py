"""模型设置出参：Key 只给脱敏值。"""

from pydantic import BaseModel


class LlmSettingsVO(BaseModel):
    configured: bool
    # 如 sk-****abcd；未配置时为空
    api_key_masked: str
    # page：页面保存的 Key；env：.env 里的 Key；none：都没有
    api_key_source: str
    # 当前生效值（页面优先，否则 .env）
    base_url: str
    model: str
