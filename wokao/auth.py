"""wokao.auth — 本地轻量认证模块：密码哈希、校验与 Session 会话管理。"""
from __future__ import annotations

import hashlib
import secrets
from typing import Optional

from wokao.db import crud

# 默认 PBKDF2 迭代次数；新哈希把参数写入哈希串本身，未来调大不影响旧记录校验
_PBKDF2_ITERATIONS = 100_000


def hash_password(password: str) -> str:
    """返回 pbkdf2_sha256$<iterations>$<salt_hex>$<derived_hex>。"""
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${_PBKDF2_ITERATIONS}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """恒定时间比对，防范时序侧信道攻击；兼容旧版 <salt_hex>$<dk_hex> 两段格式。"""
    try:
        parts = stored.split("$")
        if len(parts) == 4 and parts[0] == "pbkdf2_sha256":
            iterations, salt_hex, dk_hex = int(parts[1]), parts[2], parts[3]
        elif len(parts) == 2:
            iterations, salt_hex, dk_hex = _PBKDF2_ITERATIONS, parts[0], parts[1]
        else:
            return False
        salt = bytes.fromhex(salt_hex)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        return secrets.compare_digest(dk.hex(), dk_hex)
    except Exception:
        return False


def register_user(username: str, password: str) -> int:
    """创建新考生账号，返回 user_id。"""
    username = (username or "").strip()
    if not username:
        raise ValueError("用户名不能为空")
    if len(username) > 32:
        raise ValueError("用户名过长（≤32 字）")
    if not password or len(password) < 6:
        raise ValueError("密码至少 6 位")
    if crud.get_user_by_username(username):
        raise ValueError("该用户名已被注册")
    return crud.create_user(username, hash_password(password))


def authenticate(username: str, password: str) -> Optional[int]:
    """校验凭证，成功返回 user_id，失败返回 None。"""
    username = (username or "").strip()
    user = crud.get_user_by_username(username)
    if not user:
        return None
    if not verify_password(password, user["password_hash"]):
        return None
    return int(user["id"])


def create_session(user_id: int) -> str:
    """为用户创建会话并返回令牌。"""
    return crud.create_session(user_id)


def get_current_user(token: Optional[str]) -> Optional[dict]:
    """按令牌获取当前用户；无效或过期返回 None。"""
    if not token:
        return None
    return crud.get_user_by_token(token)


def logout(token: Optional[str]) -> None:
    """注销指定会话。"""
    if token:
        crud.delete_session(token)
