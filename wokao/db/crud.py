"""wokao.db.crud — 考试大纲、用户、计划、知识缓存与 LLM 配置的数据库增删改查。"""
from __future__ import annotations

import json
import secrets
import sqlite3
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from wokao.db.session import get_connection
from wokao.security.crypto import decrypt_secret, encrypt_secret


def _loads(s: Optional[str], default: Any) -> Any:
    """安全反序列化 JSON 字段。"""
    if not s:
        return default
    try:
        return json.loads(s)
    except Exception:
        return default


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    """将 exams 行转为 API 友好字典。"""
    return {
        "id": row["id"],
        "category": row["category"],
        "exam_name": row["exam_name"],
        "annual_period": row["annual_period"] or "",
        "exam_time": row["exam_time"],
        "registration_time": row["registration_time"] or "",
        "official_website": row["official_website"] or "",
        "exam_subjects": _loads(row["exam_subjects"], []),
        "subjects_detail": _loads(row["subjects_detail"], []),
        "exam_format": _loads(row["exam_format"], []),
        "reference_materials": _loads(row["reference_materials"], []),
        "tips": _loads(row["tips"], []),
        "description": row["description"] or "",
    }


def get_all_exams() -> List[Dict[str, Any]]:
    """返回全部考试大纲数据。"""
    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM exams ORDER BY id ASC").fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


def get_exam_by_name(exam_name: str) -> Optional[Dict[str, Any]]:
    """按考试名称精确查询。"""
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM exams WHERE exam_name = ?", (exam_name,)).fetchone()
        return _row_to_dict(row) if row else None
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 用户与会话
# ---------------------------------------------------------------------------


def create_user(username: str, password_hash: str) -> int:
    """创建新用户，返回自增 ID。"""
    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, password_hash),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()


def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """按用户名查找用户。"""
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """按 ID 查找用户。"""
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (int(user_id),)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def create_session(user_id: int, expire_days: int = 7) -> str:
    """创建会话令牌（默认 7 天）。"""
    token: str = secrets.token_urlsafe(32)
    expires_at: str = (datetime.now() + timedelta(days=expire_days)).strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
            (token, int(user_id), expires_at),
        )
        conn.commit()
        return token
    finally:
        conn.close()


def get_user_by_token(token: str) -> Optional[Dict[str, Any]]:
    """按会话令牌取当前用户（带过期校验）。"""
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT u.* FROM users u
            JOIN sessions s ON s.user_id = u.id
            WHERE s.token = ? AND (s.expires_at IS NULL OR s.expires_at > datetime('now', 'localtime'))
            """,
            (token,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def clean_expired_sessions() -> int:
    """清理过期会话。"""
    conn = get_connection()
    try:
        cur = conn.execute("DELETE FROM sessions WHERE expires_at IS NOT NULL AND expires_at <= datetime('now', 'localtime')")
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()


def delete_session(token: str) -> None:
    """注销会话。"""
    conn = get_connection()
    try:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 计划管理
# ---------------------------------------------------------------------------


def _plan_row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "username": row["username"],
        "exam_name": row["exam_name"],
        "title": row["title"] or "",
        "target_info": row["target_info"] or "",
        "daily_hours": row["daily_hours"],
        "user_feedback": row["user_feedback"] or "",
        "generated_plan": row["generated_plan"] or "",
        "is_fused": bool(row["is_fused"]) if "is_fused" in row.keys() else False,
        "fused_plan": row["fused_plan"] or "" if "fused_plan" in row.keys() else "",
        "goals_json": row["goals_json"] or "" if "goals_json" in row.keys() else "",
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def save_user_plan(
    user_id: int,
    username: str,
    exam_name: str,
    target_info: str,
    daily_hours: float,
    user_feedback: str,
    generated_plan: str,
    title: str = "",
    is_fused: bool = False,
    fused_plan: str = "",
    goals_json: str = "",
) -> int:
    """保存用户备考计划。"""
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            INSERT INTO user_plans
                (user_id, username, exam_name, title, target_info, daily_hours, user_feedback,
                 generated_plan, is_fused, fused_plan, goals_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(user_id),
                username,
                exam_name,
                title or "",
                target_info,
                float(daily_hours),
                user_feedback,
                generated_plan,
                1 if is_fused else 0,
                fused_plan or "",
                goals_json or "",
            ),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()


def get_user_plans(user_id: int, limit: int = 100) -> List[Dict[str, Any]]:
    """查询指定用户的全部计划。"""
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, user_id, username, exam_name, title, target_info,
                   daily_hours, user_feedback, generated_plan, created_at, updated_at,
                   is_fused, fused_plan, goals_json
            FROM user_plans WHERE user_id = ? ORDER BY id DESC LIMIT ?
            """,
            (int(user_id), int(limit)),
        ).fetchall()
        return [_plan_row_to_dict(r) for r in rows]
    finally:
        conn.close()


