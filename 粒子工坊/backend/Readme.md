# 粒子工坊 · 后端

FastAPI + LangGraph + SQLite。设计见 `../设计文档.md`。

```powershell
cd 粒子工坊/backend
copy .env.example .env        # 可选：LLM_API_KEY 也可以在前端「设置」页填写
uv sync
uv run uvicorn server.main:app --port 8002 --reload
```

模型 Key：前端「设置」页保存到 `data/llm_settings.json`（明文、仅本机），优先于 `.env`，保存后立即生效；清除后回退 `.env`。

检查（提交前全过）：

```powershell
uv run ruff check .
uv run lint-imports
uv run pytest
```

命令行直跑生成（不入库、不写数据库，产物在 `data/cli_runs/`）：

```powershell
uv run python -m server.task.generate_cli "一枚冰霜碎片，中间有一点高光" --size 32 --palette cold_blue --repeat 3
```

目录：`common`（常量 / 异常 / 配置 / 返回体）→ `pojo`（dto / entity / vo）→ `server`（controller / task / service / workflow / mapper / client / calc），依赖方向由 `pyproject.toml` 的 import-linter 契约约束。
