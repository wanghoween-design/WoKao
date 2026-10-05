"""wokao.agents.planner — 内容生成（LLM）与确定性排程引擎的编排管线。

第一性原则：
- LLM 只负责「内容」：任务标题、类型、量化指标、建议时长与目标周次；
- 「结构」由 wokao.scheduler.engine 确定性求解：容量约束、冲突消解、考试日倒排锚点；
- 联网检索失败 / LLM 失败 / JSON 损坏，任何一层故障都降级为兜底内容池，
  最终方案永远可产出（fail-open 到确定性内核）。

本模块是显式顺序管线：retrieval → generate → compose。
线性流程无需状态图运行时（原 LangGraph 单目标图为死代码、HITL 为空转，已移除）。
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from wokao.agents.parser import extract_json_safely
from wokao.agents.prompts import build_fused_prompt_text, current_datetime_raw
from wokao.config import get_openai_config
from wokao.scheduler.engine import build_fused_schedule, fused_to_markdown, normalize_llm_tracks

logger = logging.getLogger(__name__)


def _get_llm_instance(llm_config: Optional[Dict[str, Any]] = None) -> ChatOpenAI:
    """按优先级实例化 ChatOpenAI（用户自定义配置优先，否则回退系统全局配置）。"""
    if llm_config and llm_config.get("api_key"):
        model_name = llm_config.get("model_name") or "gpt-4o-mini"
        api_key = llm_config.get("api_key")
        base_url = (llm_config.get("base_url") or "").strip() or None
        kwargs: Dict[str, Any] = {
            "model": model_name,
            "api_key": api_key,
            "temperature": 0.3,
        }
        if base_url:
            kwargs["base_url"] = base_url
        return ChatOpenAI(**kwargs)

    params: Dict[str, str] = get_openai_config()
    kwargs = {
        "model": params.get("model", "gpt-4o-mini"),
        "api_key": params.get("api_key", ""),
        "temperature": 0.3,
    }
    if params.get("base_url"):
        kwargs["base_url"] = params["base_url"]
    return ChatOpenAI(**kwargs)


# ---------------------------------------------------------------------------
# 节点一：联网考情检索（失败静默降级，绝不阻断主流程）
# ---------------------------------------------------------------------------

_PHD_KEYWORDS = ("申博", "博士")
_MASTER_KEYWORDS = ("考研", "硕士")


def _build_policy_query(goals_data: List[Dict[str, Any]]) -> Optional[str]:
    """仅为申博/考研类目标构造政策检索 query；其余目标无需联网。"""
    year = datetime.now().year
    parts: List[str] = []
    for g in goals_data:
        name = str(g.get("exam_name") or "")
        target = str(g.get("target_info") or "")
        if any(k in name for k in _PHD_KEYWORDS):
            parts.append(f"{target or name} {year} 博士招生简章 申请考核制 材料清单 时间")
        elif any(k in name for k in _MASTER_KEYWORDS):
            parts.append(f"{target or name} {year} 硕士招生简章 考试大纲 报名时间")
    query = " ".join(part for part in parts if part)
    return query[:200] or None


def fused_retrieval_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """搜索优先的招生政策检索；任何异常都降级为空结果。"""
    empty = {"web_sources": [], "retrieved_policy": ""}
    if not state.get("use_web_search", False):
        return empty
    query = _build_policy_query(state.get("goals_data") or [])
    if not query:
        return empty

    try:
        from wokao.services.policy_search import search_and_fetch

        data = search_and_fetch(query, top_k=3)          # 正确签名：search_and_fetch(query, top_k)
        sources = data.get("sources") or []              # 返回值为 dict：{query, sources, combined_text}
    except Exception as exc:
        logger.warning("联网检索失败，已降级为离线排程：%s", exc)
        return empty

    web_sources: List[Dict[str, str]] = [
        {"title": str(s.get("title") or ""), "url": str(s.get("url") or "")}
        for s in sources
        if isinstance(s, dict)
    ]
    snippets: List[str] = []
    for s in sources[:3]:
        if not isinstance(s, dict):
            continue
        body = str(s.get("content") or s.get("snippet") or "").strip()
        if body:
            snippets.append(f"【来源：{s.get('title') or '网页'}】\n{body[:800]}")

    return {
        "web_sources": web_sources,
        "retrieved_policy": "\n\n".join(snippets)[:6000],
    }


# ---------------------------------------------------------------------------
# 节点二：LLM 内容池生成（只产内容，不产时刻表）
# ---------------------------------------------------------------------------

def fused_generate_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """调用 LLM 为各轨道生成任务内容池；解析失败返回空 dict 由兜底接管。"""
    raw_text = ""
    llm_raw_json: Dict[str, Any] = {}
    llm_error = ""
    try:
        llm = _get_llm_instance(state.get("llm_config"))
        prompt = build_fused_prompt_text(
            goals_data=state.get("goals_data") or [],
            daily_hours=float(state.get("daily_hours") or 4.0),
            user_feedback=(state.get("user_feedback") or "").strip(),
            now_str=state.get("now_str") or current_datetime_raw(),
            retrieved_policy=state.get("retrieved_policy") or "",
        )
        resp = llm.invoke([
            SystemMessage(content="你是一名顶尖备考统筹规划师，擅长为多目标考生设计分阶段、可量化的任务内容池，并严格按给定 JSON 结构输出。"),
            HumanMessage(content=prompt),
        ])
        raw_text = resp.content if hasattr(resp, "content") else str(resp)
        parsed = extract_json_safely(raw_text)
        if isinstance(parsed, dict):
            llm_raw_json = parsed
    except Exception as exc:
        llm_error = str(exc)
        logger.warning("LLM 内容生成失败，将使用确定性兜底内容池：%s", exc)

    return {
        "llm_raw_json": llm_raw_json,
        "llm_error": llm_error,
        "generated_markdown": raw_text,
    }


# ---------------------------------------------------------------------------
# 节点三：归一化校验 + 引擎落位（唯一拥有时刻表决定权的环节）
# ---------------------------------------------------------------------------

def fused_compose_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """归一化 LLM 内容池并交由确定性引擎落位；输出最终 fused_json 契约。"""
    goals_data = state.get("goals_data") or []
    names = [str(g.get("exam_name") or "") for g in goals_data]
    pools = normalize_llm_tracks((state.get("llm_raw_json") or {}).get("tracks"), goals_data)

    fused = build_fused_schedule(
        goals_data=goals_data,
        pools_by_name=pools,
        daily_hours=float(state.get("daily_hours") or 4.0),
        user_feedback=(state.get("user_feedback") or ""),
    )
    markdown = fused_to_markdown(fused)

    return {
        "fused_json": fused,
        "generated_markdown": markdown,
        "exam_summary": " + ".join(n for n in names if n) or "多目标备考",
        "is_fused": True,
    }


def run_fused_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """多目标融合备考规划管线主入口（顺序执行三个节点）。"""
    result = dict(state)
    result.update(fused_retrieval_node(result))
    result.update(fused_generate_node(result))
    result.update(fused_compose_node(result))
    return result
