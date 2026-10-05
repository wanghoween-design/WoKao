import pytest
from unittest.mock import MagicMock, patch
from wokao.services.search_providers import SearchResult, get_trust_level, DuckDuckGoProvider, BingWebProvider, multi_search
from wokao.services.knowledge_retriever import (
    SourceDocument,
    ExamInfoField,
    ExamKnowledge,
    build_query_key,
    cross_validate,
    check_cache,
    save_to_cache,
    fetch_page_content,
    retrieve_exam_knowledge,
)


def test_trust_level_classification():
    assert get_trust_level("https://yz.chsi.com.cn/zsml/queryAction.do") == "S"
    assert get_trust_level("https://admission.pku.edu.cn/notice") == "S"
    assert get_trust_level("https://www.zhihu.com/question/123456") == "A"
    assert get_trust_level("https://www.kaoyan.com/school/pku") == "A"
    assert get_trust_level("https://example.com/some/blog") == "B"


def test_build_query_key():
    key = build_query_key("考研", "北京大学", "计算机科学与技术")
    assert key == "考研_北京大学_计算机科学与技术"
    
    key_empty = build_query_key("国考", "", "")
    assert key_empty == "国考"


def test_cross_validation_rules():
    doc1 = SourceDocument(id=1, url="https://yz.chsi.com.cn", title="研招网", content="科目：政治,英语一,数学一,408", trust_level="S")
    doc2 = SourceDocument(id=2, url="https://pku.edu.cn", title="北大研招", content="科目：101,201,301,408", trust_level="S")
    doc3 = SourceDocument(id=3, url="https://blog.example.com", title="个人经验", content="参考书目...", trust_level="B")

    knowledge = ExamKnowledge(
        exam_type="考研",
        school="北京大学",
        major="计算机科学与技术",
        subjects=ExamInfoField(value="政治、英语一、数学一、408", source_ids=[1, 2]),
        reference_books=ExamInfoField(value="某参考书", source_ids=[3]),
        score_line=ExamInfoField(value="360", source_ids=[1]),
        registration_time=ExamInfoField(value=None, source_ids=[]),
        sources=[doc1, doc2, doc3]
    )

    validated = cross_validate(knowledge)
    assert validated.subjects.confidence == "high"      # 2 sources
    assert validated.reference_books.confidence == "low" # 1 source, trust level B
    assert validated.score_line.confidence == "medium"   # 1 source, trust level S
    assert validated.registration_time.confidence == "not_found" # 0 sources


def test_cache_and_retrieval_flow():
    test_key = "test_exam_type_school_major_for_pytest"
    doc = SourceDocument(id=1, url="https://yz.chsi.com.cn", title="官方", content="内容", trust_level="S")
    knowledge = ExamKnowledge(
        exam_type="测试考",
        school="测试校",
        major="测试专业",
        query_key=test_key,
        subjects=ExamInfoField(value="测试科目", source_ids=[1], confidence="medium"),
        sources=[doc],
    )

    save_to_cache(knowledge)
    cached = check_cache(test_key)
    assert cached is not None
    assert cached.exam_type == "测试考"
    assert cached.subjects.value == "测试科目"
    assert cached.subjects.confidence == "medium"
    assert len(cached.sources) == 1