def get_plan_by_id(plan_id: int) -> Optional[Dict[str, Any]]:
    """按 ID 查询计划。"""
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT id, user_id, username, exam_name, title, target_info,
                   daily_hours, user_feedback, generated_plan, created_at, updated_at,
                   is_fused, fused_plan, goals_json
            FROM user_plans WHERE id = ?
            """,
            (int(plan_id),),
        ).fetchone()
        return _plan_row_to_dict(row) if row else None
    finally:
        conn.close()


def update_plan(plan_id: int, user_id: int, **fields: Any) -> bool:
    """更新计划字段（严格归属校验：user_id 必须完全匹配）。"""
    allowed = {"title", "target_info", "daily_hours", "user_feedback", "generated_plan", "fused_plan", "goals_json", "is_fused"}
    fields = {k: v for k, v in fields.items() if k in allowed}
    if not fields:
        return False
    sets = ", ".join(f"{k} = ?" for k in fields)
    sql = (
        f"UPDATE user_plans SET {sets}, updated_at = CURRENT_TIMESTAMP "
        f"WHERE id = ? AND user_id = ?"
    )
    params = list(fields.values()) + [int(plan_id), int(user_id)]
    conn = get_connection()
    try:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def delete_plan(plan_id: int, user_id: int) -> bool:
    """删除计划（严格归属校验）。"""
    conn = get_connection()
    try:
        cur = conn.execute(
            "DELETE FROM user_plans WHERE id = ? AND user_id = ?",
            (int(plan_id), int(user_id)),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 考情检索缓存
# ---------------------------------------------------------------------------


def get_cached_knowledge(query_key: str) -> Optional[Dict[str, Any]]:
    """查询考情信息缓存。"""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM exam_knowledge WHERE query_key = ? AND expires_at > datetime('now')",
            (query_key,),
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        for jf in ("data_json", "sources_json"):
            if isinstance(d.get(jf), str):
                try:
                    d[jf] = json.loads(d[jf])
                except Exception:
                    pass
        return d
    finally:
        conn.close()


def save_knowledge_cache(
    query_key: str,
    exam_type: str,
    school: str,
    major: str,
    data_json: dict,
    sources_json: list,
    expire_days: int = 30,
) -> int:
    """保存考情信息到缓存。"""
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            INSERT OR REPLACE INTO exam_knowledge
                (query_key, exam_type, school, major, data_json, sources_json, fetched_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'), datetime('now', ? || ' days'))
            """,
            (
                query_key,
                exam_type,
                school,
                major,
                json.dumps(data_json, ensure_ascii=False),
                json.dumps(sources_json, ensure_ascii=False),
                str(expire_days),
            ),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def clean_expired_knowledge() -> int:
    """清理过期考情缓存。"""
    conn = get_connection()
    try:
        cur = conn.execute("DELETE FROM exam_knowledge WHERE expires_at <= datetime('now')")
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 用户画像与简历
# ---------------------------------------------------------------------------


def set_user_resume(user_id: int, resume_text: str) -> bool:
    """保存用户简历。"""
    conn = get_connection()
    try:
        cur = conn.execute("UPDATE users SET resume_text = ? WHERE id = ?", (resume_text, user_id))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def get_user_resume(user_id: int) -> Optional[str]:
    """获取用户简历。"""
    conn = get_connection()
    try:
        row = conn.execute("SELECT resume_text FROM users WHERE id = ?", (user_id,)).fetchone()
        return row["resume_text"] if row else None
    finally:
        conn.close()


def get_user_profile(user_id: int) -> Optional[Dict[str, Any]]:
    """获取用户完整画像档案。"""
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT id AS user_id, username, nickname, birthday, school, major,
                   current_plan, target_degree, phone, bio, resume_text, created_at, updated_at
            FROM users WHERE id = ?
            """,
            (user_id,),
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        for k in ["nickname", "birthday", "school", "major", "current_plan", "target_degree", "phone", "bio", "resume_text"]:
            if d.get(k) is None:
                d[k] = ""
        return d
    finally:
        conn.close()


def update_user_profile(user_id: int, profile: Dict[str, Any]) -> bool:
    """更新用户完整画像档案。"""
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            UPDATE users SET
                nickname = ?,
                birthday = ?,
                school = ?,
                major = ?,
                current_plan = ?,
                target_degree = ?,
                phone = ?,
                bio = ?,
                resume_text = ?,
                updated_at = datetime('now')
            WHERE id = ?
            """,
            (
                str(profile.get("nickname", "") or ""),
                str(profile.get("birthday", "") or ""),
                str(profile.get("school", "") or ""),
                str(profile.get("major", "") or ""),
                str(profile.get("current_plan", "") or ""),
                str(profile.get("target_degree", "") or ""),
                str(profile.get("phone", "") or ""),
                str(profile.get("bio", "") or ""),
                str(profile.get("resume_text", "") or ""),
                user_id,
            ),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 用户自定义 LLM 模型配置 (BYOK)
