"""wokao.api.routes.config_routes — 用户自定义大模型 (BYOK) 与 API 配置管理。"""
from __future__ import annotations

import time
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from wokao.agents.planner import _get_llm_instance
from wokao.api.dependencies import get_current_user
from wokao.api.schemas import TestLLMConfigRequest, UserLLMConfigRequest
from wokao.db import crud

router = APIRouter(tags=["User LLM Config (BYOK)"])


def _mask_api_key(key: str) -> str:
    """脱敏 API Key。"""
    if not key or len(key) <= 8:
        return "********"
    return key[:4] + "*" * (len(key) - 8) + key[-4:]


@router.get("/api/user/llm-config")
@router.get("/api/user/llm_config")
def api_get_user_llm_config(user: dict = Depends(get_current_user)):
    """获取当前登录用户的自定义 LLM 配置。"""
    cfg = crud.get_user_llm_config(user["user_id"])
    if not cfg:
        return {"configured": False, "config": None}

    clean_cfg = dict(cfg)
    clean_cfg["has_key"] = bool(clean_cfg.get("api_key"))
    clean_cfg["api_key_masked"] = _mask_api_key(clean_cfg.get("api_key", ""))
    del clean_cfg["api_key"]
    return {"configured": True, "config": clean_cfg}


@router.post("/api/user/llm-config")
@router.post("/api/user/llm_config")
def api_save_user_llm_config(req: UserLLMConfigRequest, user: dict = Depends(get_current_user)):
    """保存或更新当前用户的自定义 LLM 配置。"""
    api_key_to_save = req.api_key.strip()
    if "*" in api_key_to_save:
        existing = crud.get_user_llm_config(user["user_id"])
        if existing and existing.get("api_key"):
            api_key_to_save = existing["api_key"]

    if not api_key_to_save:
        raise HTTPException(status_code=400, detail="API 密钥 (API Key) 不能为空")
    if not req.model_name.strip():
        raise HTTPException(status_code=400, detail="模型标识 (Model Name) 不能为空")

    crud.save_user_llm_config(
        user_id=user["user_id"],
        provider=req.provider,
        model_name=req.model_name.strip(),
        api_key=api_key_to_save,
        base_url=req.base_url.strip() if req.base_url else "",
        is_active=req.is_active,
    )
    return {"status": "ok"}


@router.delete("/api/user/llm-config")
@router.delete("/api/user/llm_config")
def api_delete_user_llm_config(user: dict = Depends(get_current_user)):
    """删除当前用户的自定义 LLM 配置（恢复系统全局默认）。"""
    crud.delete_user_llm_config(user["user_id"])
    return {"status": "ok"}


@router.post("/api/user/llm-config/test")
@router.post("/api/user/llm_config/test")
def api_test_user_llm_config(req: TestLLMConfigRequest, user: dict = Depends(get_current_user)):
    """测试指定模型与 API Key 的连通性（同步处理：LLM 调用走线程池）。"""
    api_key_to_test = req.api_key.strip()
    if "*" in api_key_to_test:
        existing = crud.get_user_llm_config(user["user_id"])
        if existing and existing.get("api_key"):
            api_key_to_test = existing["api_key"]

    if not api_key_to_test:
        return JSONResponse(
            status_code=400,
            content={"success": False, "status": "failed", "msg": "API 密钥不能为空", "detail": "API 密钥不能为空"},
        )

    test_config = {
        "provider": req.provider,
        "model_name": req.model_name.strip(),
        "api_key": api_key_to_test,
        "base_url": req.base_url.strip() if req.base_url else "",
    }

    start_time = time.time()
    try:
        from langchain_core.messages import HumanMessage
        llm = _get_llm_instance(test_config)
        resp = llm.invoke([HumanMessage(content="请回复：OK")])
        latency = round((time.time() - start_time) * 1000)
        reply = resp.content if hasattr(resp, "content") else str(resp)
        return {
            "success": True,
            "status": "success",
            "latency_ms": latency,
            "reply": str(reply).strip()[:100],
        }
    except Exception as exc:
        return JSONResponse(
            status_code=400,
            content={"success": False, "status": "failed", "msg": f"连接失败：{exc}", "detail": f"连接失败：{exc}"},
        )
