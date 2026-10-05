"""wokao.services.knowledge_retriever — 搜索优先的考情信息检索与事实抽取管线。

核心原则：LLM 只做「生成搜索词」和「从搜索结果中提取信息」，
严禁使用 LLM 自身知识回答事实性问题。每条信息必须附带来源 URL。

与 policy_search 的分工：本模块负责交互式「考情深度检索」
（科目 / 分数线 / 参考书等结构化字段 + S/A/B 信任评级 + SQLite 缓存），
排程前的轻量招生政策快查见 policy_search（无 LLM 依赖）。
"""
from __future__ import annotations

import json
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional
import requests
from pydantic import BaseModel

logger = logging.getLogger(__name__)

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

from wokao.services.search_providers import SearchResult, get_trust_level, multi_search
from wokao.db import crud


class SourceDocument(BaseModel):
    id: int
    url: str
    title: str
    content: str
    trust_level: str


class ExamInfoField(BaseModel):
    value: Any = None
    source_ids: List[int] = []
    confidence: str = "not_found"
    conflict_versions: Optional[List[dict]] = None


class ExamKnowledge(BaseModel):
    exam_type: str
    school: Optional[str] = None
    major: Optional[str] = None
    subjects: ExamInfoField = ExamInfoField()
    reference_books: ExamInfoField = ExamInfoField()
    score_line: ExamInfoField = ExamInfoField()
    registration_time: ExamInfoField = ExamInfoField()
    exam_time: ExamInfoField = ExamInfoField()
    additional_info: dict = {}
    sources: List[SourceDocument] = []
    retrieved_at: str = ""
    query_key: str = ""


def build_query_key(exam_type: str, school: str = "", major: str = "") -> str:
    parts = [p for p in (exam_type, school, major) if p]
    return "_".join(parts)


def check_cache(query_key: str) -> Optional[ExamKnowledge]:
    """查询本地缓存，命中且未过期则返回 ExamKnowledge。"""
    try:
        cached_row = crud.get_cached_knowledge(query_key)
        if cached_row:
            data = cached_row.get("data_json", {})
            sources = cached_row.get("sources_json", [])
            if isinstance(data, str):
                data = json.loads(data)
            if isinstance(sources, str):
                sources = json.loads(sources)
            if isinstance(data, dict):
                if isinstance(sources, list) and not data.get("sources"):
                    data["sources"] = sources
                return ExamKnowledge(**data)
    except Exception as e:
        logger.warning("考情缓存查询失败：%s", e)
    return None


def generate_search_queries(
    user_intent: str,
    exam_type: str,
    school: str = "",
    major: str = "",
    llm_config: Optional[Dict[str, Any]] = None,
) -> List[str]:
    """调用 LLM 将用户意图拆解为多组搜索关键词。"""
    try:
        from wokao.agents.planner import _get_llm_instance
        from langchain_core.messages import HumanMessage, SystemMessage

        llm = _get_llm_instance(llm_config)
        prompt = f"""请针对以下考试信息生成 3-5 个不同角度的搜索关键词。
考试类型：{exam_type}
学校：{school}
专业：{major}
用户意图：{user_intent}

需要包含的角度（如果适用）：科目、参考书目、分数线、报名时间、经验分享。
注意：只生成搜索关键词，每行一个。不要回答任何事实性问题，不要提供额外说明。"""
        response = llm.invoke([
            SystemMessage(content="你是一个搜索关键词生成助手。只输出搜索关键词，每行一个，不要回答问题。"),
            HumanMessage(content=prompt),
        ])
        text = response.content if hasattr(response, "content") else str(response)
        queries = [line.strip("- *0123456789.、").strip() for line in text.split("\n") if line.strip() and len(line.strip()) > 2]
        if queries:
            return queries[:5]
    except Exception as e:
        logger.warning("LLM 生成搜索词失败，回退默认搜索词：%s", e)

    # Fallback 默认搜索词
    base = f"{school} {major} {exam_type}".strip()
    return [
        f"{base} 考试科目 招生简章",
        f"{base} 参考书目 考纲",
        f"{base} 录取分数线 复试线",
        f"{base} 报名时间 考试时间",
    ]


