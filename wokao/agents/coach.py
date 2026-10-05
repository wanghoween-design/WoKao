"""wokao.agents.coach — AI 伴学导师与日程动态微调引擎。"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from langchain_core.messages import HumanMessage, SystemMessage

from wokao.agents.planner import _get_llm_instance

logger = logging.getLogger(__name__)


def chat_with_coach(
    message: str,
    active_task: Optional[Dict[str, Any]] = None,
    active_track_name: str = "",
    plan_title: str = "",
    llm_config: Optional[Dict[str, Any]] = None,
) -> str:
    """与伴学导师进行多轮对话，提供考点拆解、出题测试、答疑或微调建议。"""
    task_context_block = ""
    if active_task and isinstance(active_task, dict):
        title = active_task.get("title", "")
        time_block = active_task.get("time_block", "")
        metric = active_task.get("metric", "")
        duration = active_task.get("duration_hours", 1)
        weekday = active_task.get("weekday", "")
        week = active_task.get("week", 1)
        task_context_block = f"""
【考生当前聚焦的任务卡片上下文】：
- 目标轨道：{active_track_name or '备考目标'}
- 所属周次：第 {week} 周 · {weekday}
- 安排时段：{time_block}（预估用时 {duration} 小时）
- 任务标题：{title}
- 量化指标：{metric}
"""

    system_prompt = f"""你是一名贴心、专业、严谨且充满鼓励的 AI 备考规划与伴学导师。
你的职责：
1. 为考生拆解具体考点与核心理论难点，提供实战解题思路与速记口诀；
2. 如果考生请求出题或测试，请出 2~3 道针对性的高质量典型题目（含考点剖析与标准答案）；
3. 如果考生请求调整日程（如某天太累想少学、或想插入健身跑步、换到周末等），请给出清晰的调整方案，并告知考生可点击下方的「⚡ 应用意见并重排日程」让系统一键重新排期；
4. 语言亲切生动、条理清晰，多使用 emoji 与结构化 Markdown，激发考生的学习动力与信心。

当前备考方案：{plan_title or '多目标融合备考方案'}
{task_context_block}
"""

    try:
        llm = _get_llm_instance(llm_config)
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=message),
        ])
        return response.content if hasattr(response, "content") else str(response)
    except Exception as e:
        logger.warning("AI 导师调用失败（%s），返回通用提示。", e)
        return (
            "AI 导师暂时无法连接到模型服务。请检查「设置」中的 API Key 与网络连接，"
            "或稍后重试；若你的模型额度已用尽，需要先在服务商控制台恢复额度。"
        )
