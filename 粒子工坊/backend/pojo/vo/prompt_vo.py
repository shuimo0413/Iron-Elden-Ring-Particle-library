"""提示词预览出参。"""

from pydantic import BaseModel, Field


class PromptVO(BaseModel):
    system: str
    user: str
    # 冲突提示等（如「已忽略描述中的尺寸」）
    notes: list[str] = Field(default_factory=list)
