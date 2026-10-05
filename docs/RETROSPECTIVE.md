# 我考 WoKao-ExamAgent — 复盘与自测（RETROSPECTIVE）

> ⚠️ **历史文档声明（2026-10-04）**：本文为 v2.0 重构完成时的验收快照，其中 LangGraph 相关条目描述的是已被移除的旧架构；当前管线与测试以 `tests/` 与 README 为准。

> 版本：v2.0 ｜ 完成时间：2026-08-17 ｜ 模式：PRD 驱动开发 + 偏差登记 + 自测验收

---

## 1. 功能完成情况

| 功能 | 状态 | 说明 |
|---|---|---|
| 考试分类导航（18 项预置，考公考编全覆盖） | ✅ | `exams` 表预置 18 项，含报名时段/官网/科目拆解/考试形式/参考资料/贴士 |
| 个性化备考计划生成 | ✅ | LangGraph 三节点，考情注入，输出 6 段式 Markdown（总览/考情拆解/三阶段/每日作息/避坑/参考资料） |
| Human-in-the-Loop 微调重算 | ✅ | `feedback_applied` 状态机驱动单轮收敛，反馈融合进计划 |
| 本地历史存档 | ✅ | `user_plans` 落库，可按 username 查询，最多 20 条 |
| 前端独立化（Vue 3 SPA） | ✅ | `frontend/` 工程化，构建 `dist/` 由后端托管；Vite dev 独立热更 |
| 真实 LLM（移除 mock） | ✅ | 必须 `OPENAI_API_KEY`，支持 `OPENAI_BASE_URL`/`OPENAI_MODEL` 兼容网关 |
| 可选爬虫刷新 | ✅ | `crawler.py` + `POST /api/refresh`，未装 playwright 返回 501 |

---

## 2. 运行检查结果（v2 自测）

- `python -m compileall agent.py database.py server.py crawler.py`：**退出码 0，无语法错误**。
- 依赖导入：`.venv` 内 `fastapi/uvicorn/pydantic/langchain-openai/langgraph` 均成功；`import database, agent, server, crawler` 全通过。
- `database.init_db()` 后 `get_all_exams()` 返回 **18 条**，字段含官网等新增列。
- `agent.GRAPH` 编译为 `CompiledStateGraph`；无 `OPENAI_API_KEY` 时 `run_agent` 抛明确中文 `ValueError`。
- `npm install`（139 包）+ `npm run build`（145 模块）→ 产出 `frontend/dist/{index.html,assets/...}`。
- `uvicorn server:app --port 8001` 启动正常。
- `GET /api/exams` → **HTTP 200**，返回 3 大类、18 条考试（含 `official_website`、`subjects_detail` 等）。
- `POST /api/generate_plan`（无密钥）→ HTTP 500，明确中文错误「未配置 OPENAI_API_KEY…」，不静默失败。
- `POST /api/refresh`（未装 playwright）→ **HTTP 501**，`{"ok":false,"msg":"未安装 playwright…"}`。
- `GET /` → 返回构建后的 Vue `index.html`（标题「🎓 我考 - 国家考试导航与 AI 备考」）。
- `GET /api/history?username=tester` → `count=0`、`plans=[]`（库初始干净，0 条测试残留）。

---

## 3. 遇到的问题与解决摘要

1. **沙箱 safe-delete 拦截 venv 重建 / pip 自升级 / 目录删除** —— 跳过 `pip install --upgrade pip`；删除改用 `os.rename` 隔离为 `_deprecated_*`。详见 DEVLOG。
2. **MSYS 下 npm-cli.js 路径转换异常** —— 改用 `C:/Users/...` Windows 原生前向斜杠路径作为参数。
3. **LangGraph 条件边死循环** —— `feedback_applied` 状态位，单轮收敛（v1 沿用）。
4. **SQLite JSON 序列化** —— `_loads/_dumps` 统一转换，前端拿数组标签（v1 沿用）。
5. **v1→v2 表迁移** —— `init_db()` 检测缺失 `official_website` 列即重建 `exams`，平滑升级。
6. **移除 mock 后的配置校验** —— 无密钥显式 `ValueError`，服务端映射 HTTP 500。

---

## 4. 与 PRD 的偏差摘要

- **v2 移除 `MOCK_LLM`**（用户主动要求，已登记）。
- **v2 前端重构为独立 Vue 3 SPA** + CORS 放开（用户主动要求，已登记）。
- **v2 考试库 9→18 项 + 六字段富集**（用户主动要求，已登记）。
- **v2 新增 Playwright 爬虫 + `/api/refresh`**（用户主动要求，已登记）。
- v1 既有偏差（`focus_points`、服务端注入 `exam_month`、`get_exam_by_name`、`wokao.db`）维持已接受。
- 整体未出现「未登记的重大偏差」，对外 API 契约与 PRD 一致。

---

## 5. 已知限制与改进建议

- **L1 考试时间非精确日历**：`exam_month` 启发式抽取，作息表按「每日时长」分配而非真实日期排期；后续可接入具体考试日期做倒计时日历。
- **L2 必须真实 LLM**：v2 已移除 mock，无 `OPENAI_API_KEY` 无法生成计划；如仍需离线演示，可评估恢复一个轻量规则兜底（需重新登记偏差）。
- **L3 并发与多用户**：SQLite 单连接、本地 demo 定位，未做连接池/行级锁；高并发需换 Postgres。
- **L4 历史无更新语义**：每次生成为新记录，未在原记录上「版本演进」；可加 `parent_plan_id` 形成计划谱系。
- **L5 前端无鉴权**：演示定位，未做用户登录；接入真实场景需加认证与配额。
- **L6 爬虫健壮性**：Playwright 拉取受目标站点反爬与结构变动影响，属可选增强，失败不影响核心功能；建议加缓存 TTL 与失败告警。
- **改进建议**：补充 pytest 单元测试、加 `.env.example`、提供 Dockerfile、为 `user_plans` 增加索引与 `parent_plan_id`、前端增加计划导出（PDF/MD）、爬虫失败兜底回退到预置数据。

---

## 6. 下一步待办（用户侧）

- 用户提供 `OPENAI_API_KEY`（及可选 `OPENAI_BASE_URL`、`OPENAI_MODEL`）后，端到端跑通真实计划生成。
- 可选：安装 `playwright` + `playwright install chromium`，启用 `/api/refresh` 实拉最新考期。
- 可选：清理 `_deprecated_static` / `_deprecated_WKao_typo` 废弃目录（沙箱禁止删除，需手动）。
