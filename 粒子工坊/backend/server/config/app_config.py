"""FastAPI 应用装配：CORS、全局异常、路由、静态目录（任务产物 / 粒子库贴图）。"""

from __future__ import annotations

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from common.constant.library_constant import LIBRARY_URL_SEGMENT, RUNS_URL_SEGMENT
from common.properties.app_properties import get_app_properties
from server.controller import (
    extract_controller,
    health_controller,
    library_controller,
    llm_settings_controller,
    option_controller,
    particle_run_controller,
)
from server.handler.global_exception_handler import register_exception_handlers


def build_api_router() -> APIRouter:
    api = APIRouter()
    for module in (
        health_controller,
        option_controller,
        particle_run_controller,
        extract_controller,
        library_controller,
        llm_settings_controller,
    ):
        api.include_router(module.router)
    return api


def create_app(lifespan=None) -> FastAPI:
    props = get_app_properties()
    app = FastAPI(title=props.app_name, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=props.cors_origin_list(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_exception_handlers(app)
    app.include_router(build_api_router(), prefix=props.api_prefix)

    runs_dir = props.runs_path()
    runs_dir.mkdir(parents=True, exist_ok=True)
    app.mount(f"{props.api_prefix}{RUNS_URL_SEGMENT}", StaticFiles(directory=runs_dir), name="runs")
    images_dir = props.particle_library_path() / "images"
    app.mount(
        f"{props.api_prefix}{LIBRARY_URL_SEGMENT}",
        StaticFiles(directory=images_dir, check_dir=False),
        name="library",
    )
    return app
