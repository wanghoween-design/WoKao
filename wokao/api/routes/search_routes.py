"""wokao.api.routes.search_routes — 考情知识检索与招生政策核验。"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from wokao.api.dependencies import get_current_user, get_effective_user_llm_config
from wokao.api.schemas import SearchExamInfoRequest
from wokao.services.knowledge_retriever import retrieve_exam_knowledge

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Exam Search & Retrieval"])


@router.post("/api/search_exam_info")
def api_search_exam_info(req: SearchExamInfoRequest, user: dict = Depends(get_current_user)):
    """搜索优先的考情信息检索（同步处理：LLM + 爬虫走线程池，避免阻塞事件循环）。"""
    try:
        user_llm = get_effective_user_llm_config(user["user_id"])
        knowledge = retrieve_exam_knowledge(
            exam_type=req.exam_type,
            school=req.school or "",
            major=req.major or "",
            user_query=req.query or "",
            llm_config=user_llm,
        )
        return knowledge.model_dump()
    except Exception as exc:
        logger.warning("考情检索失败（user=%s, exam=%s）：%s", user.get("username"), req.exam_type, exc)
        raise HTTPException(
            status_code=500,
            detail="考情信息检索失败：检索服务或模型暂时不可用，请稍后重试。",
        )
