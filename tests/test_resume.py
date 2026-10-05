import json
import pytest
from fastapi.testclient import TestClient
from server import app
from wokao.db import crud as database


client = TestClient(app)


def test_resume_save_and_get():
    # 1. Register a test user
    import time
    username = f"resume_user_{int(time.time() * 1000)}"
    reg_resp = client.post("/api/auth/register", json={"username": username, "password": "password123"})
    assert reg_resp.status_code == 200
    token = reg_resp.json()["token"]
    user_id = reg_resp.json()["user_id"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Get profile initially (resume should be empty or null)
    prof_resp = client.get("/api/profile", headers=headers)
    assert prof_resp.status_code == 200
    assert prof_resp.json()["user_id"] == user_id
    assert prof_resp.json()["resume_text"] == ""

    # 3. Save resume text
    sample_resume = "教育背景：XX大学软件工程专业\n成绩：前10%\n获得奖项：国家奖学金\n意向目标：985高校计算机学硕"
    save_resp = client.post("/api/profile/resume", headers=headers, json={"resume_text": sample_resume})
    assert save_resp.status_code == 200
    assert save_resp.json()["status"] == "ok"

    # 4. Get profile again to verify persistence
    prof_resp2 = client.get("/api/profile", headers=headers)
    assert prof_resp2.status_code == 200
    assert prof_resp2.json()["resume_text"] == sample_resume

    # Direct database check
    db_resume = database.get_user_resume(user_id)
    assert db_resume == sample_resume
