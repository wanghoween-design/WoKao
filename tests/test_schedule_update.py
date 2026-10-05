import json
import time
import pytest
from fastapi.testclient import TestClient
from server import app
from wokao.db import crud as database


client = TestClient(app)


def test_schedule_update_and_export_consistency():
    # 1. Register test user
    username = f"sched_user_{int(time.time() * 1000)}"
    reg_resp = client.post("/api/auth/register", json={"username": username, "password": "password123"})
    assert reg_resp.status_code == 200
    token = reg_resp.json()["token"]
    user_id = reg_resp.json()["user_id"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Create a dummy fused plan
    initial_fused = {
        "title": "多轨备考融合方案",
        "horizon_weeks": 12,
        "tracks": [
            {
                "exam_name": "全国硕士研究生统一招生考试（考研）",
                "key_dates": "12月下旬初试",
                "tasks": [
                    {
                        "week": 1,
                        "weekday": "周一",
                        "time_block": "08:30-10:30",
                        "title": "高等数学基础概念梳理",
                        "metric": "完成第一章例题",
                        "duration_hours": 2.0,
                        "type": "study",
                        "status": "todo"
                    }
                ]
            }
        ]
    }

    plan_id = database.save_user_plan(
        user_id=user_id,
        username=username,
        exam_name="考研",
        title="可编辑日程测试方案",
        target_info="985 计算机",
        daily_hours=4.0,
        user_feedback="",
        generated_plan="# 考研复习计划大纲\n\n- 第1周：高等数学基础概念",
        is_fused=1,
        fused_plan=json.dumps(initial_fused, ensure_ascii=False),
        goals_json=json.dumps([{"exam_name": "考研", "target_info": "985"}], ensure_ascii=False)
    )

    # 3. Update the schedule with modified tasks (simulating ScheduleEditor.vue save)
    modified_fused = {
        "title": "多轨备考融合方案（用户自定义修改版）",
        "horizon_weeks": 12,
        "tracks": [
            {
                "exam_name": "全国硕士研究生统一招生考试（考研）",
                "key_dates": "12月下旬初试",
                "tasks": [
                    {
                        "week": 1,
                        "weekday": "周一",
                        "time_block": "19:00-21:30", # Changed from 08:30-10:30
                        "title": "高等数学极限与连续性突破", # Modified title
                        "metric": "精刷15道真题",
                        "duration_hours": 2.5,
                        "type": "study",
                        "status": "todo"
                    },
                    {
                        "week": 1,
                        "weekday": "周二",
                        "time_block": "20:00-21:30", # Added new task
                        "title": "考研英语长难句精读",
                        "metric": "拆解5篇外刊长难句",
                        "duration_hours": 1.5,
                        "type": "study",
                        "status": "todo"
                    }
                ]
            }
        ]
    }

    put_resp = client.put(
        f"/api/plans/{plan_id}/schedule",
        headers=headers,
        json={"schedule_json": json.dumps(modified_fused, ensure_ascii=False)}
    )
    assert put_resp.status_code == 200
    assert put_resp.json()["status"] == "ok"

    # 4. Verify GET /api/plans/{plan_id} returns the updated schedule
    get_resp = client.get(f"/api/plans/{plan_id}", headers=headers)
    assert get_resp.status_code == 200
    fetched_plan = get_resp.json()["plan"]
    assert "高等数学极限与连续性突破" in fetched_plan["fused_plan"]
    assert "考研英语长难句精读" in fetched_plan["fused_plan"]
    assert "19:00-21:30" in fetched_plan["fused_plan"]

    # 5. Verify ICS export reflects the new time block and modified tasks
    ics_resp = client.get(f"/api/plans/{plan_id}/export.ics", headers=headers)
    assert ics_resp.status_code == 200
    assert "text/calendar" in ics_resp.headers["content-type"]
    ics_text = ics_resp.text
    assert "高等数学极限与连续性突破" in ics_text
    assert "考研英语长难句精读" in ics_text

    # 6. Test invalid schedule JSON
    bad_resp = client.put(
        f"/api/plans/{plan_id}/schedule",
        headers=headers,
        json={"schedule_json": "{not valid json"}
    )
    assert bad_resp.status_code == 400
