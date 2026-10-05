"""wokao.db.session — SQLite 连接会话与并发配置。"""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path

# 默认数据库路径（保存在项目根目录下的 wokao.db）
BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
DB_PATH: str = os.getenv("WOKAO_DB_PATH") or str(BASE_DIR / "wokao.db")


def get_connection() -> sqlite3.Connection:
    """获取 SQLite 连接，并开启 WAL 模式提高并发性能。"""
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn
