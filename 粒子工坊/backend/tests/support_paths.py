"""测试共用路径：真实粒子库（只读）与临时目录。conftest 与各测试都从这里取，避免直接 import conftest。"""

import tempfile
from pathlib import Path

BACKEND_ROOT = Path(__file__).absolute().parent.parent
# 真实粒子库：backend → 粒子工坊 → 粒子库（测试只读）
REAL_LIBRARY_DIR = BACKEND_ROOT.parent.parent

TEST_ROOT = Path(tempfile.mkdtemp(prefix="particle_workshop_test_"))
TEST_LIBRARY_DIR = TEST_ROOT / "library"
TEST_DATA_DIR = TEST_ROOT / "data"
