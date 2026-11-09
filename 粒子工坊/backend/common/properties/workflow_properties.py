"""功能一工作流配置：每个变体的模型调用次数上限、默认变体数。"""

from functools import lru_cache

from common.properties.base_properties import BaseProperties


class WorkflowProperties(BaseProperties):
    # 每个变体每轮（首轮 / 每次打回）最多调用模型次数；解析失败与检查不过共用
    workflow_max_attempts: int = 3
    workflow_default_variants: int = 2


@lru_cache
def get_workflow_properties() -> WorkflowProperties:
    return WorkflowProperties()