def _fetch_single_page(res: "SearchResult", max_chars_per_page: int) -> str:
    """抓取单个结果页正文；失败返回 snippet 兜底。"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }
    content = ""
    if not res.url.endswith(".pdf") and not res.url.endswith(".doc"):
        try:
            resp = requests.get(res.url, headers=headers, timeout=8)
            if resp.status_code == 200:
                resp.encoding = resp.apparent_encoding or "utf-8"
                html = resp.text
                if BeautifulSoup:
                    soup = BeautifulSoup(html, "html.parser")
                    for s in soup(["script", "style", "nav", "footer", "header", "noscript"]):
                        s.decompose()
                    text = soup.get_text(separator="\n")
                    lines = [line.strip() for line in text.splitlines() if line.strip()]
                    content = "\n".join(lines)
        except Exception:
            content = ""
    if not content or len(content) < 50:
        content = res.snippet
    return content[:max_chars_per_page]


def fetch_page_content(
    results: List[SearchResult],
    max_items: int = 8,
    max_chars_per_page: int = 3000,
) -> List[SourceDocument]:
    """并发抓取高可信度页面的主要文本内容（线程池，保持输入顺序与编号）。"""
    targets = list(results[:max_items])
    contents: List[str] = [""] * len(targets)

    if targets:
        workers = min(6, len(targets))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(_fetch_single_page, res, max_chars_per_page): i for i, res in enumerate(targets)}
            for future in as_completed(futures):
                idx = futures[future]
                try:
                    contents[idx] = future.result()
                except Exception:
                    contents[idx] = ""

    documents = []
    for idx, res in enumerate(targets):
        trust = get_trust_level(res.url)
        content = contents[idx] or res.snippet
        documents.append(
            SourceDocument(
                id=idx + 1,
                url=res.url,
                title=res.title or "网页结果",
                content=content,
                trust_level=trust,
            )
        )
    return documents


def extract_structured_info(
    documents: List[SourceDocument],
    exam_type: str,
    school: str = "",
    major: str = "",
    llm_config: Optional[Dict[str, Any]] = None,
) -> ExamKnowledge:
    """严格从检索到的文档内容中提取结构化考情信息。"""
    from wokao.agents.planner import _get_llm_instance
    from wokao.agents.parser import extract_json_safely
    from langchain_core.messages import HumanMessage, SystemMessage

    llm = _get_llm_instance(llm_config)

    docs_text = ""
    for doc in documents:
        docs_text += f"\n--- 文档 [{doc.id}] ({doc.title} - {doc.url}) ---\n{doc.content}\n"

    system_prompt = """你是一个严谨的考试信息提取助手。
