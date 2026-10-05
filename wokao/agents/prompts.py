"""wokao.agents.prompts — 规划师 Prompt 模板与时间工具。

设计原则：LLM 只产「任务内容」（标题/类型/量化指标/时长/目标周次），
不产出星期与具体时段——时间落位由 wokao.scheduler.engine 确定性求解。
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Optional


def current_datetime_raw() -> str:
    """返回当前基准实时时间，包含完整中文日期、星期与 ISO 格式。"""
    t = datetime.now()
    weekdays: tuple[str, ...] = ("星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日")
    wd_str: str = weekdays[t.weekday()]
    quarter: int = (t.month - 1) // 3 + 1
    return f"{t.year}年{t.month}月{t.day}日 {wd_str}（第{quarter}季度，ISO: {t.strftime('%Y-%m-%d')}）"


def extract_exam_month(annual_period: str, exam_time: str = "") -> str:
    """尝试从考试时间文本中提取关键月份提示（缺省返回 '考前'）。"""
    text = f"{annual_period} {exam_time}".strip()
    m = re.search(r"(\d{1,2})\s*月", text)
    if m:
        return f"{m.group(1)}月"
    m = re.search(r"[-/](\d{1,2})[-/]", text)
    if m:
        return f"{int(m.group(1))}月"
    return "考前"


def build_fused_prompt_text(
    goals_data: List[Dict[str, Any]],
    daily_hours: float,
    user_feedback: str,
    now_str: str,
    retrieved_policy: str = "",
) -> str:
    """多目标协同融合规划 Prompt —— 只要求内容池，不要求时刻表。"""
    blocks = []
    for g in goals_data:
        subjects_str = ", ".join(g.get("exam_subjects", []) or [])
        blocks.append(
            f"目标【{g.get('exam_name')}】\n"
            f"  科目：{subjects_str}\n"
            f"  周期：{g.get('annual_period', '')}\n"
            f"  考情：{g.get('exam_time', '')}\n"
            f"  用户意向：{g.get('target_info', '') or '未指定'}\n"
        )
    goals_md = "\n".join(blocks)

    policy_block = ""
    if retrieved_policy:
        policy_block = f"\n【最新官方政策检索结果（仅供内容参考）】\n{retrieved_policy[:3000]}\n"

    schema = (
        "请输出严格的标准 JSON 格式，包裹在 ```json ... ``` 代码块中。结构如下：\n"
        "{\n"
        '  "title": "融合计划标题（如：考研 + 考公 双线并进全周期方案）",\n'
        '  "summary": "一句话概述",\n'
        '  "tracks": [\n'
        "    {\n"
        '      "exam_name": "<必须与给定目标名称一字不差>",\n'
        '      "key_dates": "该目标的关键节点说明",\n'
        '      "tasks": [\n'
        "        {\n"
        '          "title": "任务标题（含科目与阶段语义）",\n'
        '          "type": "学习|刷题|训练|模考|复盘|背诵|材料",\n'
        '          "metric": "可核验的量化完成标准（题量/篇数/正确率/套数）",\n'
        '          "duration_hours": 2.0,\n'
        '          "target_week": 3\n'
        "        }\n"
        "      ]\n"
        "    }\n"
        "  ]\n"
        "}\n"
        "硬性要求：\n"
        f"1. tracks 必须恰好覆盖全部 {len(goals_data)} 个目标，exam_name 与给定名称完全一致；\n"
        "2. 只输出任务「内容」和「目标周次 target_week」，禁止输出星期几或具体时段——时间落位由系统确定性引擎完成；\n"
        "3. 每个 track 输出 15~40 个任务，按 基础(前40%周次)→强化(中间35%)→冲刺(后25%) 三阶段梯度分布；\n"
        "4. duration_hours 取值 0.5~3 小时；同一周内任务总时量需与用户每日可用时长匹配，宁缺毋滥；\n"
        "5. metric 必须可核验，杜绝「认真学习」「多多复习」这类空话。\n"
    )

    prompt = (
        "你是一名顶尖备考统筹规划师。用户正在同时准备多个国家考试目标，需要为每个目标设计一套分阶段、可量化、可执行的任务内容池。"
        "系统将把你产出的内容确定性地排布到未来数周的周日程网格中（自动消解跨目标时间冲突并遵守每日时长上限）。\n\n"
        f"【当前实时基准】\n  {now_str}\n\n"
        + goals_md
        + policy_block
        + f"\n【用户每日可支配学习总量】{daily_hours} 小时/天（所有目标合计）\n"
    )
    if user_feedback:
        prompt += f"\n【用户微调要求（优先级最高）】{user_feedback}\n"
    prompt += "\n" + schema
    return prompt
