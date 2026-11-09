"""依赖装配：controller 通过 Depends 获取 service，service 不感知 FastAPI。"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from common.properties.app_properties import get_app_properties
from common.properties.extract_properties import get_extract_properties
from common.properties.workflow_properties import get_workflow_properties
from server.config.client_config import get_library_client, get_llm_client
from server.config.database_config import get_db
from server.service.extract_service import ExtractService
from server.service.library_service import LibraryService
from server.service.llm_settings_service import LlmSettingsService
from server.service.option_service import OptionService
from server.service.particle_run_service import ParticleRunService

BusinessDb = Annotated[AsyncSession, Depends(get_db)]


def get_option_service() -> OptionService:
    return OptionService(get_llm_client(), get_workflow_properties())


def get_particle_run_service(db: BusinessDb) -> ParticleRunService:
    return ParticleRunService(db, get_app_properties(), get_llm_client(), get_workflow_properties())


def get_extract_service() -> ExtractService:
    return ExtractService(get_extract_properties(), get_library_client())


def get_library_service() -> LibraryService:
    return LibraryService(get_app_properties(), get_library_client())


def get_llm_settings_service() -> LlmSettingsService:
    return LlmSettingsService(get_llm_client())


OptionServiceDep = Annotated[OptionService, Depends(get_option_service)]
ParticleRunServiceDep = Annotated[ParticleRunService, Depends(get_particle_run_service)]
ExtractServiceDep = Annotated[ExtractService, Depends(get_extract_service)]
LibraryServiceDep = Annotated[LibraryService, Depends(get_library_service)]
LlmSettingsServiceDep = Annotated[LlmSettingsService, Depends(get_llm_settings_service)]
