"""外部客户端单例：大模型、粒子库、任务产物目录。service 注入与工作流共用同一实例。"""

from __future__ import annotations

from functools import lru_cache

from common.properties.app_properties import get_app_properties
from common.properties.llm_properties import get_llm_properties
from server.client.llm_client import LlmClient
from server.client.particle_library_client import ParticleLibraryClient
from server.client.run_artifact_client import RunArtifactClient

# 前端「设置」页保存的模型配置，放在 data/ 下（已被 git 忽略）
LLM_SETTINGS_FILE_NAME = "llm_settings.json"


@lru_cache
def get_llm_client() -> LlmClient:
    return LlmClient(get_llm_properties(), get_app_properties().data_path() / LLM_SETTINGS_FILE_NAME)


@lru_cache
def get_library_client() -> ParticleLibraryClient:
    return ParticleLibraryClient(get_app_properties().particle_library_path())


@lru_cache
def get_artifact_client() -> RunArtifactClient:
    runs_dir = get_app_properties().runs_path()
    runs_dir.mkdir(parents=True, exist_ok=True)
    return RunArtifactClient(runs_dir)
