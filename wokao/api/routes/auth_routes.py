"""wokao.api.routes.auth_routes — 考生注册、登录、登出与个人画像。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from wokao import auth
from wokao.api.dependencies import get_current_user
from wokao.api.schemas import LoginRequest, RegisterRequest, ResumeRequest, UserProfileUpdateRequest
from wokao.db import crud
from wokao.security import allow

router = APIRouter(tags=["Auth & Profile"])


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.post("/api/auth/register")
def api_register(req: RegisterRequest, request: Request):
    """考生注册（按来源 IP 限流，防批量注册）。"""
    if not allow(f"register:{_client_ip(request)}", limit=50, window_seconds=3600.0):
        raise HTTPException(status_code=429, detail="注册尝试过于频繁，请一小时后再试")
    try:
        user_id = auth.register_user(req.username, req.password)
        token = auth.create_session(user_id)
        return {"status": "ok", "user_id": user_id, "username": req.username.strip(), "token": token}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/api/auth/login")
def api_login(req: LoginRequest, request: Request):
    """考生登录（按用户名与来源 IP 双维度限流，防口令爆破）。

    注意：按用户名计数意味着攻击者可锁定他人登录（可用性换安全），
    本地单机应用定位下可接受。
    """
    ip = _client_ip(request)
    if not allow(f"login:u:{req.username}", limit=8) or not allow(f"login:ip:{ip}", limit=30):
        raise HTTPException(status_code=429, detail="登录尝试过于频繁，请 5 分钟后再试")
    user_id = auth.authenticate(req.username, req.password)
    if not user_id:
        raise HTTPException(status_code=401, detail="准考标识（用户名）或访问凭据（密码）不正确")
    token = auth.create_session(user_id)
    return {"status": "ok", "user_id": user_id, "username": req.username.strip(), "token": token}


@router.get("/api/auth/me")
@router.get("/api/me")
def api_me(user: dict = Depends(get_current_user)):
    """获取当前登录考生信息。"""
    return {"user_id": user["user_id"], "username": user["username"]}


@router.post("/api/auth/logout")
def api_logout(user: dict = Depends(get_current_user)):
    """注销当前会话。"""
    auth.logout(str(user.get("token") or ""))
    return {"status": "ok"}


@router.post("/api/profile/resume")
def api_save_resume(req: ResumeRequest, user: dict = Depends(get_current_user)):
    """保存用户简历纯文本。"""
    crud.set_user_resume(user["user_id"], req.resume_text)
    return {"status": "ok"}


@router.get("/api/profile")
def api_get_profile(user: dict = Depends(get_current_user)):
    """获取用户完整画像与档案信息。"""
    profile = crud.get_user_profile(user["user_id"])
    if not profile:
        return {
            "user_id": user["user_id"],
            "username": user.get("username", ""),
            "nickname": "",
            "birthday": "",
            "school": "",
            "major": "",
            "current_plan": "",
            "target_degree": "",
            "phone": "",
            "bio": "",
            "resume_text": "",
        }
    return profile


@router.put("/api/profile")
@router.post("/api/profile")
def api_update_profile(req: UserProfileUpdateRequest, user: dict = Depends(get_current_user)):
    """更新用户完整画像与档案信息。"""
    payload = req.model_dump()
    success = crud.update_user_profile(user["user_id"], payload)
    if not success:
        raise HTTPException(status_code=500, detail="更新考生个人档案失败")
    updated = crud.get_user_profile(user["user_id"])
    return {"status": "ok", "profile": updated}
