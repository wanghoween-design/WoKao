"""wokao.scheduler.engine — 确定性排程引擎。

第一性原理：备考排程是「约束满足问题」，不是「文本生成问题」。

职责边界：
- LLM（内容层）：为每条目标轨道产出任务内容池（标题 / 类型 / 量化指标 / 建议时长 / 目标周次）；
- 本引擎（结构层）：把任务确定性地落位到「周 × 星期 × 时段」网格上，并保证三条硬约束：
    C1 容量约束 —— 任一考生任一天的学习总时长 ≤ daily_hours（跨轨道合计）；
    C2 冲突约束 —— 同一时刻全局唯一（跨轨道永不重叠）；
    C3 锚点约束 —— 第 1 周锚定计划创建周的周一，horizon 不越过最近考试日。

输出 JSON 契约（前端 FusedPlanView / AppleCalendarWeekView 依赖）：
{
  "title": str, "summary": str, "horizon_weeks": int,
  "tracks": [{"exam_name", "target_info", "key_dates",
              "tasks": [{"title","week","weekday","time_block","duration_hours",
                         "type","metric","status"}]}],
  "meta": {"engine", "anchor_monday", "horizon_weeks", "exam_dates",
           "daily_capacity_hours", "dropped_tasks"}
}
"""
from __future__ import annotations

import re
from collections import deque
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

WEEKDAYS_ZH: List[str] = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

# 学习时段池：三段黄金学习区（与前端 AppleCalendarWeekView 的 07:00–23:00 视窗对齐）
SEGMENTS: List[Tuple[str, str]] = [
    ("08:30", "11:30"),   # 上午段 3h
    ("14:00", "17:00"),   # 下午段 3h
    ("19:00", "22:00"),   # 晚间段 3h
]

MAX_DAILY_STUDY_HOURS = 9.0   # 三段时段池总和上限
MIN_TASK_HOURS = 0.25         # 最小可排任务粒度
ENGINE_ID = "wokao-scheduler/1.0"


# ---------------------------------------------------------------------------
# 时间小工具
# ---------------------------------------------------------------------------

def hhmm_to_float(text: str) -> float:
    """'08:30' -> 8.5。"""
    parts = str(text).split(":")
    return int(parts[0]) + int(parts[1]) / 60.0


def float_to_hhmm(value: float) -> str:
    """8.5 -> '08:30'。"""
    total = int(round(value * 60))
    return f"{total // 60:02d}:{total % 60:02d}"


# ---------------------------------------------------------------------------
# C3 锚点：从考情文本解析最近的未来考试日期
# ---------------------------------------------------------------------------

_DATE_FULL_RE = re.compile(r"(\d{4})\s*[-/年\.]\s*(\d{1,2})\s*[-/月\.]\s*(\d{1,2})\s*日?")
_MONTH_RE = re.compile(r"(?:(\d{4})\s*[-/年])?\s*(\d{1,2})\s*月\s*(上旬|中旬|下旬|月底|月初|底|初)?")
_XUN_DAY: Dict[str, int] = {
    "上旬": 8, "中旬": 15, "下旬": 24,
    "月初": 5, "月底": 26, "底": 26, "初": 8,
}
_EXAM_WORDS = ("考试", "笔试", "初试", "开考", "举行")


