"""wokao.services — 搜索引擎适配、考情知识检索与招生政策检索服务。"""
from wokao.services.search_providers import (
    SearchResult,
    DuckDuckGoProvider,
    TavilyProvider,
    BingWebProvider,
    get_trust_level,
    get_provider,
    multi_search,
)
from wokao.services.knowledge_retriever import (
    SourceDocument,
    ExamInfoField,
    ExamKnowledge,
    build_query_key,
    check_cache,
    retrieve_exam_knowledge,
)

__all__ = [
    "SearchResult",
    "DuckDuckGoProvider",
    "TavilyProvider",
    "BingWebProvider",
    "get_trust_level",
    "get_provider",
    "multi_search",
    "SourceDocument",
    "ExamInfoField",
    "ExamKnowledge",
    "build_query_key",
    "check_cache",
    "retrieve_exam_knowledge",
]
