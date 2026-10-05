"""wokao.config — 全局统一配置加载器。

优先级：环境变量 > config.toml > config.json > 内置默认值。
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# 项目根目录
BASE_DIR: Path = Path(__file__).resolve().parent.parent

# LLM 与搜索相关配置键
_CONFIG_KEYS: tuple[str, ...] = (
    "OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_MODEL",
    "TAVILY_API_KEY", "SEARCH_PROVIDER", "KNOWLEDGE_CACHE_DAYS",
)

_DEFAULTS: Dict[str, Optional[str]] = {
    "OPENAI_API_KEY": None,
    "OPENAI_BASE_URL": None,
    "OPENAI_MODEL": "gpt-4o-mini",
    "TAVILY_API_KEY": None,
    "SEARCH_PROVIDER": "duckduckgo",
    "KNOWLEDGE_CACHE_DAYS": "30",
}


def _load_file_config() -> Dict[str, Optional[str]]:
    """从 config.toml / config.json 读取配置。"""
    cfg: Dict[str, Optional[str]] = {}
    toml_path = BASE_DIR / "config.toml"
    json_path = BASE_DIR / "config.json"

    raw: Dict[str, object] = {}
    if toml_path.is_file():
        try:
            import tomllib
            with toml_path.open("rb") as f:
                raw = json.loads(json.dumps(tomllib.load(f)))
        except Exception as exc:
            logger.warning("读取 config.toml 失败，已忽略：%s", exc)
    elif json_path.is_file():
        try:
            with json_path.open("r", encoding="utf-8") as f:
                raw = json.load(f)
        except Exception as exc:
            logger.warning("读取 config.json 失败，已忽略：%s", exc)

    for key in _CONFIG_KEYS:
        val = raw.get(key)
        if isinstance(val, str) and val.strip():
            cfg[key] = val.strip()
    return cfg


def load_config() -> Dict[str, Optional[str]]:
    """合并文件配置与环境变量（环境变量优先级最高）。"""
    merged: Dict[str, Optional[str]] = dict(_DEFAULTS)
    merged.update(_load_file_config())
    for key in _CONFIG_KEYS:
        env_val = os.getenv(key)
        if env_val and env_val.strip():
            merged[key] = env_val.strip()
    return merged


def get_openai_config() -> Dict[str, str]:
    """返回 LLM 调用参数。"""
    cfg = load_config()
    params: Dict[str, str] = {
        "api_key": cfg["OPENAI_API_KEY"] or "",
        "model": cfg["OPENAI_MODEL"] or "gpt-4o-mini",
    }
    if cfg.get("OPENAI_BASE_URL"):
        params["base_url"] = cfg["OPENAI_BASE_URL"]
    return params


def get_search_config() -> Dict[str, Optional[str]]:
    """返回搜索与知识检索配置。"""
    cfg = load_config()
    return {
        "provider": cfg.get("SEARCH_PROVIDER") or "duckduckgo",
        "tavily_api_key": cfg.get("TAVILY_API_KEY"),
        "cache_days": int(cfg.get("KNOWLEDGE_CACHE_DAYS") or "30"),
    }
