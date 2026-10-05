"""wokao.api.routes.plan_routes — 备考计划生成、多目标融合排程、查询、更新、日程编辑与日历导出。"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, Response

from wokao.agents.planner import run_fused_agent
from wokao.api.dependencies import get_current_user, get_effective_user_llm_config
from wokao.api.schemas import PlanGenerateRequest, PlanUpdateRequest, ScheduleUpdateRequest
from wokao.db import crud

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Plans & Schedules"])


@router.get("/api/exams")
def api_exams():
    """获取全部预置国家考试大纲数据与分类。"""
    exams = crud.get_all_exams()
    categories = []
    for ex in exams:
        if ex["category"] not in categories:
            categories.append(ex["category"])
    return {"categories": categories, "exams": exams}


@router.get("/api/now")
def api_now():
    """获取服务器实时基准时间。"""
    now = datetime.now()
    weekdays_zh = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    return {
        "iso": now.isoformat(timespec="seconds"),
        "date": now.strftime("%Y-%m-%d"),
        "year": now.year,
        "month": now.month,
        "day": now.day,
        "weekday": weekdays_zh[now.weekday()],
        "quarter": (now.month - 1) // 3 + 1,
    }


@router.post("/api/generate_fused_plan")
def api_generate_fused_plan(req: PlanGenerateRequest, user: dict = Depends(get_current_user)):
    """生成多目标融合排程计划（同步处理：LLM 生成耗时 30~90s，走线程池避免阻塞事件循环）。"""
    if not req.goals:
        raise HTTPException(status_code=400, detail="请至少选择一个备考目标。")

    goals_data: List[Dict[str, Any]] = []
    for g in req.goals:
        name = (g.exam_name or "").strip()
        if not name:
            continue
        exam = crud.get_exam_by_name(name)
        if exam is None:
            raise HTTPException(status_code=400, detail=f"未找到考试「{name}」，请检查目标名称。")
        goals_data.append({
            "exam_name": exam["exam_name"],
            "category": exam["category"],
            "annual_period": exam.get("annual_period", ""),
            "exam_time": exam.get("exam_time", ""),
            "official_website": exam.get("official_website", ""),
            "exam_subjects": exam["exam_subjects"],
            "target_info": g.target_info or "",
        })

    if not goals_data:
        raise HTTPException(status_code=400, detail="没有有效的备考目标。")

    user_llm = get_effective_user_llm_config(user["user_id"])
    result = run_fused_agent({
        "goals_data": goals_data,
        "daily_hours": req.daily_hours,
        "user_feedback": req.user_feedback or "",
        "use_web_search": req.use_web_search,
        "llm_config": user_llm,
    })

    exam_summary: str = result.get("exam_summary", "")
    fused_json = result.get("fused_json", {})
    fused_plan_str: str = json.dumps(fused_json, ensure_ascii=False) if fused_json else ""
    combined_target: str = "；".join(f"{g.exam_name}：{g.target_info or ''}" for g in req.goals if g.exam_name)

    plan_id: int = crud.save_user_plan(
        user_id=user["user_id"],
        username=user["username"],
        exam_name=exam_summary,
        target_info=combined_target,
        daily_hours=req.daily_hours,
        user_feedback=req.user_feedback or "",
        generated_plan=result.get("generated_markdown", ""),
        title=exam_summary,
        is_fused=result.get("is_fused", True),
        fused_plan=fused_plan_str,
        goals_json=json.dumps([g.model_dump() for g in req.goals], ensure_ascii=False),
    )

    saved = crud.get_plan_by_id(plan_id)
    return {
        "plan_id": plan_id,
        "generated_plan": result.get("generated_markdown", ""),
        "is_fused": result.get("is_fused", True),
        "fused_plan": fused_json,
        "exam_name": exam_summary,
        "web_sources": result.get("web_sources", []),
        "degraded": bool(result.get("llm_error")),
        "created_at": str(saved["created_at"] if saved else ""),
    }


@router.get("/api/plans")
def api_get_plans(user: dict = Depends(get_current_user)):
    """获取当前考生全部归档计划。"""
    plans = crud.get_user_plans(user["user_id"], limit=100)
    return {"count": len(plans), "plans": plans}


@router.get("/api/plans/{plan_id}")
def api_get_plan_detail(plan_id: int, user: dict = Depends(get_current_user)):
    """获取单个计划详情。"""
    plan = crud.get_plan_by_id(plan_id)
    if not plan or plan.get("user_id") != user["user_id"]:
        raise HTTPException(status_code=404, detail="计划不存在或无权访问")
    return {"plan": plan}


@router.put("/api/plans/{plan_id}")
def api_update_plan(plan_id: int, req: PlanUpdateRequest, user: dict = Depends(get_current_user)):
    """修改计划字段与微调。"""
    plan = crud.get_plan_by_id(plan_id)
    if not plan or plan.get("user_id") != user["user_id"]:
        raise HTTPException(status_code=404, detail="计划不存在或无权访问")

    fields: Dict[str, Any] = {}
    if req.title is not None:
        fields["title"] = req.title
    if req.target_info is not None:
        fields["target_info"] = req.target_info
    if req.daily_hours is not None:
        fields["daily_hours"] = req.daily_hours
    if req.user_feedback is not None:
        fields["user_feedback"] = req.user_feedback

    if fields:
        crud.update_plan(plan_id, user["user_id"], **fields)

    updated = crud.get_plan_by_id(plan_id)
    return {"ok": True, "plan": updated}


@router.put("/api/plans/{plan_id}/schedule")
def api_update_schedule(plan_id: int, req: ScheduleUpdateRequest, user: dict = Depends(get_current_user)):
    """更新编辑后的日程安排。"""
    plan = crud.get_plan_by_id(plan_id)
    if not plan or plan.get("user_id") != user["user_id"]:
        raise HTTPException(status_code=404, detail="计划不存在或无权访问")

    try:
        schedule_data = json.loads(req.schedule_json)
    except Exception:
        raise HTTPException(status_code=400, detail="日程 JSON 格式无效")

    crud.update_plan(plan_id, user["user_id"], fused_plan=req.schedule_json)
    updated = crud.get_plan_by_id(plan_id)
    return {"status": "ok", "plan": updated}


@router.delete("/api/plans/{plan_id}")
def api_delete_plan(plan_id: int, user: dict = Depends(get_current_user)):
    """删除计划。"""
    plan = crud.get_plan_by_id(plan_id)
    if not plan or plan.get("user_id") != user["user_id"]:
        raise HTTPException(status_code=404, detail="计划不存在或无权访问")
    crud.delete_plan(plan_id, user["user_id"])
    return {"ok": True}


# ---------------------------------------------------------------------------
# 日历与文件导出
# ---------------------------------------------------------------------------

_WEEKDAY_OFFSET: Dict[str, int] = {
    "周一": 0, "星期一": 0, "Monday": 0,
    "周二": 1, "星期二": 1, "Tuesday": 1,
    "周三": 2, "星期三": 2, "Wednesday": 2,
    "周四": 3, "星期四": 3, "Thursday": 3,
    "周五": 4, "星期五": 4, "Friday": 4,
    "周六": 5, "星期六": 5, "Saturday": 5,
    "周日": 6, "星期日": 6, "Sunday": 6,
}


def _parse_time_block(tb: str) -> tuple[int, int, int, int]:
    m = re.search(r"(\d{1,2})[:：](\d{2})\s*[-~至到]\s*(\d{1,2})[:：](\d{2})", tb or "")
    if m:
        return int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))
    logger.warning("时段 %r 无法解析，.ics 导出按默认 09:00-10:30 落位。", tb)
    return 9, 0, 10, 30


def _ics_escape(value: str) -> str:
    """按 RFC 5545 转义 TEXT 值：反斜杠、分号、逗号与换行。"""
    return (
        str(value)
        .replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
    )


_ICS_VTIMEZONE = "\r\n".join([
    "BEGIN:VTIMEZONE",
    "TZID:Asia/Shanghai",
    "BEGIN:STANDARD",
    "DTSTART:19700101T000000",
    "TZOFFSETFROM:+0800",
    "TZOFFSETTO:+0800",
    "TZNAME:CST",
    "END:STANDARD",
    "END:VTIMEZONE",
])


def _build_plan_ics(plan: dict) -> str:
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//WoKao ExamAgent//Academic Planning//CN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{_ics_escape(plan.get('title') or plan.get('exam_name') or '我考备考计划')}",
        "X-WR-TIMEZONE:Asia/Shanghai",
        _ICS_VTIMEZONE,
    ]

    base_date = datetime.now()
    monday = (base_date - timedelta(days=base_date.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    fused_str = plan.get("fused_plan", "")
    fused_data = None
    if fused_str:
        try:
            fused_data = json.loads(fused_str)
        except Exception:
            fused_data = None

    event_id = 1
    if fused_data and isinstance(fused_data, dict) and "tracks" in fused_data:
        for t in fused_data.get("tracks", []):
            exam_name = t.get("exam_name", "备考")
            for task in t.get("tasks", []):
                week_idx = max(1, int(task.get("week", 1))) - 1
                wd_str = task.get("weekday", "周一")
                day_offset = _WEEKDAY_OFFSET.get(wd_str, 0)
                sh, sm, eh, em = _parse_time_block(task.get("time_block", ""))

                task_date = monday + timedelta(weeks=week_idx, days=day_offset)
                dt_start = task_date.replace(hour=sh, minute=sm)
                dt_end = task_date.replace(hour=eh, minute=em)
                if dt_end <= dt_start:
                    dt_end = dt_start + timedelta(hours=float(task.get("duration_hours", 1.5)))

                dt_stamp_str = datetime.now().strftime("%Y%m%dT%H%M%S")
                dt_start_str = dt_start.strftime("%Y%m%dT%H%M%S")
                dt_end_str = dt_end.strftime("%Y%m%dT%H%M%S")
                title = f"[{exam_name}] {task.get('title', '学习任务')}"
                desc = f"类型：{task.get('type', '学习')}\\n时长：{task.get('duration_hours', 1)}h\\n指标：{task.get('metric', '按计划执行')}"

                lines.extend([
                    "BEGIN:VEVENT",
                    f"UID:wokao-plan-{plan['id']}-{event_id}@wokao.local",
                    f"DTSTAMP:{dt_stamp_str}",
                    f"DTSTART;TZID=Asia/Shanghai:{dt_start_str}",
                    f"DTEND;TZID=Asia/Shanghai:{dt_end_str}",
                    f"SUMMARY:{_ics_escape(title)}",
                    f"DESCRIPTION:{_ics_escape(desc)}",
                    "STATUS:CONFIRMED",
                    "END:VEVENT",
                ])
                event_id += 1

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines)


@router.get("/api/plans/{plan_id}/export.ics")
@router.get("/api/plans/{plan_id}/export/ics")
def api_export_ics(plan_id: int, user: dict = Depends(get_current_user)):
    """导出标准 iCalendar (.ics) 日历文件。"""
    plan = crud.get_plan_by_id(plan_id)
    if not plan or plan.get("user_id") != user["user_id"]:
        raise HTTPException(status_code=404, detail="计划不存在或无权访问")

    ics_content = _build_plan_ics(plan)
    filename = f"plan_{plan_id}.ics"
    return Response(
        content=ics_content,
        media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/api/plans/{plan_id}/export.md")
@router.get("/api/plans/{plan_id}/export/markdown")
def api_export_markdown(plan_id: int, user: dict = Depends(get_current_user)):
    """导出 Markdown 规划文件。"""
    plan = crud.get_plan_by_id(plan_id)
    if not plan or plan.get("user_id") != user["user_id"]:
        raise HTTPException(status_code=404, detail="计划不存在或无权访问")

    md_content = plan.get("generated_plan", "") or f"# {plan.get('title')}\n暂无规划文本。"
    filename = f"plan_{plan_id}.md"
    return Response(
        content=md_content,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
