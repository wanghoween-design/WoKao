# 我考 WoKao-ExamAgent — 产品需求文档（PRD）

> ⚠️ **历史文档声明（2026-10-04）**：本文成稿于去 LangGraph 重构之前。文中「LangGraph 状态图」「Human-in-the-Loop 重算」「状态图编排」等章节描述的是旧架构；当前实现为「LLM 内容池 + 确定性约束求解排程引擎」的顺序管线（见 `wokao/agents/planner.py` 与 `wokao/scheduler/engine.py`）。产品需求部分仍然有效，技术架构请以代码与 README 为准。

> 版本：v2.0 ｜ 状态：已批准（自驱动开发，未阻塞等待确认）
> 创建日期：2026-08-17 ｜ 最近更新：2026-08-17（v2 重构）

---

## 1. 项目概述与目标用户

**我考（WoKao-ExamAgent）** 是一款面向中国学生与社会考生的「国家考试大纲导航与个性化备考中枢」。它以结构化考试大纲数据库为入口，结合 LangGraph 驱动的 AI Agent，将用户的「目标院校 / 专业 / 科目 + 每日可用时长」解析为一份精准到【基础 / 强化 / 冲刺】三阶段、并附带【每日作息安排表】的 Markdown 备考计划；支持用户提交微调意见（Human-in-the-Loop）后自动重算。

**v2 重点升级**：
- **前端独立化**：从单文件 `static/index.html` 重构为独立的 **Vue 3 + Vite** 单页应用（`frontend/` 目录），构建产物 `frontend/dist/` 由后端托管，开发期可独立用 Vite dev server 热更新。
- **数据全面化**：预设考试由 9 项扩展到 **18 项**，重点补强「考公考编」类（国考/省考、选调生、事业单位、教师招聘、银行招考、法考、CPA 等），并新增报名时段、官网、科目拆解、考试形式、参考资料、备考贴士等结构化字段。
- **真实 LLM**：移除 v1 的 `MOCK_LLM` 离线兜底，改为必须配置 `OPENAI_API_KEY`（支持自定义 `OPENAI_BASE_URL` / `OPENAI_MODEL`，兼容任意 OpenAI 兼容网关）。
- **可选爬虫**：新增 `crawler.py`（基于 Playwright），通过 `POST /api/refresh` 拉取最新考试时间/报名信息，未装 playwright 时优雅返回 501。

**目标用户**：
- **高校 / 大学生**：考研、申博、四六级、三支一扶/西部计划、教资。
- **社会人 / 职业**：国考/省考、选调生、教师招聘(考编)、事业单位(考编)、软考、法考、注册会计师(CPA)、银行招考、执业医师/卫生资格。
- **中学生**：高考、中考、高职单招。
- **通用技能**：全国计算机等级考试(NCRE)。

**开放项默认值（已决策并记录）**：
- LLM：必须 `OPENAI_API_KEY`；可选 `OPENAI_BASE_URL`（默认走 OpenAI 官方）、`OPENAI_MODEL`（默认 `gpt-4o-mini`）。
- 后端 API 默认端口 `8000`，绑定 `127.0.0.1`（前端 dev 经 Vite 代理 `/api` 到 8000；生产由后端直接托管 `frontend/dist`）。
- 数据库文件名 `wokao.db`，位于项目根目录。
- 历史记录默认最多返回 20 条。

---

## 2. 核心功能需求

| 编号 | 功能 | 说明 | 优先级 |
|---|---|---|---|
| F1 | 考试分类导航 | 左栏按大类筛选，展示考试时间、报名时段、官网链接、科目标签、科目拆解表 | P0 |
| F2 | 个性化备考计划生成 | 输入目标 / 时长，Agent 生成含考情拆解 + 三阶段 + 每日作息表 + 避坑指南 + 参考资料 的 Markdown 计划 | P0 |
| F3 | 用户微调与计划重算 | 提交 `user_feedback`（如「周末不学」），触发重算并融合进新计划 | P0 |
| F4 | 本地历史存档 | 每次生成落地 SQLite，可按用户名查询历史计划卡片 | P1 |
| F5 | 考试信息刷新（可选） | `POST /api/refresh` 经 Playwright 拉取最新考期/报名信息，未装则 501 | P2 |

非功能需求：零修改即可构建运行；前端 Vue SFC 工程化；中文字符 UTF-8；移动端响应式（Tailwind 栅格）。

---

## 3. 数据模型设计

### 3.1 `exams` 表（考试大纲导航库，预置只读）

