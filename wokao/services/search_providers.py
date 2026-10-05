"""wokao.services.search_providers — 搜索引擎适配层。

支持的搜索引擎：
1. DuckDuckGo（主力，免费无限额，无需 API Key）
2. Tavily（可选，需 API Key，专为 AI Agent 设计）
3. Bing 网页搜索（轻量爬取兜底）
"""
from __future__ import annotations

import logging
import re
import urllib.parse
from typing import List, Optional
from pydantic import BaseModel

from wokao.config import get_search_config, load_config

logger = logging.getLogger(__name__)


class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str
    provider: str


TRUST_LEVELS = {
    "S": [r".*\.edu\.cn", r"yz\.chsi\.com\.cn", r"chsi\.com\.cn", r"www\.moe\.gov\.cn", r"bm\.scs\.gov\.cn", r"ntce\.neea\.edu\.cn"],
    "A": [r"zhihu\.com", r"kaoyan\.com", r"bilibili\.com", r"xiaohongshu\.com", r"tieba\.baidu\.com"],
}


def get_trust_level(url: str) -> str:
    """按 URL 域名匹配信任等级 (S / A / B)。"""
    try:
        domain = urllib.parse.urlparse(url).netloc
    except Exception:
        return "B"

    for level, patterns in TRUST_LEVELS.items():
        for pattern in patterns:
            if re.search(pattern, domain):
                return level
    return "B"


class DuckDuckGoProvider:
    """DuckDuckGo 搜索引擎适配器。"""

    def search(self, query: str, max_results: int = 5, region: str = "cn-zh") -> List[SearchResult]:
        try:
            from duckduckgo_search import DDGS
            results = DDGS().text(query, region=region, max_results=max_results)
            return [
                SearchResult(
                    title=r.get("title", ""),
                    url=r.get("href", ""),
                    snippet=r.get("body", ""),
                    provider="duckduckgo",
                )
                for r in results
            ]
        except Exception as e:
            logger.warning("DuckDuckGo 搜索失败（query=%r）：%s", query, e)
            return []


class TavilyProvider:
    """Tavily 搜索引擎适配器。"""

    def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        try:
            from tavily import TavilyClient
            cfg = load_config()
            api_key = cfg.get("TAVILY_API_KEY")
            if not api_key:
                logger.debug("TAVILY_API_KEY 未配置，跳过 Tavily 检索。")
                return []

            client = TavilyClient(api_key=api_key)
            response = client.search(query, max_results=max_results)
            results = response.get("results", [])
            return [
                SearchResult(
                    title=r.get("title", ""),
                    url=r.get("url", ""),
                    snippet=r.get("content", ""),
                    provider="tavily",
                )
                for r in results
            ]
        except ImportError:
            logger.debug("tavily-python 未安装，跳过 Tavily 检索。")
            return []
        except Exception as e:
            logger.warning("Tavily 搜索失败（query=%r）：%s", query, e)
            return []


class BingWebProvider:
    """Bing 网页轻量抓取适配器。"""

    def search(self, query: str, max_results: int = 8) -> List[SearchResult]:
        try:
            from wokao.services.policy_search import _bing_search
            results = _bing_search(query, max_results=max_results)
            return [
                SearchResult(
                    title=r.get("title", ""),
                    url=r.get("url", ""),
                    snippet=r.get("snippet", ""),
                    provider="bing",
                )
                for r in results
            ]
        except Exception as e:
            logger.warning("Bing 网页检索失败（query=%r）：%s", query, e)
            return []


def get_provider(name: str = "duckduckgo") -> object:
    """提供者工厂函数。"""
    if name == "tavily":
        return TavilyProvider()
    elif name == "bing":
        return BingWebProvider()
    return DuckDuckGoProvider()


_VALID_PROVIDERS = ("duckduckgo", "tavily", "bing")


def _default_providers() -> List[str]:
    """从全局配置读取默认搜索提供者（SEARCH_PROVIDER，逗号分隔多个）。"""
    cfg = get_search_config()
    raw = str(cfg.get("provider") or "duckduckgo")
    picked = [p.strip().lower() for p in raw.split(",") if p.strip().lower() in _VALID_PROVIDERS]
    return picked or ["duckduckgo"]


def multi_search(queries: List[str], provider_names: Optional[List[str]] = None, max_results_per_query: int = 5) -> List[SearchResult]:
    """多关键词、多搜索引擎聚合检索与去重排序（信任等级 S > A > B）。

    provider_names 缺省时读取配置 SEARCH_PROVIDER（如 "duckduckgo,tavily"）。
    """
    if provider_names is None:
        provider_names = _default_providers()

    all_results = []
    seen_urls = set()

    for query in queries:
        for provider_name in provider_names:
            provider = get_provider(provider_name)
            results = provider.search(query, max_results=max_results_per_query)
            for res in results:
                if res.url not in seen_urls:
                    seen_urls.add(res.url)
                    all_results.append(res)

    def trust_sort_key(res: SearchResult) -> int:
        lvl = get_trust_level(res.url)
        if lvl == "S":
            return 0
        if lvl == "A":
            return 1
        return 2

    all_results.sort(key=trust_sort_key)
    return all_results
