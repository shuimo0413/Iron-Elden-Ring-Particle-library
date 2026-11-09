"""路径工具：定位 backend 根目录，把配置里的相对路径按 backend 根目录解析。

一律用 Path(__file__).absolute()，不用 resolve()：工作区里 粒子库/ 是 junction，
resolve() 会穿过 junction 指到父目录。
"""

from __future__ import annotations

import os
from pathlib import Path

# 本文件在 backend/common/utils/ → 上两级即 backend 根
BACKEND_ROOT = Path(__file__).absolute().parent.parent.parent


def resolve_backend_path(raw: str) -> Path:
    """绝对路径原样返回；相对路径拼到 backend 根后做字面规范化（不解析 junction）。"""
    path = Path(raw)
    if path.is_absolute():
        return path
    return Path(os.path.normpath(BACKEND_ROOT / path))