| 字段 | 类型 | 说明 |
|---|---|---|
| id | INTEGER PK AUTOINCREMENT | 主键 |
| category | TEXT NOT NULL | 考试大类（如「社会人 / 职业」） |
| exam_name | TEXT NOT NULL | 考试名称（如「国考/省考」） |
| exam_time | TEXT NOT NULL | 常规考试时间说明（含年份，如「国考笔试 2025-11-30」） |
| registration_time | TEXT | 报名时段说明 |
| official_website | TEXT | 官方网站名称 + 网址 |
| exam_subjects | TEXT NOT NULL | 核心科目，JSON 数组字符串 |
| subjects_detail | TEXT | 科目拆解，JSON 数组：[{name,type,score,duration,desc}] |
| exam_format | TEXT | 考试形式，JSON 数组字符串 |
| reference_materials | TEXT | 参考资料，JSON 数组字符串 |
| tips | TEXT | 备考贴士，JSON 数组字符串 |
| description | TEXT | 考试简介 |

> `init_db()` 兼容旧表：若 `exams` 缺少 `official_website` 列则自动重建，保证 v1→v2 平滑迁移。

### 3.2 `user_plans` 表（用户计划存档）

| 字段 | 类型 | 说明 |
|---|---|---|
| id | INTEGER PK AUTOINCREMENT | 主键 |
| username | TEXT NOT NULL | 考生名 / 标识 |
| exam_name | TEXT NOT NULL | 关联考试名称 |
| target_info | TEXT | 目标院校 / 专业 / 科目 |
| daily_hours | REAL | 每日可学时长（小时） |
| user_feedback | TEXT | 最近一次微调意见（落库保留原值便于审计） |
| generated_plan | TEXT | 生成的 Markdown 计划全文 |
| created_at | TIMESTAMP DEFAULT CURRENT_TIMESTAMP | 创建时间 |

> `user_plans.user_feedback` 落库时保留用户原始反馈文本（便于回溯），与 Agent 内部 `feedback_applied` 状态机解耦。

---

## 4. API 设计

基础前缀：`/api` ｜ 内容类型：`application/json; charset=utf-8` ｜ CORS：`*` 已放开（便于独立 Vite dev）

### 4.1 `GET /api/exams`
返回全部分类与考试列表（含 v2 新增字段）。
```json
{
  "categories": ["高校/大学生", "社会人/职业", "中学生"],
  "exams": [
    {
      "id": 1, "category": "高校/大学生", "exam_name": "考研",
      "exam_time": "初试 2025-12-20 至 21（网上报名 10-16 至 10-27）",
      "registration_time": "网上预报名 10-10 至 10-13；正式报名 10-16 至 10-27",
      "official_website": "中国研究生招生信息网 https://yz.chsi.com.cn",
      "exam_subjects": ["思想政治理论", "外国语", "业务课(一)", "业务课(二)"],
      "subjects_detail": [{"name":"思想政治理论","type":"公共课","score":100,"duration":"3h","desc":"马原、毛中特…"}],
      "exam_format": ["初试（国家统一组织，笔试）", "复试（招生单位组织）"],
      "reference_materials": ["教育部《2026 年全国硕士研究生招生工作管理规定》"],
      "tips": ["尽早确定院校与专业，避免报名后期扎堆"],
      "description": "全国硕士研究生统一招生考试"
    }
  ]
}
```

### 4.2 `POST /api/generate_plan`
请求体（JSON）：
```json
{
  "username": "考生A", "category": "高校/大学生", "exam_name": "考研",
  "target_info": "目标：985 计算机 408", "daily_hours": 4, "user_feedback": "周末不学"
}
```
响应示例（成功）：
```json
{ "plan_id": 1, "generated_plan": "# 考研备考计划 ...", "is_approved": true, "created_at": "2026-08-17T10:00:00" }
```
错误（未配置密钥）：
```json
{ "detail": "未配置 OPENAI_API_KEY，无法生成计划。请在环境变量中设置 OPENAI_API_KEY（以及可选的 OPENAI_BASE_URL、OPENAI_MODEL）后重试。" }
```
HTTP 状态：成功 `200`；参数校验失败 `422`；未配置密钥 `500`。

### 4.3 `GET /api/history?username=考生A`
返回该用户最近最多 20 条计划（字段同 `user_plans` 落库行）。

### 4.4 `POST /api/refresh`（可选）
请求体 `{"source": "scs" | "yz" | "neea"}`，经 Playwright 拉取指定来源最新考期/报名信息并回写 `exams`。
- 未安装 playwright：`HTTP 501`，`{"ok":false,"msg":"未安装 playwright…"}`。
- 成功：`{"ok":true,"source":...,"url":...,"updated":{...},"errors":[...]}`。

---

## 5. LangGraph 状态图

### 5.1 `ExamAgentState`（TypedDict）
| 字段 | 类型 | 说明 |
|---|---|---|
| category | str | 考试大类 |
| exam_name | str | 考试名称 |
| target_info | str | 目标院校 / 专业 / 科目 |
| daily_hours | float | 每日可学时长 |
| exam_month | str | 由考试时间解析出的月份提示 |
| exam_subjects | List[str] | 核心科目列表 |
| focus_points | List[str] | parse 阶段解析出的备考重点 |
| official_website | str | v2：官网（注入 prompt） |
| subjects_detail | List[dict] | v2：科目拆解（注入 prompt） |
| exam_format | List[str] | v2：考试形式（注入 prompt） |
| reference_materials | List[str] | v2：参考资料（注入 prompt） |
| tips | List[str] | v2：备考贴士（注入 prompt） |
| user_feedback | str | 用户微调意见 |
| generated_plan | str | 生成的 Markdown 计划 |
| error | str | 错误信息 |
| is_approved | bool | 人工复核是否通过 |
| feedback_applied | bool | 反馈是否已融合（防止条件边死循环） |

