"""命令行直跑生成（M1 验收）：选项 + 描述 → 问模型 → 解析 / 检查 → PNG，不写数据库、不入库。

用法（在 backend/ 下）：
    uv run python -m server.task.generate_cli "一枚冰霜碎片，中间有一点高光" --size 32 --palette cold_blue
    uv run python -m server.task.generate_cli "小火花" --size 8 --repeat 3

产物写到 data/cli_runs/<时间戳>/<序号>/，每次尝试一个子目录。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime

from common.constant.canvas_size import SUPPORTED_CANVAS_SIZES, get_canvas_spec
from common.properties.app_properties import get_app_properties
from common.properties.workflow_properties import get_workflow_properties
from pojo.dto.particle_run_dto import RunOptionsDTO
from server.calc import art_check_calc, compact_art_calc, prompt_calc
from server.client.llm_client import LlmClient
from server.client.particle_library_client import ParticleLibraryClient
from server.client.run_artifact_client import RunArtifactClient
from server.config.client_config import get_llm_client


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="粒子工坊命令行生成（不入库）")
    parser.add_argument("description", help="一句话描述")
    parser.add_argument("--size", type=int, default=32, choices=SUPPORTED_CANVAS_SIZES)
    parser.add_argument("--category", default="auto")
    parser.add_argument("--palette", default="auto")
    parser.add_argument("--outline", default="dark")
    parser.add_argument("--symmetry", default="none")
    parser.add_argument("--repeat", type=int, default=1, help="独立重复生成次数（验收时每种尺寸跑 3 次）")
    return parser.parse_args()


async def _generate_once(
    index: int,
    description: str,
    options: dict,
    llm: LlmClient,
    library: ParticleLibraryClient,
    artifacts: RunArtifactClient,
    max_attempts: int,
) -> bool:
    spec = get_canvas_spec(options["size"])
    bundle = prompt_calc.build_prompt(description, options)
    for note in bundle.notes:
        print(f"  [提示] {note}")
    messages = [{"role": "system", "content": bundle.system}, {"role": "user", "content": bundle.user}]
    variant_id = f"r{index}"
    for attempt_no in range(1, max_attempts + 1):
        reply = await llm.chat_json(messages, max_tokens=spec.max_tokens)
        artifacts.write_text(0, variant_id, attempt_no, "prompt.txt", prompt_calc.render_messages_text(messages))
        artifacts.write_text(0, variant_id, attempt_no, "response.json", reply.content)
        usage = (
            f"tokens {reply.prompt_tokens}+{reply.completion_tokens}"
            f"（思考 {reply.reasoning_tokens}）finish={reply.finish_reason}"
        )
        result = compact_art_calc.parse_compact_art(
            reply.content,
            size=spec.size,
            max_colors=spec.max_colors,
            finish_reason=reply.finish_reason,
            reasoning_tokens=reply.reasoning_tokens,
            existing_names=frozenset(library.list_names()),
        )
        if reply.content:
            messages.append({"role": "assistant", "content": reply.content})
        if not result.ok:
            print(f"  第 {attempt_no} 次：解析失败（{usage}）")
            for problem in result.problems:
                print(f"    - {problem}")
            messages.append({"role": "user", "content": prompt_calc.build_retry_message(result.problems)})
            continue
        report = art_check_calc.check_art(
            result.standard_art,
            spec=spec,
            symmetry=options["symmetry"],
            outline=options["outline"],
            unused_palette_keys=result.unused_palette_keys,
        )
        art_rel = artifacts.write_json(0, variant_id, attempt_no, "art.json", result.standard_art)
        attempt_dir = artifacts.attempt_dir(0, variant_id, attempt_no)
        art_path = artifacts.absolute(art_rel)
        library.render_png(art_path, attempt_dir / "preview_x1.png", scale=1)
        preview = library.render_png(art_path, attempt_dir / "preview_scaled.png", scale=spec.preview_scale)
        artifacts.write_json(0, variant_id, attempt_no, "check_report.json", report.to_dict())
        status = "通过" if report.passed else "规则不过"
        print(f"  第 {attempt_no} 次：解析成功，{status}（{usage}）→ {preview}")
        for warning in result.warnings:
            print(f"    · {warning}")
        if report.passed:
            return True
        for problem in report.problems:
            print(f"    - {problem}")
        messages.append({"role": "user", "content": prompt_calc.build_retry_message(report.problems)})
    return False


async def _main() -> int:
    args = _parse_args()
    llm = get_llm_client()
    if not llm.configured:
        print("未配置 LLM_API_KEY（前端「设置」页或 backend/.env）", file=sys.stderr)
        return 1
    options = RunOptionsDTO(
        size=args.size, category=args.category, palette=args.palette, outline=args.outline, symmetry=args.symmetry
    ).model_dump()
    app_props = get_app_properties()
    out_dir = app_props.data_path() / "cli_runs" / datetime.now().strftime("%Y%m%d_%H%M%S")
    library = ParticleLibraryClient(app_props.particle_library_path())
    artifacts = RunArtifactClient(out_dir)
    print(f"选项：{json.dumps(options, ensure_ascii=False)}\n产物目录：{out_dir}")
    successes = 0
    for index in range(1, args.repeat + 1):
        print(f"[{index}/{args.repeat}]")
        ok = await _generate_once(
            index, args.description, options, llm, library, artifacts, get_workflow_properties().workflow_max_attempts
        )
        successes += int(ok)
    print(f"完成：{successes}/{args.repeat} 次在次数内通过全部硬性规则")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(asyncio.run(_main()))