你只能从下面提供的【参考文档】中提取信息。
【铁律】：
1. 严禁使用你自己的既有知识进行脑补或猜测。
2. 如果文档中未检索到某项信息，请将该字段的 value 设为 "未检索到"，source_ids 设为 []。
3. 如果提取到信息，必须在 source_ids 中填入提供该信息的文档编号（如 [1, 2]）。
4. 如果发现不同文档之间存在矛盾（例如报名时间或分数线不同），请在 conflict_versions 中记录不同版本的陈述及来源。
5. 请输出严格的 JSON 格式，包裹在 ```json 代码块中。"""

    user_prompt = f"""目标：{school} {major} {exam_type}

【参考文档】：
{docs_text}

请提取以下字段并按此 JSON 结构返回：
{{
  "subjects": {{ "value": "考试科目列表或说明", "source_ids": [1], "conflict_versions": null }},
  "reference_books": {{ "value": "参考书目列表", "source_ids": [1], "conflict_versions": null }},
  "score_line": {{ "value": "分数线信息", "source_ids": [1], "conflict_versions": null }},
  "registration_time": {{ "value": "报名时间", "source_ids": [1], "conflict_versions": null }},
  "exam_time": {{ "value": "考试时间", "source_ids": [1], "conflict_versions": null }}
}}"""

    try:
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ])
        raw_text = response.content if hasattr(response, "content") else str(response)
        parsed = extract_json_safely(raw_text)
        if not parsed:
            parsed = {}
    except Exception as e:
        logger.warning("结构化抽取失败：%s", e)
        parsed = {}

    def parse_field(name: str) -> ExamInfoField:
        data = parsed.get(name, {})
        if not isinstance(data, dict):
            return ExamInfoField(value="未检索到", source_ids=[], confidence="not_found")
        val = data.get("value")
        s_ids = data.get("source_ids", [])
        if not isinstance(s_ids, list):
            s_ids = []
        conflicts = data.get("conflict_versions")
        return ExamInfoField(
            value=val if val is not None else "未检索到",
            source_ids=s_ids,
            conflict_versions=conflicts if isinstance(conflicts, list) else None,
        )

    knowledge = ExamKnowledge(
        exam_type=exam_type,
        school=school,
        major=major,
        subjects=parse_field("subjects"),
        reference_books=parse_field("reference_books"),
        score_line=parse_field("score_line"),
        registration_time=parse_field("registration_time"),
        exam_time=parse_field("exam_time"),
        sources=documents,
        retrieved_at=time.strftime("%Y-%m-%d %H:%M:%S"),
        query_key=build_query_key(exam_type, school, major),
    )
    return knowledge


def cross_validate(knowledge: ExamKnowledge) -> ExamKnowledge:
    """根据来源数量与权威度交叉验证各字段置信度。"""
    source_map = {s.id: s for s in knowledge.sources}

    for field_name in ("subjects", "reference_books", "score_line", "registration_time", "exam_time"):
        field: ExamInfoField = getattr(knowledge, field_name)
        if field.conflict_versions:
            field.confidence = "conflict"
            continue

        if not field.source_ids or field.value in ("未检索到", None, ""):
            field.confidence = "not_found"
            continue

        if len(field.source_ids) >= 2:
            field.confidence = "high"
        elif len(field.source_ids) == 1:
            sid = field.source_ids[0]
            doc = source_map.get(sid)
            if doc and doc.trust_level == "S":
                field.confidence = "medium"
            else:
                field.confidence = "low"
        else:
            field.confidence = "not_found"

    return knowledge


def save_to_cache(knowledge: ExamKnowledge, expire_days: int = 30) -> None:
    """将检索与验证结果写入本地 SQLite 缓存。"""
    try:
        data_dict = knowledge.model_dump(exclude={"sources"})
        sources_list = [s.model_dump() for s in knowledge.sources]
        crud.save_knowledge_cache(
            query_key=knowledge.query_key,
            exam_type=knowledge.exam_type,
            school=knowledge.school or "",
            major=knowledge.major or "",
            data_json=data_dict,
            sources_json=sources_list,
            expire_days=expire_days,
        )
    except Exception as e:
        logger.warning("写入考情缓存失败：%s", e)


def retrieve_exam_knowledge(
    exam_type: str,
    school: str = "",
    major: str = "",
    user_query: str = "",
    force_refresh: bool = False,
    llm_config: Optional[Dict[str, Any]] = None,
) -> ExamKnowledge:
    """考情信息检索主入口：查缓存 → 多源搜索 → 正文抓取 → 结构化提取 → 交叉验证 → 缓存。"""
    query_key = build_query_key(exam_type, school, major)

    if not force_refresh:
        cached = check_cache(query_key)
        if cached:
            return cached

    queries = generate_search_queries(
        user_intent=user_query,
        exam_type=exam_type,
        school=school,
        major=major,
        llm_config=llm_config,
    )
    search_results = multi_search(queries, max_results_per_query=4)
    documents = fetch_page_content(search_results, max_items=6)
    knowledge = extract_structured_info(
        documents,
        exam_type=exam_type,
        school=school,
        major=major,
        llm_config=llm_config,
    )
    validated_knowledge = cross_validate(knowledge)
    save_to_cache(validated_knowledge)
    return validated_knowledge
