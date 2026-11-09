"""工作流单例：启动时打开 AsyncSqliteSaver（checkpoints.sqlite）并编译主图，关闭时释放连接。

待审核任务的图状态存在 checkpoint 里，服务重启后用同一 thread_id 仍可 /resume。
"""

from __future__ import annotations

from pathlib import Path

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from common.properties.db_properties import get_db_properties
from server.config.client_config import get_artifact_client, get_library_client, get_llm_client
from server.workflow.deps import WorkflowDeps
from server.workflow.graph_builder import build_graph

_saver_context = None
_graph = None


async def init_workflow() -> None:
    global _saver_context, _graph
    if _graph is not None:
        return
    checkpoint_path = get_db_properties().resolved_checkpoint_path()
    Path(checkpoint_path).parent.mkdir(parents=True, exist_ok=True)
    _saver_context = AsyncSqliteSaver.from_conn_string(checkpoint_path)
    saver = await _saver_context.__aenter__()
    deps = WorkflowDeps(llm=get_llm_client(), library=get_library_client(), artifacts=get_artifact_client())
    _graph = build_graph(deps, checkpointer=saver)


async def close_workflow() -> None:
    global _saver_context, _graph
    if _saver_context is not None:
        await _saver_context.__aexit__(None, None, None)
    _saver_context = None
    _graph = None


def get_graph():
    if _graph is None:
        raise RuntimeError("工作流尚未初始化（init_workflow 未调用）")
    return _graph