def parse_exam_anchor(*texts: Any) -> Optional[date]:
    """从考情文本中解析最近一个未来考试日期；解析不出返回 None。

    优先级：
      1. 完整日期（2026-12-20 / 2026年12月20日）——最强信号；
      2. 带「旬」关键词或紧邻考词（考试/笔试/初试…）的月份；
      3. 普通月份提及（兜底，取窗口内最晚的一个，避开"报名月"误判为"考试月"）。
    """
    today = date.today()
    limit = today + timedelta(days=400)
    keyworded: List[date] = []
    generic: List[date] = []

    for text in texts:
        if not text:
            continue
        s = str(text)

        full_spans: List[Tuple[int, int]] = []
        for m in _DATE_FULL_RE.finditer(s):
            try:
                d = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            except ValueError:
                continue
            full_spans.append((m.start(), m.end()))
            if today <= d <= limit:
                keyworded.append(d)

        # 先收集全部月份匹配边界：上下文窗口不得越过相邻月份，
        # 防止「10月报名，12月下旬考试」中远处的「考试」被误圈给报名月。
        month_spans = [(mm.start(), mm.end()) for mm in _MONTH_RE.finditer(s)]
        for i, m in enumerate(_MONTH_RE.finditer(s)):
            if any(a <= m.start() < b for a, b in full_spans):
                continue  # 与完整日期重叠，跳过
            month = int(m.group(2))
            if not (1 <= month <= 12):
                continue
            phase = m.group(3)
            day = _XUN_DAY.get(phase or "", 15)
            prev_end = month_spans[i - 1][1] if i > 0 else 0
            next_start = month_spans[i + 1][0] if i + 1 < len(month_spans) else len(s)
            context = (
                s[max(prev_end, m.start() - 2): m.start()]
                + s[m.end(): min(next_start, m.end() + 6)]
            )
            has_exam_word = any(w in context for w in _EXAM_WORDS)

            if m.group(1):
                try:
                    d = date(int(m.group(1)), month, day)
                except ValueError:
                    continue
                if today <= d <= limit:
                    (keyworded if (phase or has_exam_word) else generic).append(d)
            else:
                for y in (today.year, today.year + 1):
                    try:
                        d = date(y, month, day)
                    except ValueError:
                        continue
                    if today <= d <= limit:
                        (keyworded if (phase or has_exam_word) else generic).append(d)
                        break

    if keyworded:
        return min(keyworded)
    if generic:
        return max(generic)
    return None


