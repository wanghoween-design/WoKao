"""wokao.api.app — FastAPI 应用程序装配与静态前端托管。"""
from __future__ import annotations

import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from wokao.api.routes.auth_routes import router as auth_router
from wokao.api.routes.coach_routes import router as coach_router
from wokao.api.routes.config_routes import router as config_router
from wokao.api.routes.plan_routes import router as plan_router
from wokao.api.routes.search_routes import router as search_router
from wokao.db import clean_expired_knowledge, clean_expired_sessions, init_db

BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
FRONTEND_DIST: Path = BASE_DIR / "frontend" / "dist"
INDEX_FILE: Path = FRONTEND_DIST / "index.html"


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用实例。"""
    # 确保数据库表已初始化，并顺手清理过期会话与过期的考情缓存
    init_db()
    clean_expired_sessions()
    clean_expired_knowledge()

    app = FastAPI(
        title="我考 · 国家考试备考规划院 API",
        version="2.0.0",
        description="多目标融合排程、24H 全景作息、Apple 日历同步与 AI 伴学导师 API。",
    )

    # 跨域配置：仅放行本地 Vite 开发服务器；认证走 Bearer 头（非 Cookie），
    # 无需 allow_credentials，避免「* + credentials」的危险组合。
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 挂载路由蓝图
    app.include_router(auth_router)
    app.include_router(plan_router)
    app.include_router(coach_router)
    app.include_router(config_router)
    app.include_router(search_router)

    # 静态前端资源托管 (生产构建)
    if FRONTEND_DIST.is_dir() and (FRONTEND_DIST / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")

    @app.get("/", summary="前端首页")
    def index():
        if INDEX_FILE.is_file():
            return FileResponse(str(INDEX_FILE), media_type="text/html; charset=utf-8")
        return JSONResponse(
            status_code=200,
            content={"message": "WoKao-ExamAgent API is running. Build frontend with 'npm run build' inside frontend/."},
        )

    return app


app = create_app()
