"""应用入口：uv run uvicorn server.main:app --port 8002

启动时（lifespan）：建表 → 把仍为 running 的任务标记为 interrupted → 打开 checkpoint 并编译工作流；
关闭时：中断后台任务 → 关闭 checkpoint → 释放数据库连接。
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from common.properties.app_properties import get_app_properties
from common.properties.db_properties import get_db_properties
from common.properties.workflow_properties import get_workflow_properties
from server.config.app_config import create_app
from server.config.client_config import get_llm_client
from server.config.database_config import close_database, get_database
from server.config.logging_config import setup_logging
from server.config.workflow_config import close_workflow, init_workflow
from server.service.particle_run_service import ParticleRunService
from server.task import run_runner

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    database = get_database()
    if get_db_properties().db_auto_create:
        await database.create_all()
    async with database.session_factory() as session:
        service = ParticleRunService(session, get_app_properties(), get_llm_client(), get_workflow_properties())
        interrupted = await service.mark_interrupted_on_startup()
    if interrupted:
        log.warning("启动时把 %s 个运行中的任务标记为已中断", interrupted)
    await init_workflow()
    library_dir = get_app_properties().particle_library_path()
    log.info("粒子库目录：%s（images 存在=%s）", library_dir, (library_dir / "images").is_dir())
    if not get_llm_client().configured:
        log.warning("未配置 LLM_API_KEY：可在前端「设置」页填写；未填前功能一（AI 生成）不可用，功能二（取色）照常")
    yield
    await run_runner.shutdown()
    await close_workflow()
    await close_database()


setup_logging()
app = create_app(lifespan=lifespan)
