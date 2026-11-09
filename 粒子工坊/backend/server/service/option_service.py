"""按钮清单与提示词预览：选项来自 common.constant，预览不调模型。"""

from __future__ import annotations

from common.constant.canvas_size import CANVAS_SIZES, SUPPORTED_CANVAS_SIZES
from common.constant.particle_option import (
    CATEGORY_OPTIONS,
    DEFAULT_OPTIONS,
    OUTLINE_OPTIONS,
    PALETTE_OPTIONS,
    RECOMMENDATIONS,
    SYMMETRY_OPTIONS,
    VARIANT_COUNT_OPTIONS,
    OptionItem,
)
from common.properties.workflow_properties import WorkflowProperties
from pojo.dto.prompt_dto import PromptPreviewDTO
from pojo.vo.option_vo import CanvasSizeVO, OptionItemVO, OptionsVO
from pojo.vo.prompt_vo import PromptVO
from server.calc import prompt_calc
from server.client.llm_client import LlmClient


class OptionService:
    def __init__(self, llm: LlmClient, workflow_props: WorkflowProperties) -> None:
        self.llm = llm
        self.workflow_props = workflow_props

    # 按钮清单：各组选项、尺寸参数、色调锚点、推荐联动、默认值、模型是否已配置
    def options(self) -> OptionsVO:
        defaults = {**DEFAULT_OPTIONS, "variants": self.workflow_props.workflow_default_variants}
        return OptionsVO(
            sizes=[
                CanvasSizeVO(
                    size=spec.size,
                    margin_px=spec.margin_px,
                    max_colors=spec.max_colors,
                    min_coverage=spec.min_coverage,
                    max_coverage=spec.max_coverage,
                    preview_scale=spec.preview_scale,
                )
                for spec in (CANVAS_SIZES[size] for size in SUPPORTED_CANVAS_SIZES)
            ],
            categories=_items(CATEGORY_OPTIONS),
            palettes=_items(PALETTE_OPTIONS),
            outlines=_items(OUTLINE_OPTIONS),
            symmetries=_items(SYMMETRY_OPTIONS),
            variant_counts=list(VARIANT_COUNT_OPTIONS),
            defaults=defaults,
            recommendations=RECOMMENDATIONS,
            llm_configured=self.llm.configured,
        )

    # 提示词预览：与新建任务同一套拼装逻辑
    def preview(self, dto: PromptPreviewDTO) -> PromptVO:
        bundle = prompt_calc.build_prompt(dto.description, dto.options.model_dump())
        return PromptVO(system=bundle.system, user=bundle.user, notes=bundle.notes)


def _items(options: tuple[OptionItem, ...]) -> list[OptionItemVO]:
    return [
        OptionItemVO(value=item.value, label=item.label, anchors=[list(anchor) for anchor in item.anchors])
        for item in options
    ]
