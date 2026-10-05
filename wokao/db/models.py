"""wokao.db.models — 数据库初始化、表结构定义与迁移。"""
from __future__ import annotations

import json
import sqlite3
from typing import Any, List

from wokao.db.seeds import PRESET_EXAMS
from wokao.db.session import get_connection


def _dumps(obj: Any) -> str:
    """序列化为 UTF-8 JSON 字符串。"""
    return json.dumps(obj, ensure_ascii=False)


def _insert_presets(conn: sqlite3.Connection) -> None:
    """将 PRESET_EXAMS 写入 exams 表。"""
    conn.executemany(
        """
        INSERT INTO exams
            (category, exam_name, annual_period, exam_time, registration_time, official_website,
             exam_subjects, subjects_detail, exam_format, reference_materials, tips, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                e["category"],
                e["exam_name"],
                e.get("annual_period", ""),
                e["exam_time"],
                e.get("registration_time", ""),
                e.get("official_website", ""),
                _dumps(e["exam_subjects"]),
                _dumps(e.get("subjects_detail", [])),
                _dumps(e.get("exam_format", [])),
                _dumps(e.get("reference_materials", [])),
                _dumps(e.get("tips", [])),
                e.get("description", ""),
            )
            for e in PRESET_EXAMS
        ],
    )


def init_db() -> None:
    """初始化数据库：建表并预置/迁移数据。"""
    conn: sqlite3.Connection = get_connection()
    try:
        # 用户计划表
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                exam_name TEXT NOT NULL,
                target_info TEXT,
                daily_hours REAL,
                user_feedback TEXT,
                generated_plan TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # 考试大纲表
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS exams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                exam_name TEXT NOT NULL,
                exam_time TEXT NOT NULL,
                exam_subjects TEXT NOT NULL,
                description TEXT
            )
            """
        )

        cols: List[str] = [r[1] for r in conn.execute("PRAGMA table_info(exams)")]
        if "annual_period" not in cols:
            conn.execute("DROP TABLE IF EXISTS exams")
            conn.execute(
                """
                CREATE TABLE exams (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    exam_name TEXT NOT NULL,
                    annual_period TEXT,
                    exam_time TEXT NOT NULL,
                    registration_time TEXT,
                    official_website TEXT,
                    exam_subjects TEXT NOT NULL,
                    subjects_detail TEXT,
                    exam_format TEXT,
                    reference_materials TEXT,
                    tips TEXT,
                    description TEXT
                )
                """
            )
            _insert_presets(conn)
        else:
            cnt: int = conn.execute("SELECT COUNT(*) AS c FROM exams").fetchone()["c"]
            if cnt == 0:
                _insert_presets(conn)

        # 用户账号表
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # 会话表
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP
            )
            """
        )
        sess_cols: List[str] = [r[1] for r in conn.execute("PRAGMA table_info(sessions)")]
        if "expires_at" not in sess_cols:
            conn.execute("ALTER TABLE sessions ADD COLUMN expires_at TIMESTAMP")

        # user_plans 字段迁移
        up_cols: List[str] = [r[1] for r in conn.execute("PRAGMA table_info(user_plans)")]
        if "user_id" not in up_cols:
            conn.execute("ALTER TABLE user_plans ADD COLUMN user_id INTEGER")
        if "title" not in up_cols:
            conn.execute("ALTER TABLE user_plans ADD COLUMN title TEXT")
        if "updated_at" not in up_cols:
            conn.execute("ALTER TABLE user_plans ADD COLUMN updated_at TIMESTAMP")
        if "is_fused" not in up_cols:
            conn.execute("ALTER TABLE user_plans ADD COLUMN is_fused INTEGER DEFAULT 0")
        if "fused_plan" not in up_cols:
            conn.execute("ALTER TABLE user_plans ADD COLUMN fused_plan TEXT")
        if "goals_json" not in up_cols:
            conn.execute("ALTER TABLE user_plans ADD COLUMN goals_json TEXT")

        # 历史数据归属回填：user_id 为空的旧计划按用户名匹配归属，
        # 使严格归属校验（user_id 必须相等）可安全启用。
        conn.execute(
            """
            UPDATE user_plans
            SET user_id = (SELECT u.id FROM users u WHERE u.username = user_plans.username)
            WHERE user_id IS NULL
              AND EXISTS (SELECT 1 FROM users u WHERE u.username = user_plans.username)
            """
        )

        # 考情知识检索缓存表
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS exam_knowledge (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_key TEXT NOT NULL UNIQUE,
                exam_type TEXT NOT NULL,
                school TEXT DEFAULT '',
                major TEXT DEFAULT '',
                data_json TEXT NOT NULL,
                sources_json TEXT NOT NULL,
                fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL
            )
            """
        )

        # 用户自定义 LLM 模型配置表（BYOK）
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_llm_configs (
                user_id INTEGER PRIMARY KEY,
                provider TEXT DEFAULT 'custom',
                model_name TEXT NOT NULL,
                api_key TEXT NOT NULL,
                base_url TEXT DEFAULT '',
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )

        # 用户档案全量字段迁移
        user_cols = {
            "nickname": "TEXT DEFAULT ''",
            "birthday": "TEXT DEFAULT ''",
            "school": "TEXT DEFAULT ''",
            "major": "TEXT DEFAULT ''",
            "current_plan": "TEXT DEFAULT ''",
            "target_degree": "TEXT DEFAULT ''",
            "phone": "TEXT DEFAULT ''",
            "bio": "TEXT DEFAULT ''",
            "resume_text": "TEXT DEFAULT ''",
            "updated_at": "TIMESTAMP",
        }
        for col_name, col_type in user_cols.items():
            try:
                conn.execute(f"SELECT {col_name} FROM users LIMIT 0")
            except Exception:
                conn.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")

        conn.commit()
    finally:
        conn.close()
