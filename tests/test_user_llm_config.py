import json
import time
import pytest
from fastapi.testclient import TestClient
from server import app
from wokao.db import crud as database


client = TestClient(app)


def test_user_llm_config_crud_and_isolation():
    # 1. Register User A
    ts = int(time.time() * 1000)
    user_a_name = f"llm_user_a_{ts}"
    resp_a = client.post("/api/auth/register", json={"username": user_a_name, "password": "password123"})
    assert resp_a.status_code == 200
    token_a = resp_a.json()["token"]
    user_a_id = resp_a.json()["user_id"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # 2. Register User B
    user_b_name = f"llm_user_b_{ts}"
    resp_b = client.post("/api/auth/register", json={"username": user_b_name, "password": "password123"})
    assert resp_b.status_code == 200
    token_b = resp_b.json()["token"]
    user_b_id = resp_b.json()["user_id"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 3. User A starts with no custom LLM config
    cfg_a_init = client.get("/api/user/llm_config", headers=headers_a)
    assert cfg_a_init.status_code == 200
    assert cfg_a_init.json()["configured"] is False

    # 4. User A saves a custom DeepSeek config
    save_resp_a = client.post(
        "/api/user/llm_config",
        headers=headers_a,
        json={
            "provider": "deepseek",
            "model_name": "deepseek-chat",
            "api_key": "sk-user-a-secret-key-12345678",
            "base_url": "https://api.deepseek.com/v1",
            "is_active": 1
        }
    )
    assert save_resp_a.status_code == 200
    assert save_resp_a.json()["status"] == "ok"

    # 5. Verify User A gets masked API key
    cfg_a = client.get("/api/user/llm_config", headers=headers_a)
    assert cfg_a.status_code == 200
    assert cfg_a.json()["configured"] is True
    config_data_a = cfg_a.json()["config"]
    assert config_data_a["provider"] == "deepseek"
    assert config_data_a["model_name"] == "deepseek-chat"
    assert config_data_a["base_url"] == "https://api.deepseek.com/v1"
    assert config_data_a["has_key"] is True
    assert "sk-" in config_data_a["api_key_masked"]
    assert "secret" not in config_data_a["api_key_masked"]  # masked!

    # 6. CRITICAL SECURITY CHECK: User B MUST NOT see User A's config!
    cfg_b = client.get("/api/user/llm_config", headers=headers_b)
    assert cfg_b.status_code == 200
    assert cfg_b.json()["configured"] is False  # User B is completely isolated!

    # Direct database check for strict physical isolation
    db_cfg_a = database.get_user_llm_config(user_a_id)
    assert db_cfg_a is not None
    assert db_cfg_a["api_key"] == "sk-user-a-secret-key-12345678"
    assert db_cfg_a["model_name"] == "deepseek-chat"

    db_cfg_b = database.get_user_llm_config(user_b_id)
    assert db_cfg_b is None  # Nothing in DB for user B

    # 7. User A deletes their config -> falls back to system default
    del_resp_a = client.delete("/api/user/llm_config", headers=headers_a)
    assert del_resp_a.status_code == 200
    assert del_resp_a.json()["status"] == "ok"

    cfg_a_after = client.get("/api/user/llm_config", headers=headers_a)
    assert cfg_a_after.status_code == 200
    assert cfg_a_after.json()["configured"] is False
    assert database.get_user_llm_config(user_a_id) is None


def test_user_llm_test_endpoint_validation():
    ts = int(time.time() * 1000)
    user_name = f"llm_test_user_{ts}"
    resp = client.post("/api/auth/register", json={"username": user_name, "password": "password123"})
    token = resp.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Empty API key should fail
    bad_resp = client.post(
        "/api/user/llm_config/test",
        headers=headers,
        json={"provider": "custom", "model_name": "gpt-4o-mini", "api_key": "", "base_url": ""}
    )
    assert bad_resp.status_code == 400

    # Invalid connection URL should return friendly error json (not unhandled 500)
    bad_conn = client.post(
        "/api/user/llm_config/test",
        headers=headers,
        json={
            "provider": "custom",
            "model_name": "gpt-4o-mini",
            "api_key": "sk-fake-key",
            "base_url": "http://127.0.0.1:9999/v1" # Non-existent port
        }
    )
    assert bad_conn.status_code == 400
    assert bad_conn.json()["success"] is False
    assert "连接失败" in bad_conn.json()["msg"]
