"""文件访问常量：静态目录的 URL 段、粒子名格式。"""

import re

# data/runs/ 产物，挂在接口前缀下：/api/v1/files/runs/<run_id>/<variant_id>/<attempt_no>/xxx
RUNS_URL_SEGMENT = "/files/runs"
# 粒子库 images/*.png（只读）
LIBRARY_URL_SEGMENT = "/files/library"
# 粒子库总览图
SHOWCASE_URL_PATH = "/files/showcase.png"

# 库内文件名：英文字母、数字、下划线、短横线，最长 64
PARTICLE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_\-]{1,64}$")
