"""wokao.api.routes.coach_routes — AI 伴学导师实时答疑与日程动态微调。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from wokao.agents.coach import chat_with_coach
from wokao.api.dependencies import get_current_user, get_effective_user_llm_config
from wokao.api.schemas import AgentCoachChatRequest

router = APIRouter(tags=["AI Study Coach"])


@router.post("/api/agent/chat")
def api_coach_chat(req: AgentCoachChatRequest, user: dict = Depends(get_current_user)):
    """AI 伴学导师对话接口（同步处理：LLM 调用走线程池，避免阻塞事件循环）。"""
    if not req.message or not req.message.strip():
        raise HTTPException(status_code=400, detail="消息内容不能为空")

    user_llm = get_effective_user_llm_config(user["user_id"])
    reply = chat_with_coach(
        message=req.message.strip(),
        active_task=req.active_task,
        active_track_name=req.active_track_name or "",
        plan_title=req.plan_title or "",
        llm_config=user_llm,
    )
    return {"reply": reply}
