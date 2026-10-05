"""wokao.db — 数据库模块。

统一导出数据会话、模型初始化、种子数据与 CRUD 函数。
"""
from wokao.db.session import DB_PATH, get_connection
from wokao.db.seeds import PRESET_EXAMS
from wokao.db.models import init_db
from wokao.db.crud import (
    get_all_exams,
    get_exam_by_name,
    create_user,
    get_user_by_username,
    get_user_by_id,
    create_session,
    get_user_by_token,
    clean_expired_sessions,
    delete_session,
    save_user_plan,
    get_user_plans,
    get_plan_by_id,
    update_plan,
    delete_plan,
    get_cached_knowledge,
    save_knowledge_cache,
    clean_expired_knowledge,
    set_user_resume,
    get_user_resume,
    get_user_llm_config,
    save_user_llm_config,
    delete_user_llm_config,
)

__all__ = [
    "DB_PATH",
    "get_connection",
    "PRESET_EXAMS",
    "init_db",
    "get_all_exams",
    "get_exam_by_name",
    "create_user",
    "get_user_by_username",
    "get_user_by_id",
    "create_session",
    "get_user_by_token",
    "clean_expired_sessions",
    "delete_session",
    "save_user_plan",
    "get_user_plans",
    "get_plan_by_id",
    "update_plan",
    "delete_plan",
    "get_cached_knowledge",
    "save_knowledge_cache",
    "clean_expired_knowledge",
    "set_user_resume",
    "get_user_resume",
    "get_user_llm_config",
    "save_user_llm_config",
    "delete_user_llm_config",
]
