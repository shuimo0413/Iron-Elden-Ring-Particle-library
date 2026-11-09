"""节点依赖：大模型、粒子库、产物目录。由 workflow_config 构造后传给 build_graph。"""

from __future__ import annotations

from dataclasses import dataclass

from server.client.llm_client import LlmClient
from server.client.particle_library_client import ParticleLibraryClient
from server.client.run_artifact_client import RunArtifactClient


@dataclass
class WorkflowDeps:
    llm: LlmClient
    library: ParticleLibraryClient
    artifacts: RunArtifactClient
