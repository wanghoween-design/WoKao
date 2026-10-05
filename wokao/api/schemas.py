"""wokao.api.schemas — API 请求与响应 Pydantic 数据契约。"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    username: str = Field(min_length=1, max_length=32)
    password: str = Field(min_length=6, max_length=128)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=32)
    password: str = Field(min_length=6, max_length=128)


class GoalItem(BaseModel):
    exam_name: str = Field(min_length=1, max_length=100)
    target_info: Optional[str] = Field(default="", max_length=2000)


class PlanGenerateRequest(BaseModel):
    goals: List[GoalItem] = Field(min_length=1, max_length=5)
    daily_hours: float = Field(default=4.0, ge=0.5, le=16.0)
    user_feedback: Optional[str] = Field(default="", max_length=2000)
    use_web_search: bool = True


class PlanUpdateRequest(BaseModel):
    user_feedback: Optional[str] = Field(default=None, max_length=2000)
    target_info: Optional[str] = Field(default=None, max_length=2000)
    daily_hours: Optional[float] = Field(default=None, ge=0.5, le=16.0)
    title: Optional[str] = Field(default=None, min_length=1, max_length=100)


class ScheduleUpdateRequest(BaseModel):
    schedule_json: str = Field(min_length=1, max_length=2_000_000)


class SearchExamInfoRequest(BaseModel):
    exam_type: str = Field(min_length=1, max_length=100)
    school: Optional[str] = Field(default="", max_length=200)
    major: Optional[str] = Field(default="", max_length=200)
    query: Optional[str] = Field(default="", max_length=500)


class ResumeRequest(BaseModel):
    resume_text: str = Field(max_length=100_000)


class UserProfileUpdateRequest(BaseModel):
    nickname: Optional[str] = Field(default="", max_length=64)
    birthday: Optional[str] = Field(default="", max_length=32)
    school: Optional[str] = Field(default="", max_length=128)
    major: Optional[str] = Field(default="", max_length=128)
    current_plan: Optional[str] = Field(default="", max_length=128)
    target_degree: Optional[str] = Field(default="", max_length=128)
    phone: Optional[str] = Field(default="", max_length=32)
    bio: Optional[str] = Field(default="", max_length=2000)
    resume_text: Optional[str] = Field(default="", max_length=100_000)


class UserLLMConfigRequest(BaseModel):
    name: Optional[str] = Field(default="", max_length=64)
    provider: str = Field(default="custom", max_length=50)
    model_name: str = Field(min_length=1, max_length=200)
    api_key: str = Field(min_length=1, max_length=500)
    base_url: Optional[str] = Field(default="", max_length=500)
    is_active: int = Field(default=1, ge=0, le=1)


class LLMConfigActivateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=64)


class TestLLMConfigRequest(BaseModel):
    provider: str = Field(default="custom", max_length=50)
    model_name: str = Field(min_length=1, max_length=200)
    api_key: str = Field(max_length=500)
    base_url: Optional[str] = Field(default="", max_length=500)


class AgentCoachChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    active_task: Optional[Dict[str, Any]] = None
    active_track_name: Optional[str] = Field(default="", max_length=200)
    plan_title: Optional[str] = Field(default="", max_length=200)


AgentCoachChatRequest.model_rebuild()