def compute_window(
    exam_dates: List[Optional[date]],
    today: Optional[date] = None,
    max_weeks: int = 12,
    min_weeks: int = 1,
) -> Tuple[date, int]:
    """返回 (第1周周一, horizon周数)。horizon 不越过最近考试日所在周。"""
    today = today or date.today()
    start_monday = today - timedelta(days=today.weekday())
    valid = [d for d in exam_dates if isinstance(d, date)]
    horizon = max_weeks
    if valid:
        weeks_to_exam = ((min(valid) - start_monday).days // 7) + 1
        horizon = max(min_weeks, min(max_weeks, weeks_to_exam))
    return start_monday, max(1, horizon)


def phase_for_week(week: int, horizon: int) -> str:
    """12 周梯度跃升：基础精读 → 强化攻坚 → 真题冲刺。"""
    ratio = week / max(1, horizon)
    if ratio <= 0.40:
        return "基础"
    if ratio <= 0.75:
        return "强化"
    return "冲刺"


# ---------------------------------------------------------------------------
# LLM 内容池归一化（防御式：任何垃圾输入都不抛异常）
# ---------------------------------------------------------------------------

def _coerce_task(raw: Any) -> Optional[Dict[str, Any]]:
    """把 LLM 输出的单条任务强制规整为合法结构；不合规返回 None。"""
    if not isinstance(raw, dict):
        return None
    title = str(raw.get("title") or "").strip()
    if not title:
        return None
    try:
        dur = float(raw.get("duration_hours") or 2.0)
    except (TypeError, ValueError):
        dur = 2.0
    dur = min(max(dur, MIN_TASK_HOURS), 8.0)
    target_week = raw.get("target_week", raw.get("week"))
    try:
        target_week = int(target_week) if target_week is not None else None
    except (TypeError, ValueError):
        target_week = None
    if target_week is not None and not (1 <= target_week <= 52):
        target_week = None
    return {
        "title": title[:80],
        "type": str(raw.get("type") or "学习").strip()[:8] or "学习",
        "metric": str(raw.get("metric") or "").strip()[:80],
        "duration_hours": round(dur, 2),
        "target_week": target_week,
    }


def normalize_llm_tracks(
    raw_tracks: Any,
    goals_data: List[Dict[str, Any]],
) -> Dict[str, List[Dict[str, Any]]]:
    """把 LLM 返回的 tracks 原始结构归一化为 {目标名: [任务dict]}。

    匹配规则：精确同名 → 双向包含 → 丢弃。任何一层失败都静默降级。
    """
    goal_names = [str(g.get("exam_name") or "").strip() for g in goals_data]
    pools: Dict[str, List[Dict[str, Any]]] = {name: [] for name in goal_names}

    if not isinstance(raw_tracks, list):
        return pools

    for rt in raw_tracks:
        if not isinstance(rt, dict):
            continue
        name = str(rt.get("exam_name") or "").strip()
        matched: Optional[str] = None
        if name in pools:
            matched = name
        else:
            for gn in goal_names:
                if gn and (gn in name or name in gn):
                    matched = gn
                    break
        if not matched:
            continue
        tasks_raw = rt.get("tasks")
        if isinstance(tasks_raw, list):
            for t in tasks_raw[:120]:
                coerced = _coerce_task(t)
                if coerced:
                    pools[matched].append(coerced)
    return pools


# ---------------------------------------------------------------------------
# 兜底内容生成器（科目轮转 × 三阶段 × 周末角色，确定性无随机）
# ---------------------------------------------------------------------------

_FALLBACK_KINDS: Tuple[Tuple[str, str, str], ...] = (
    ("学习", "{subj}核心考点精读与框架梳理", "完成《{subj}》重点章节精读并产出思维导图"),
    ("刷题", "{subj}专项题库限时精练", "限时完成30道《{subj}》典型题并统计正确率"),
    ("攻坚", "{subj}高频重难点专项突破", "攻克2个《{subj}》高频难点并制成记忆卡片"),
)


def _make_fallback_task(goal: Dict[str, Any], week: int, horizon: int, weekday_idx: int, counter: int, max_dur: float) -> Dict[str, Any]:
    subjects = [s for s in (goal.get("exam_subjects") or []) if isinstance(s, str) and s.strip()] or ["综合科目"]
    subj = subjects[counter % len(subjects)]
    kind_idx = (counter // len(subjects)) % len(_FALLBACK_KINDS)
    _, title_tpl, metric_tpl = _FALLBACK_KINDS[kind_idx]
    phase = phase_for_week(week, horizon)

    if weekday_idx == 5:  # 周六：全真模考日
        return {"title": f"{phase}阶段全真模考与限时核分", "type": "模考",
                "metric": "限时完成1套真题并严格核分复盘错因", "duration_hours": round(min(3.0, max_dur), 2)}
    if weekday_idx == 6:  # 周日：复盘规划日
        return {"title": f"{phase}阶段周复盘与下周规划对齐", "type": "复盘",
                "metric": "输出本周错题清单并确认下周资料就绪", "duration_hours": round(min(2.0, max_dur), 2)}
    return {"title": f"{phase}阶段·{title_tpl.format(subj=subj)}",
            "type": _FALLBACK_KINDS[kind_idx][0],
            "metric": metric_tpl.format(subj=subj),
            "duration_hours": round(min(2.0, max_dur), 2)}


# ---------------------------------------------------------------------------
# 主入口：构建融合排程
# ---------------------------------------------------------------------------

def build_fused_schedule(
    goals_data: List[Dict[str, Any]],
    pools_by_name: Dict[str, List[Dict[str, Any]]],
    daily_hours: float,
    today: Optional[date] = None,
    user_feedback: str = "",
) -> Dict[str, Any]:
    """把各轨道任务内容池确定性落位，返回完整 fused_json dict。

    约束保证：
      C1 容量：每轨每日 ≤ capacity/n_tracks，跨轨合计 ≤ capacity；
      C2 冲突：(weekday, segment) 归属函数 owner=(d+s)%n 保证同时刻全局唯一；
      C3 锚点：horizon 受最近考试日倒排钳制。
    """
    today = today or date.today()
    goals_data = [g for g in goals_data if isinstance(g, dict) and (g.get("exam_name") or "").strip()]
    n = max(1, len(goals_data))

    # --- C3 锚点与窗口 ---
    anchors: Dict[str, Optional[date]] = {}
    for g in goals_data:
        explicit_iso = str(g.get("exam_date") or "").strip()
        parsed: Optional[date] = None
        if explicit_iso:
            try:
                parsed = date.fromisoformat(explicit_iso[:10])
            except ValueError:
                parsed = None
        if parsed is None:
            parsed = parse_exam_anchor(g.get("annual_period"), g.get("exam_time"))
        anchors[str(g["exam_name"])] = parsed

    start_monday, horizon = compute_window(list(anchors.values()), today=today)

    capacity = min(max(float(daily_hours or 4.0), 0.5), MAX_DAILY_STUDY_HOURS)
    share = capacity / n          # 每轨每日时长份额（硬约束）
    seg_len = 3.0                 # 每个时段池长度

    # --- 内容分桶 ---
    track_pools: List[list] = []
    for g in goals_data:
        name = str(g["exam_name"])
        pool = list((pools_by_name or {}).get(name) or [])
        hinted: List[Optional[Dict[str, Any]]] = [None] * horizon
        unhinted: List[Dict[str, Any]] = []
        for task in pool:
            tw = task.get("target_week")
            if tw is not None and 1 <= tw <= horizon and hinted[tw - 1] is None:
                hinted[tw - 1] = task
            else:
                unhinted.append(task)
        week_buckets: List[deque] = [deque() for _ in range(horizon)]
        overflow = 0
        for i, wk in enumerate(range(horizon)):
            if hinted[wk] is not None:
                week_buckets[wk].append(hinted[wk])
        rr_index = 0
        for task in unhinted:
            placed = False
            for step in range(horizon):
                w_idx = (rr_index + step) % horizon
                if sum(t.get("duration_hours", 2.0) for t in week_buckets[w_idx]) + task["duration_hours"] <= share * 7 * 1.05:
                    week_buckets[w_idx].append(task)
                    rr_index = w_idx + 1
                    placed = True
                    break
            if not placed:
                overflow += 1
        track_pools.append(week_buckets)

    # --- 落位 ---
    used_day: Dict[Tuple[int, int, int], float] = {}   # (track, week_idx, weekday) -> 已用时；按周重置
    pending: List[deque] = [deque() for _ in range(n)]
    counters = [0] * n             # 兜底任务轮转计数器
    dropped_total = 0
    tracks_out: List[Dict[str, Any]] = []

    all_tasks: List[List[Dict[str, Any]]] = [[] for _ in range(n)]
    for w_idx in range(horizon):
        # 上周遗留任务溢出即弃（容量优先），计数
        for t_idx in range(n):
            dropped_total += len(pending[t_idx])
            pending[t_idx] = deque(track_pools[t_idx][w_idx])
        for d in range(7):
            for s in range(len(SEGMENTS)):
                owner = (d + s) % n
                avail = share - used_day.get((owner, w_idx, d), 0.0)
                if avail < min(MIN_TASK_HOURS, share):
                    continue
                seg_start = hhmm_to_float(SEGMENTS[s][0])
                from_pool = bool(pending[owner])
                if from_pool:
                    item = pending[owner].popleft()
                else:
                    counters[owner] += 1
                    fb = _make_fallback_task(goals_data[owner], w_idx + 1, horizon, d, counters[owner],
                                             max_dur=min(seg_len, avail))
                    item = {**fb, "duration_hours": float(fb.get("duration_hours", 2.0))}
                remaining = float(item.get("_remaining", item.get("duration_hours", 2.0)))
                dur = min(remaining, seg_len, avail)
                dur = round(dur, 2)
                task_entry = {
                    "title": str(item.get("title", "")),
                    "week": w_idx + 1,
                    "weekday": WEEKDAYS_ZH[d],
                    "time_block": f"{float_to_hhmm(seg_start)}-{float_to_hhmm(seg_start + dur)}",
                    "duration_hours": dur,
                    "type": str(item.get("type", "学习")),
                    "metric": str(item.get("metric", "")) or "按质按量完成",
                    "status": "todo",
                }
                all_tasks[owner].append(task_entry)
                used_day[(owner, w_idx, d)] = used_day.get((owner, w_idx, d), 0.0) + dur
                rest = remaining - dur
                if rest >= min(MIN_TASK_HOURS, share):
                    if from_pool:
                        # 仅真实内容池任务允许跨日续接；引擎自产任务按槽位定尺寸不产生残段
                        cont = dict(item)
                        cont["_remaining"] = round(rest, 2)
                        pending[owner].appendleft(cont)
                    else:
                        dropped_total += 1

    # --- 组装输出（契约兼容前端） ---
    names = [str(g["exam_name"]) for g in goals_data]
    exam_summary = " + ".join(names)
    summary = f"未来 {horizon} 周统筹推进 {exam_summary} 备考日程。"
    if user_feedback.strip():
        summary += " 已融合你的微调意见。"

    for t_idx, g in enumerate(goals_data):
        key_dates_parts = [p for p in (g.get("annual_period"), g.get("exam_time")) if p]
        anchor = anchors.get(str(g["exam_name"]))
        if anchor:
            key_dates_parts.append(f"考试锚点：{anchor.isoformat()}")
        tracks_out.append({
            "exam_name": str(g["exam_name"]),
            "target_info": str(g.get("target_info") or ""),
            "key_dates": "；".join(key_dates_parts),
            "tasks": sorted(all_tasks[t_idx], key=lambda k: (k["week"], WEEKDAYS_ZH.index(k["weekday"]), k["time_block"])),
        })

    fused: Dict[str, Any] = {
        "title": f"{exam_summary} 多目标融合备考方案",
        "summary": summary,
        "horizon_weeks": horizon,
        "tracks": tracks_out,
        "meta": {
            "engine": ENGINE_ID,
            "anchor_monday": start_monday.isoformat(),
            "horizon_weeks": horizon,
            "exam_dates": {k: (v.isoformat() if v else None) for k, v in anchors.items()},
            "daily_capacity_hours": capacity,
            "dropped_tasks": dropped_total,
        },
    }
    return fused


def fused_to_markdown(fused: Dict[str, Any]) -> str:
    """渲染融合方案 Markdown 文本（供 .md 导出与 generated_plan 字段）。"""
    now_head = datetime.now().strftime("%Y-%m-%d")
    lines = [
        f"# {fused.get('title', '多目标融合备考计划')}",
        "",
        f"> {fused.get('summary', '多目标并行推进日程')}",
        "",
        f"📅 当前基准时间：{now_head}",
        "",
        "## 一、各目标关键节点与里程碑",
    ]
    for t in fused.get("tracks", []) or []:
        lines.append(f"- **{t.get('exam_name')}**：{t.get('key_dates', '按周推进')}")
    meta = fused.get("meta") or {}
    anchor = meta.get("anchor_monday")
    if anchor:
        lines.append(f"- 排期锚点：第 1 周 = {anchor}（周一）；共 {fused.get('horizon_weeks', '?')} 周")
    lines.append("")
    lines.append("## 二、周日程并行排布总览")
    for t in fused.get("tracks", []) or []:
        lines.append(f"### 🎯 目标轨道：{t.get('exam_name')}")
        for task in t.get("tasks", []) or []:
            wk = task.get("week", 1)
            wd = task.get("weekday", "") or "持续"
            tb = task.get("time_block", "安排时间段")
            lines.append(
                f"- **第{wk}周 {wd} {tb}** ｜ {task.get('title', '')} "
                f"（{task.get('type', '学习')}，{task.get('duration_hours', 1)}h）— 🎯 衡量指标：{task.get('metric', '按质按量完成')}"
            )
        lines.append("")
    return "\n".join(lines)
