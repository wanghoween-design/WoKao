"""wokao.api.routes.config_routes — 用户自定义大模型 (BYOK) 配置管理。

支持一人多套配置（不同厂商/额度备用），单套激活即时生效；
api_key 落库加密，接口返回一律脱敏。
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from wokao.agents.planner import _get_llm_instance
from wokao.api.dependencies import get_current_user
from wokao.api.schemas import (
    LLMConfigActivateRequest,
    TestLLMConfigRequest,
    UserLLMConfigRequest,
)
from wokao.db import crud

logger = logging.getLogger(__name__)

router = APIRouter(tags=["User LLM Config (BYOK)"])

# 各厂商申请 Key 的入口（供前端展示跳转）
PROVIDER_KEY_URLS: Dict[str, str] = {
    "deepseek": "https://platform.deepseek.com",
    "dashscope": "https://bailian.console.aliyun.com",
    "zhipu": "https://open.bigmodel.cn",
    "doubao": "https://console.volcengine.com/ark",
    "siliconflow": "https://cloud.siliconflow.cn",
    "openai": "https://platform.openai.com",
}


def _mask_api_key(key: str) -> str:
    """脱敏 API Key。"""
    if not key or len(key) <= 8:
        return "********"
    return key[:4] + "*" * (len(key) - 8) + key[-4:]


def _sanitize(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """配置 dict → 前端安全形态：去掉明文 Key，给出掩码与 has_key。"""
    clean = {k: cfg[k] for k in ("name", "provider", "model_name", "base_url", "is_active") if k in cfg}
    clean["has_key"] = bool(cfg.get("api_key"))
    clean["api_key_masked"] = _mask_api_key(cfg.get("api_key", ""))
    clean["key_url"] = PROVIDER_KEY_URLS.get(cfg.get("provider", ""), "")
    return clean


def _list_sanitized(user_id: int) -> List[Dict[str, Any]]:
    return [_sanitize(c) for c in crud.list_user_llm_configs(user_id)]


@router.get("/api/user/llm-config")
@router.get("/api/user/llm_config")
def api_get_user_llm_config(user: dict = Depends(get_current_user)):
    """获取当前用户全部模型配置与当前激活套（脱敏）。"""
    configs = _list_sanitized(user["user_id"])
    active = next((c for c in configs if c.get("is_active")), None)
    return {"configured": active is not None, "config": active, "configs": configs}


@router.post("/api/user/llm-config")
@router.post("/api/user/llm_config")
def api_save_user_llm_config(req: UserLLMConfigRequest, user: dict = Depends(get_current_user)):
    """保存一套模型配置（同名覆盖；is_active=1 时保存并启用）。"""
    api_key_to_save = req.api_key.strip()
    if "*" in api_key_to_save:
        # 掩码占位：沿用同名已存配置的密钥
        existing = next(
            (c for c in crud.list_user_llm_configs(user["user_id"]) if c.get("name") == req.name.strip()),
            None,
        )
        if existing and existing.get("api_key"):
            api_key_to_save = existing["api_key"]

    if not api_key_to_save:
        raise HTTPException(status_code=400, detail="API 密钥 (API Key) 不能为空")
    if not req.model_name.strip():
        raise HTTPException(status_code=400, detail="模型标识 (Model Name) 不能为空")

    name = (req.name or "").strip() or f"{req.provider}·{req.model_name.strip()}"
    crud.save_user_llm_config(
        user_id=user["user_id"],
        name=name,
        provider=req.provider,
        model_name=req.model_name.strip(),
        api_key=api_key_to_save,
        base_url=req.base_url.strip() if req.base_url else "",
        is_active=req.is_active,
    )
    return {"status": "ok", "name": name, "configs": _list_sanitized(user["user_id"])}


@router.post("/api/user/llm-config/activate")
@router.post("/api/user/llm_config/activate")
def api_activate_user_llm_config(req: LLMConfigActivateRequest, user: dict = Depends(get_current_user)):
    """一键切换激活配置（额度用完换另一套）。"""
    ok = crud.activate_user_llm_config(user["user_id"], req.name.strip())
    if not ok:
        raise HTTPException(status_code=404, detail="配置不存在，可能已被删除")
    return {"status": "ok", "configs": _list_sanitized(user["user_id"])}


@router.delete("/api/user/llm-config")
@router.delete("/api/user/llm_config")
def api_delete_user_llm_config(name: str = "", user: dict = Depends(get_current_user)):
    """删除模型配置：带 name 删单套，不带 name 清空全部（恢复系统默认）。"""
    crud.delete_user_llm_config(user["user_id"], name.strip() or None)
    return {"status": "ok", "configs": _list_sanitized(user["user_id"])}


@router.post("/api/user/llm-config/test")
@router.post("/api/user/llm_config/test")
def api_test_user_llm_config(req: TestLLMConfigRequest, user: dict = Depends(get_current_user)):
    """测试指定模型与 API Key 的连通性（同步处理：LLM 调用走线程池）。"""
    api_key_to_test = req.api_key.strip()
    if "*" in api_key_to_test:
        existing = next(
            (c for c in crud.list_user_llm_configs(user["user_id"]) if c.get("model_name") == req.model_name.strip()),
            None,
        )
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
