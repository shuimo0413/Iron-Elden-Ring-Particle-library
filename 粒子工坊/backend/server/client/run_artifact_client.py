"""任务产物目录：data/runs/<run_id>/<variant_id>/<attempt_no>/ 下的提示词、模型原始返回、JSON、PNG。

对外只暴露相对 runs/ 的 posix 路径（存库用），对外地址由 service 拼接。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class RunArtifactClient:
    def __init__(self, runs_dir: Path) -> None:
        self.runs_dir = runs_dir

    def attempt_dir(self, run_id: int, variant_id: str, attempt_no: int) -> Path:
        path = self.runs_dir / str(run_id) / variant_id / str(attempt_no)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def relative(self, path: Path) -> str:
        return path.relative_to(self.runs_dir).as_posix()

    def absolute(self, relative_path: str) -> Path:
        return self.runs_dir / relative_path

    def write_text(self, run_id: int, variant_id: str, attempt_no: int, filename: str, text: str) -> str:
        path = self.attempt_dir(run_id, variant_id, attempt_no) / filename
        path.write_text(text, encoding="utf-8")
        return self.relative(path)

    def write_json(self, run_id: int, variant_id: str, attempt_no: int, filename: str, data: Any) -> str:
        return self.write_text(run_id, variant_id, attempt_no, filename, json.dumps(data, ensure_ascii=False, indent=2))

    def read_json(self, relative_path: str) -> Any:
        return json.loads(self.absolute(relative_path).read_text(encoding="utf-8"))
