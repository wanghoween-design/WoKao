"""tests/test_api_endpoints.py — 集成测试 API 接口与 .ics / .md 导出。"""

import time
from fastapi.testclient import TestClient
from server import app
from wokao.db import crud as database

client = TestClient(app)


def test_api_now():
    res = client.get("/api/now")
    assert res.status_code == 200
    data = res.json()
    assert "date" in data
    assert "year" in data
    assert "weekday" in data


def test_api_exams():
    res = client.get("/api/exams")
    assert res.status_code == 200
    data = res.json()
    assert "categories" in data
    assert "exams" in data
    assert len(data["exams"]) >= 18
    # 验证关键富字段
    sample = data["exams"][0]
    assert "annual_period" in sample
    assert "official_website" in sample
    assert "subjects_detail" in sample


def test_auth_and_plan_lifecycle_and_export():
    unique_name = f"api_user_{int(time.time()*1000)}"

    # 1. 注册
    reg_res = client.post("/api/auth/register", json={"username": unique_name, "password": "password666"})
    assert reg_res.status_code == 200
    token = reg_res.json()["token"]
    user_id = reg_res.json()["user_id"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. 当前用户 me
    me_res = client.get("/api/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["username"] == unique_name

    # 3. 登录
    login_res = client.post("/api/auth/login", json={"username": unique_name, "password": "password666"})
    assert login_res.status_code == 200

    # 4. 创建模拟融合计划
    sample_fused = {
        "title": "测试双轨融合方案",
        "summary": "12周冲刺",
        "horizon_weeks": 12,
        "tracks": [
            {
                "exam_name": "考研",
                "key_dates": "12月下旬初试",
                "tasks": [
                    {
                        "title": "英语真题研读",
                        "week": 1,
                        "weekday": "周一",
                        "time_block": "08:30-10:00",
                        "duration_hours": 1.5,
                        "type": "学习",
                        "metric": "精读2篇",
                        "status": "todo"
                    }
                ]
            }
        ]
    }
    import json
    plan_id = database.save_user_plan(
        user_id=user_id,
        username=unique_name,
        exam_name="考研 + 考公",
        target_info="985 + 省直",
        daily_hours=4.0,
        user_feedback="",
        generated_plan="# 测试 Markdown 全文",
        title="测试双轨方案",
        is_fused=True,
        fused_plan=json.dumps(sample_fused, ensure_ascii=False)
    )

    # 5. 读取列表与单条
    list_res = client.get("/api/plans", headers=headers)
    assert list_res.status_code == 200
    assert len(list_res.json()["plans"]) == 1

    detail_res = client.get(f"/api/plans/{plan_id}", headers=headers)
    assert detail_res.status_code == 200
    assert detail_res.json()["plan"]["title"] == "测试双轨方案"

    # 6. 测试 .ics 日历导出
    ics_res = client.get(f"/api/plans/{plan_id}/export.ics", headers=headers)
    assert ics_res.status_code == 200
    assert "text/calendar" in ics_res.headers.get("content-type", "")
    ics_text = ics_res.text
    assert "BEGIN:VCALENDAR" in ics_text
    assert "BEGIN:VEVENT" in ics_text
    assert "英语真题研读" in ics_text
    assert "END:VCALENDAR" in ics_text

    # 7. 测试 .md 导出
    md_res = client.get(f"/api/plans/{plan_id}/export.md", headers=headers)
    assert md_res.status_code == 200
    assert "测试 Markdown 全文" in md_res.text

    # 8. 删除
    del_res = client.delete(f"/api/plans/{plan_id}", headers=headers)
    assert del_res.status_code == 200
