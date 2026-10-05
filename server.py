"""server.py — 项目启动入口（uvicorn server:app）。"""
from __future__ import annotations

import logging
import os

import uvicorn

from wokao.api import app, create_app

__all__ = ["app", "create_app"]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "127.0.0.1")
    print(f"🚀 [我考 WoKao-ExamAgent] 正在启动服务：http://{host}:{port}")
    uvicorn.run("server:app", host=host, port=port, reload=False)
