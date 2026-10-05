"""tests/test_auth_and_db.py — 测试用户密码哈希、会话过期机制与 SQLite CRUD。"""

import pytest
import time
from wokao import auth
from wokao.db import crud as database


def test_password_hash_and_verify():
    pwd = "MySecretPassword123"
    hashed = auth.hash_password(pwd)
    assert hashed != pwd
    assert "$" in hashed
    assert auth.verify_password(pwd, hashed) is True
    assert auth.verify_password("WrongPassword", hashed) is False


def test_user_registration_and_auth():
    unique_user = f"tester_{int(time.time()*1000)}"
    user_id = auth.register_user(unique_user, "password123")
    assert user_id > 0

    # 重复注册测试
    with pytest.raises(ValueError, match="已被注册"):
        auth.register_user(unique_user, "anotherpwd")

    # 登录测试
    auth_id = auth.authenticate(unique_user, "password123")
    assert auth_id == user_id

    # 错误密码
    assert auth.authenticate(unique_user, "wrong") is None


def test_session_expiration():
    unique_user = f"sess_user_{int(time.time()*1000)}"
    user_id = auth.register_user(unique_user, "password123")

    # 正常 7 天会话
    token = database.create_session(user_id, expire_days=7)
    user_row = database.get_user_by_token(token)
    assert user_row is not None
    assert user_row["id"] == user_id

    # 已过期会话（-1 天）
    expired_token = database.create_session(user_id, expire_days=-1)
    expired_user = database.get_user_by_token(expired_token)
    assert expired_user is None

    # 清理过期会话
    cleaned_count = database.clean_expired_sessions()
    assert cleaned_count >= 1

    # 注销测试
    database.delete_session(token)
    assert database.get_user_by_token(token) is None


def test_user_plans_crud():
    unique_user = f"plan_user_{int(time.time()*1000)}"
    user_id = auth.register_user(unique_user, "password123")

    plan_id = database.save_user_plan(
        user_id=user_id,
        username=unique_user,
        exam_name="考研 + 考公",
        target_info="985 408 + 省直",
        daily_hours=4.5,
        user_feedback="周末不学",
        generated_plan="# 备考方案",
        title="双轨方案",
        is_fused=True,
        fused_plan='{"tracks":[]}',
    )
    assert plan_id > 0

    # 读取
    p = database.get_plan_by_id(plan_id)
    assert p is not None
    assert p["title"] == "双轨方案"
    assert p["daily_hours"] == 4.5
    assert p["is_fused"] is True

    # 列表
    plans = database.get_user_plans(user_id)
    assert len(plans) == 1
    assert plans[0]["id"] == plan_id

    # 更新
    ok = database.update_plan(plan_id, user_id, title="新双轨方案", daily_hours=5.0)
    assert ok is True
    updated_p = database.get_plan_by_id(plan_id)
    assert updated_p["title"] == "新双轨方案"
    assert updated_p["daily_hours"] == 5.0

    # 删除
    del_ok = database.delete_plan(plan_id, user_id)
    assert del_ok is True
    assert database.get_plan_by_id(plan_id) is None
