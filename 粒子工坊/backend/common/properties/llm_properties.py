"""大模型配置：OpenAI 兼容接口（默认 DeepSeek）的 Key、地址、模型名、温度、超时与思考模式。"""

from functools import lru_cache

from common.properties.base_properties import BaseProperties


class LlmProperties(BaseProperties):
    llm_api_key: str = ""
    llm_base_url: str = "https://api.deepseek.com"
    # DeepSeek 官方接口上 deepseek-flash 即 DeepSeek-V4.1-Flash-1017
    llm_model: str = "deepseek-flash"
    # 0.7 兼顾多样性与格式稳定；调高画面更多变但更容易数错字符
    llm_temperature: float = 0.7
    # 思考模式下单次调用常要几十秒到几分钟；调小容易在思考途中超时
    llm_timeout_seconds: float = 300.0
    # 思考模式：enabled / disabled；留空则不发 thinking 参数（给不认识该参数的其它兼容接口用）
    llm_thinking: str = "enabled"
    # 思考强度：low / high / max；仅思考开启时发送。调高画得更用心，但更慢、更费 token
    llm_reasoning_effort: str = "high"
    # 思考开启时，在每种画布尺寸的输出上限之外额外给的 token 预算（思考内容也计入 max_tokens）。
    # 调小省钱，但容易“思考占满上限、json 被截断”
    llm_thinking_token_budget: int = 16000

    @property
    def configured(self) -> bool:
        return bool(self.llm_api_key.strip())

    @property
    def thinking_enabled(self) -> bool:
        return self.llm_thinking.strip().lower() == "enabled"


@lru_cache
def get_llm_properties() -> LlmProperties:
    return LlmProperties()
