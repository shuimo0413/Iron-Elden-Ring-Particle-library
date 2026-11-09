"""pytest 公共配置：项目根加入 sys.path；数据目录与粒子库都指向临时目录，绝不写真实 粒子库/。

临时粒子库：拷贝真实 tool/ 下的三个共享脚本 + 两张贴图，入库与重建总览图都发生在这里。
环境变量必须在导入任何 properties 之前设置（properties 有 lru_cache）。
"""

import os
import shutil
import sys
from pathlib import Path

_BACKEND_ROOT = Path(__file__).absolute().parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from tests.support_paths import REAL_LIBRARY_DIR, TEST_DATA_DIR, TEST_LIBRARY_DIR  # noqa: E402

SHARED_TOOL_SCRIPTS = ("render_pixel_art.py", "extract_image_rgba.py", "gen_particle_showcase.py")
SAMPLE_PARTICLE_COUNT = 2


def _build_test_library() -> None:
    (TEST_LIBRARY_DIR / "tool" / "origin_json").mkdir(parents=True, exist_ok=True)
    (TEST_LIBRARY_DIR / "images").mkdir(parents=True, exist_ok=True)
    for script in SHARED_TOOL_SCRIPTS:
        shutil.copy2(REAL_LIBRARY_DIR / "tool" / script, TEST_LIBRARY_DIR / "tool" / script)
    for png in sorted((REAL_LIBRARY_DIR / "images").glob("*.png"))[:SAMPLE_PARTICLE_COUNT]:
        shutil.copy2(png, TEST_LIBRARY_DIR / "images" / png.name)


_build_test_library()

os.environ["DATA_DIR"] = str(TEST_DATA_DIR)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(TEST_DATA_DIR / 'app.sqlite').as_posix()}"
os.environ["CHECKPOINT_DB_PATH"] = str(TEST_DATA_DIR / "checkpoints.sqlite")
os.environ["PARTICLE_LIBRARY_DIR"] = str(TEST_LIBRARY_DIR)
os.environ["LLM_API_KEY"] = "test-key"
os.environ["WORKFLOW_MAX_ATTEMPTS"] = "3"
