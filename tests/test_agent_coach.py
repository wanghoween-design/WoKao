import time
import pytest
from fastapi.testclient import TestClient
from server import app
from wokao.db import crud as database

client = TestClient(app)


def test_agent_coach_chat_validation_and_context():
    ts = int(time.time() * 1000)
    username = f"coach_user_{ts}"
    resp = client.post("/api/auth/register", json={"username": username, "password": "password123"})
    token = resp.json()["token"]
    user_id = resp.json()["user_id"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Empty message should fail validation (422 or 400)
    res_bad = client.post(
        "/api/agent/chat",
        headers=headers,
        json={"message": "", "plan_id": None, "task_context": None}
    )
    assert res_bad.status_code in (400, 422)

    # 2. Unauthorized request should return 401
    res_unauth = client.post(
        "/api/agent/chat",
        json={"message": "你好", "plan_id": None}
    )
    assert res_unauth.status_code == 401

    # 3. Create a test plan for the user
    plan_id = database.save_user_plan(
        user_id=user_id,
        username=username,
        exam_name="考研 + 申博",
        target_info="目标吉林大学计算机",
        daily_hours=4.0,
        user_feedback="",
        generated_plan="# 备考方案",
        title="双轨备考计划",
        is_fused=True
    )

    # 4. 带任务上下文的请求载荷结构（前端契约）
    chat_payload = {
        "message": "请问当前任务的数据结构重点是什么？",
        "plan_id": plan_id,
        "task_context": {
            "title": "计算机专业课（数据结构树与图论）",
            "week": 1,
            "weekday": "周一",
            "time_block": "08:30-11:00",
            "metric": "完成树与图论思维导图及 20 道习题",
            "trackName": "申博"
        },
    }
    assert chat_payload["plan_id"] == plan_id


def test_coach_fallback_message_when_llm_fails(monkeypatch):
    """LLM 调用失败时返回通用提示，且不泄露原始异常细节。"""
    import wokao.agents.coach as coach_mod

    def _boom(*args, **kwargs):
        raise RuntimeError("no llm in tests: secret-endpoint-info")

    monkeypatch.setattr(coach_mod, "_get_llm_instance", _boom)
    reply = coach_mod.chat_with_coach("帮我出两道数据结构题", plan_title="测试方案")

    assert "暂时无法连接" in reply
    assert "RuntimeError" not in reply
    assert "secret-endpoint-info" not in reply
