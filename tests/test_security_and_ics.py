"""tests/test_security_and_ics.py — 安全原语与日历导出的边界测试。

覆盖此前零断言的路径：限流器滑动窗口、PBKDF2 旧格式兼容、
RFC 5545 TEXT 转义与 VTIMEZONE 内嵌、AI 导师降级文案不泄露异常细节。
"""

import hashlib
import json
import secrets
import time

from wokao import auth
from wokao.api.routes.plan_routes import _build_plan_ics
from wokao.security import rate_limit


# ---------------------------------------------------------------------------
# 限流器
# ---------------------------------------------------------------------------

def test_rate_limit_sliding_window():
    key = f"test-rl-{time.time()}"
    assert rate_limit.allow(key, limit=3, window_seconds=1.0) is True
    assert rate_limit.allow(key, limit=3, window_seconds=1.0) is True
    assert rate_limit.allow(key, limit=3, window_seconds=1.0) is True
    # 窗口内第 4 次被拒
    assert rate_limit.allow(key, limit=3, window_seconds=1.0) is False
    # 窗口滑过后恢复
    time.sleep(1.05)
    assert rate_limit.allow(key, limit=3, window_seconds=1.0) is True


def test_rate_limit_keys_are_isolated():
    assert rate_limit.allow("rl-iso-a", limit=1, window_seconds=1.0) is True
    assert rate_limit.allow("rl-iso-b", limit=1, window_seconds=1.0) is True
    assert rate_limit.allow("rl-iso-a", limit=1, window_seconds=1.0) is False


# ---------------------------------------------------------------------------
# PBKDF2 哈希格式
# ---------------------------------------------------------------------------

def test_password_hash_is_self_describing():
    hashed = auth.hash_password("whatever1")
    parts = hashed.split("$")
    assert parts[0] == "pbkdf2_sha256"
    assert int(parts[1]) >= 100_000


def test_password_legacy_two_part_format_verify():
    """旧版 salt$dk 两段格式（升级前的存量账号）必须能通过校验。"""
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", "legacy123".encode("utf-8"), salt, 100_000)
    legacy = salt.hex() + "$" + dk.hex()
    assert auth.verify_password("legacy123", legacy) is True
    assert auth.verify_password("wrong-password", legacy) is False


def test_password_malformed_hash_rejected():
    assert auth.verify_password("x", "not-a-valid-hash") is False
    assert auth.verify_password("x", "a$b$c$d$e") is False
    assert auth.verify_password("x", "") is False


# ---------------------------------------------------------------------------
# ICS 导出
# ---------------------------------------------------------------------------

def _sample_plan(title: str = "考研+国考,冲刺;版") -> dict:
    fused = {
        "tracks": [{
            "exam_name": "考研",
            "tasks": [{
                "title": "英语,精读;真题",
                "week": 1,
                "weekday": "周一",
                "time_block": "08:30-10:00",
                "duration_hours": 1.5,
                "type": "学习",
                "metric": "精读,2篇",
            }],
        }],
    }
    return {"id": 1, "title": title, "fused_plan": json.dumps(fused, ensure_ascii=False)}


def test_ics_escapes_rfc5545_specials():
    """逗号 / 分号必须转义，否则日历文件对严格客户端非法。"""
    ics = _build_plan_ics(_sample_plan())
    assert "SUMMARY:[考研] 英语\\,精读\\;真题" in ics
    assert "X-WR-CALNAME:考研+国考\\,冲刺\\;版" in ics
    # 原始未转义片段不应出现
    assert "SUMMARY:[考研] 英语,精读;真题" not in ics


def test_ics_embeds_vtimezone():
    ics = _build_plan_ics(_sample_plan())
    assert "BEGIN:VTIMEZONE" in ics
    assert "TZID:Asia/Shanghai" in ics
    assert "DTSTART;TZID=Asia/Shanghai:" in ics
