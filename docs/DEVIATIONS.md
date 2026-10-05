# 我考 WoKao-ExamAgent — 偏差记录（DEVIATIONS）

> 记录实际实现与 PRD 不一致或采用更优方案之处。

---

## 偏差条目（v1 已登记）：ExamAgentState 新增 `focus_points` 字段

- **实际实现**：`parse_target_node` 产出 `focus_points: List[str]`（从 `target_info` 抽取院校层次/专业/科目关键词 + 结合 `exam_subjects`），供 `generate_plan_node` 作为「备考重点」消费，避免空转。
- **影响范围**：仅 Agent 内部状态结构；对外 API 契约不变。
- **状态**：已接受

---

## 偏差条目（v1 已登记）：`exam_month` 由服务端注入

- **实际实现**：`server.py` 在调用 `run_agent` 前用 `_extract_exam_month(exam["exam_time"])` 注入 `exam_month`；`parse_target_node` 直接沿用，不再重复解析考试时间。
- **状态**：已接受

---

## 偏差条目（v1 已登记）：额外提供 `get_exam_by_name()`

- **实际实现**：新增 `get_exam_by_name(exam_name)` 供服务端按名精确取字段向 Agent 传参。
- **状态**：已接受

---

## 偏差条目（v1 已登记）：数据库文件 `wokao.db`

- **实际实现**：固定为项目根目录 `wokao.db`（`database.py` 中 `DB_PATH` 推导）。
- **状态**：已接受

---

## 偏差条目（v2）：移除 `MOCK_LLM` 离线兜底

- **原 v1 实现 / PRD**：v1 PRD §2.4 将 `MOCK_LLM=1` 列为可选降级，要求实现时登记偏差；v1 已实现完整离线规则生成。
- **v2 实际实现**：**按用户明确要求移除 mock**（「mock 这边我觉得可以先去掉」）。`agent.py` 不再含 `_mock_generate()`；`generate_plan_node` 在无 `OPENAI_API_KEY` 时直接抛 `ValueError` 返回明确中文错误。离线验收改为：用户配置真实 `OPENAI_API_KEY`（或任意 OpenAI 兼容网关的 `OPENAI_BASE_URL`）后运行。
- **偏差原因**：用户将接入真实 LLM，mock 不再需要且会掩盖「未配密钥」的真实问题。
- **影响范围**：移除 v1 的零密钥离线生成能力；`OPENAI_API_KEY` 成为生成计划的硬性前置。
- **状态**：已接受（用户主动要求）

---

## 偏差条目（v2）：前端由单文件 HTML 重构为独立 Vue 3 SPA

- **原 v1 实现 / PRD**：v1 PRD §6 前端为单文件 `static/index.html`（CDN 引入 Tailwind + Marked.js），§8 验收要求「首页 `static/index.html` 可打开」。
- **v2 实际实现**：按用户要求「重新独立出来一个文件夹，去进行前后端的框架的搭配」「用 Vue 3 去进行前端开发」，前端升级为独立工程 `frontend/`（Vite + Vue 3 + Tailwind + markdown-it + axios），构建产物 `frontend/dist/` 由后端 `index()` 静态托管，开发期可用独立 Vite dev server（`npm run dev`，代理 `/api` → `:8000`）。后端因此新增 `CORSMiddleware(allow_origins=["*"])`。
- **偏差原因**：用户认为原界面过简、不好看，要求工程化前端框架以获得更好观感与可维护性。
- **影响范围**：目录结构变更（新增 `frontend/`）；运行方式变更（需先 `npm install && npm run build`）；`GET /` 返回 Vue SPA 而非静态 HTML。
- **状态**：已接受（用户主动要求）

---

## 偏差条目（v2）：考试库由 9 项扩展到 18 项并富集结构化字段

- **原 v1 实现 / PRD**：v1 预置 9 项（考研/国考省考/四六级/申博/三支一扶/高考/中考/教资/软考），`exams` 字段为 id/category/exam_name/exam_time/exam_subjects/description。
- **v2 实际实现**：预置扩至 **18 项**，重点补强考公考编（国考/省考、选调生、教师招聘、事业单位、银行招考、法考、CPA、执业医师/卫生资格等），并新增 `registration_time`、`official_website`、`subjects_detail`、`exam_format`、`reference_materials`、`tips` 六个字段（JSON 编码）。`init_db()` 自动迁移缺失 `official_website` 列的旧表。
- **偏差原因**：用户认为 v1「什么都没有」「需要很全面、包括考公考编」。部分 2026 考期数据经联网检索（WebSearch）嵌入。
- **影响范围**：`exams` schema 扩展；`agent.py` 状态图新增对应字段并注入 prompt；前端 `ExamDetail.vue` 增加展示。
- **状态**：已接受（用户主动要求）

---

## 偏差条目（v2）：新增 Playwright 可选爬虫 + `POST /api/refresh`

- **原 v1 实现 / PRD**：v1 无爬虫，考试数据为静态预置。
- **v2 实际实现**：新增 `crawler.py`（基于 `sync_playwright`），`POST /api/refresh` 按来源（scs/yz/neea）拉取最新考期/报名信息并回写 `exams`；未装 playwright 时返回 `HTTP 501` + 友好提示。该能力为可选，`requirements.txt` 中 playwright 注释为可选依赖。
- **偏差原因**：用户提出「可能需要网页爬取」获取最新考试信息；以可选模块形式落地，不影响核心功能。
- **影响范围**：新增 `crawler.py`、后端 `api_refresh` 路由、requirements 注释；仅在显式调用时激活。
- **状态**：已接受

---

## 偏差条目（v2）：API 端口与托管形态调整

- **实际实现**：后端默认端口仍为 8000，但绑定 `127.0.0.1`；生产由后端直接托管 `frontend/dist/`，开发期前端独立占用 Vite 默认 `5173` 并经代理访问后端，故放开 CORS。
- **影响范围**：仅部署/开发形态变化，API 契约（`/api/*`）不变。
- **状态**：已接受