### 5.2 Nodes
- `parse_target_node`：从 `target_info` 抽取院校层次 / 专业 / 科目关键词，结合 `exam_subjects` 生成 `focus_points`，并从 `exam_time` 解析 `exam_month`。
- `generate_plan_node`：调用 LLM 基于考情字段 + 解析结果 + 时长 + 反馈，产出 6 段式 Markdown（总览 / 考情拆解 / 三阶段 / 每日作息表 / 避坑指南 / 参考资料与官网）；未配置 `OPENAI_API_KEY` 抛 `ValueError`。融合 `user_feedback` 后置 `feedback_applied=True` 并清空反馈。
- `human_review_node`：反馈非空且未应用 → `is_approved=False` → 回 `generate_plan_node`；否则 `is_approved=True` → END。

### 5.3 Edges 与条件路由
```
START → parse_target_node → generate_plan_node → human_review_node
human_review_node --(is_approved==False)--> generate_plan_node
human_review_node --(is_approved==True)--> END
```
循环防护同 v1：`feedback_applied` 状态机保证二次进入 review 必然走向 END。

---

## 6. 前端结构（Vue 3 SPA）

独立目录 `frontend/`（Vite + Vue 3 + Tailwind + markdown-it + axios）：
- `ExamSidebar.vue`：分类 Tab + 考试卡片列表，emit `select`。
- `ExamDetail.vue`：展示描述、考试时间、报名时段、官网链接、科目标签、科目拆解表、考试形式、贴士、参考资料。
- `PlanStudio.vue`：用户名/目标/时长/反馈输入，生成按钮（loading），Markdown 渲染，emit `done`。
- `HistoryList.vue`：按用户名查询，计划卡片 + 内联预览。
- `App.vue`：12 栅格（侧栏 3 + 详情 4 + 计划 5），挂载时拉取 `/api/exams`，默认选中首个。

构建：`cd frontend && npm install && npm run build` → `frontend/dist/`，后端 `index()` 静态托管；开发期 `npm run dev`（Vite 代理 `/api` → `:8000`）。

---

## 7. 开发任务拆解与里程碑

| 里程碑 | 交付物 | 状态 |
|---|---|---|
| M1 PRD | docs/PRD.md | ✅ |
| M2 数据层 | database.py（v2 富集 schema + 18 预置 + 迁移） | ✅ |
| M3 Agent 层 | agent.py（v2 状态图 + 真实 LLM + 考情 prompt） | ✅ |
| M4 服务层 | server.py（API + CORS + 托管 dist + /api/refresh） | ✅ |
| M5 前端 | frontend/（Vue 3 SPA） | ✅ |
| M5b 爬虫 | crawler.py（Playwright 可选刷新） | ✅ |
| M6 工程化 | requirements / setup 脚本 / .gitignore / README | ✅ |
| M7 验收 | compileall + build + 启动 + curl + DB 落库 | ✅ |

---

## 8. 测试验收标准

1. `python -m compileall .` 无语法错误；`frontend/` 可 `npm install && npm run build` 产出 `dist/`。
2. `uvicorn server:app` 启动，`GET /api/exams` 返回 200 与 18 条预置考试（含官网等新增字段）。
3. 配置 `OPENAI_API_KEY` 后 `POST /api/generate_plan` 返回 `plan_id>0` 且 `generated_plan` 含「总览 / 考情拆解 / 基础 / 强化 / 冲刺 / 每日作息 / 避坑指南 / 参考资料」。
4. `wokao.db` 生成，`user_plans` 可落库；`GET /api/history` 返回历史。
5. 未配置密钥时 `generate_plan` 返回明确中文错误（HTTP 500），不静默失败。
6. 未装 playwright 时 `POST /api/refresh` 返回 501。

---

## 9. 风险与边界

- **R1 无 OpenAI 密钥**：返回明确中文错误（v2 已移除 mock，不再离线兜底）。
- **R2 LangGraph 条件边死循环**：`feedback_applied` 状态机防护（见 §5.3）。
- **R3 SQLite 并发写**：单用户本地 demo，独立连接 + 异常捕获。
- **R4 考试时间自然语言**：`exam_month` 启发式抽取，非精确日历排期。
- **R5 移动端**：基础响应式（Tailwind 栅格折叠）。
- **R6 爬虫反爬**：Playwright 拉取受目标站点反爬与结构变动影响，属可选增强，失败不影响核心功能。
