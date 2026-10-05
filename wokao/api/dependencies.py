"""wokao.api.dependencies — FastAPI 认证依赖与共享业务助手。"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from fastapi import Header, HTTPException

from wokao import auth
from wokao.db import crud

logger = logging.getLogger(__name__)


def get_current_user(authorization: Optional[str] = Header(None)) -> Dict[str, object]:
    """经 Authorization: Bearer <token> 校验并获取当前已登录考生（同步处理：SQLite 读取走线程池）。"""
    token: Optional[str] = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:].strip()

    user = auth.get_current_user(token)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="会话无效或已过期，请重新登录",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"user_id": user["id"], "username": user["username"], "token": token}


def get_effective_user_llm_config(user_id: int) -> Optional[Dict[str, Any]]:
    """获取当前用户生效的自定义 LLM 配置；未配置/未激活/无密钥时返回 None 走系统默认。

    全局唯一实现（原 plan/coach/search 三处路由各自复制一份，已收敛至此）。
    """
    try:
        cfg = crud.get_user_llm_config(user_id)
        if cfg and cfg.get("is_active") and cfg.get("api_key"):
            return cfg
    except Exception as exc:
        logger.warning("读取用户 LLM 配置失败，回退系统默认：%s", exc)
    return None