# ---------------------------------------------------------------------------


def _llm_row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    """行 → 配置 dict，api_key 自动解密为明文。"""
    d = dict(row)
    if d.get("api_key"):
        d["api_key"] = decrypt_secret(d["api_key"])
    return d


def list_user_llm_configs(user_id: int) -> List[Dict[str, Any]]:
    """列出用户全部模型配置（api_key 已解密，路由层负责脱敏），激活的排最前。"""
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT * FROM user_llm_configs WHERE user_id = ?
            ORDER BY is_active DESC, updated_at DESC, id DESC
            """,
            (user_id,),
        ).fetchall()
        return [_llm_row_to_dict(r) for r in rows]
    finally:
        conn.close()


def get_user_llm_config(user_id: int) -> Optional[Dict[str, Any]]:
    """获取用户当前激活的模型配置（api_key 已解密；无配置返回 None）。

    兼容旧调用方（planner / coach / search 经 get_effective_user_llm_config 使用）。
    """
    configs = list_user_llm_configs(user_id)
    for cfg in configs:
        if cfg.get("is_active"):
            return cfg
    return configs[0] if configs else None


def save_user_llm_config(
    user_id: int,
    name: str,
    provider: str,
    model_name: str,
    api_key: str,
    base_url: str = "",
    is_active: int = 1,
) -> bool:
    """按 (user_id, name) 保存一套模型配置（api_key 加密落库）；is_active=1 时独占激活。"""
    name = (name or "").strip() or f"{provider}·{model_name}"
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO user_llm_configs
                (user_id, name, provider, model_name, api_key, base_url, is_active, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, 0, datetime('now'))
            ON CONFLICT (user_id, name) DO UPDATE SET
                provider = excluded.provider,
                model_name = excluded.model_name,
                api_key = excluded.api_key,
                base_url = excluded.base_url,
                updated_at = datetime('now')
            """,
            (user_id, name, provider, model_name, encrypt_secret(api_key), base_url.strip()),
        )
        if is_active:
            conn.execute("UPDATE user_llm_configs SET is_active = 0 WHERE user_id = ?", (user_id,))
            conn.execute(
                "UPDATE user_llm_configs SET is_active = 1 WHERE user_id = ? AND name = ?",
                (user_id, name),
            )
        else:
            # 若用户此前没有任何配置，首套无论如何都要激活
            count = conn.execute(
                "SELECT COUNT(*) AS n FROM user_llm_configs WHERE user_id = ?", (user_id,)
            ).fetchone()["n"]
            has_active = conn.execute(
                "SELECT COUNT(*) AS n FROM user_llm_configs WHERE user_id = ? AND is_active = 1",
                (user_id,),
            ).fetchone()["n"]
            if count and not has_active:
                conn.execute(
                    "UPDATE user_llm_configs SET is_active = 1 WHERE user_id = ? AND name = ?",
                    (user_id, name),
                )
        conn.commit()
        return True
    finally:
        conn.close()


def activate_user_llm_config(user_id: int, name: str) -> bool:
    """切换激活配置：目标套激活，其余取消。"""
    conn = get_connection()
    try:
        cur = conn.execute(
            "UPDATE user_llm_configs SET is_active = 0 WHERE user_id = ?", (user_id,)
        )
        cur = conn.execute(
            "UPDATE user_llm_configs SET is_active = 1, updated_at = datetime('now') "
            "WHERE user_id = ? AND name = ?",
            (user_id, name),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def delete_user_llm_config(user_id: int, name: Optional[str] = None) -> bool:
    """删除模型配置：name 为 None 时清空全部（恢复系统默认）。

    若删掉的是激活套且还有剩余配置，自动启用最近更新的一套，保证始终有激活项。
    """
    conn = get_connection()
    try:
        if name is None:
            cur = conn.execute("DELETE FROM user_llm_configs WHERE user_id = ?", (user_id,))
        else:
            cur = conn.execute(
                "DELETE FROM user_llm_configs WHERE user_id = ? AND name = ?", (user_id, name)
            )
        if cur.rowcount > 0:
            remaining = conn.execute(
                """
                SELECT name FROM user_llm_configs WHERE user_id = ?
                ORDER BY is_active DESC, updated_at DESC, id DESC LIMIT 1
                """,
                (user_id,),
            ).fetchone()
            has_active = conn.execute(
                "SELECT COUNT(*) AS n FROM user_llm_configs WHERE user_id = ? AND is_active = 1",
                (user_id,),
            ).fetchone()["n"]
            if remaining and not has_active:
                conn.execute(
                    "UPDATE user_llm_configs SET is_active = 1 WHERE user_id = ? AND name = ?",
                    (user_id, remaining["name"]),
                )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()
