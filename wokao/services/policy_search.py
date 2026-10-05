"""wokao.services.policy_search — 申博 / 考研等政策真实检索。

与 knowledge_retriever 的分工：
  - 本模块：排程前的「招生政策快查」——无 LLM 依赖、免 API Key、轻量快速，
    供 wokao.agents.planner 在生成方案前注入最新招生简章摘要；
  - knowledge_retriever：考情「深度检索」——LLM 生成搜索词 + 结构化字段抽取
    + S/A/B 信任评级 + SQLite 缓存，服务于 /api/search_exam_info 交互式查询。

搜索源（免 key，无需 API）：
  1) Bing 网页搜索（requests 直连，最快最稳，优先）—— 实测可返回 target 院校官方招生页；
  2) Playwright 兜底 html.duckduckgo.com（浏览器路径）。

页面抓取（取正文）：
  1) Playwright（Chromium，能渲染 JS/SPA，主路径，进程级单例复用）；
  2) requests 静态兜底（无浏览器也能抓普通官网 HTML）。

浏览器路径统一指向项目 .pw-browsers（E 盘，避免占 C 盘）。
"""
from __future__ import annotations

import os
import re
import threading
from typing import Any, Dict, List

# ---- Playwright 浏览器路径（E 盘，C 盘紧张）----
# 注意：本文件位于 wokao/services/ 下，项目根需上溯三级。
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_PW_BROWSERS = os.path.join(_PROJECT_ROOT, ".pw-browsers")
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", _PW_BROWSERS)

try:
    import requests  # 静态抓取 + Bing 搜索兜底
except Exception:  # pragma: no cover
    requests = None



def _quote(s: str) -> str:
    if requests is not None:
        return requests.utils.quote(s)
    return s.replace(" ", "+").replace("（", "(").replace("）", ")")


# ----------------------------------------------------------------------------
# 搜索层
# ----------------------------------------------------------------------------
def _bing_search(query: str, max_results: int = 8) -> List[Dict[str, str]]:
    """Bing 网页搜索（requests 直连，免 key）。返回 [{title,url,snippet}]。"""
    if requests is None:
        return []
    url = f"https://www.bing.com/search?q={_quote(query)}&setlang=zh-CN&cc=CN"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
        ),
        "Accept-Language": "zh-CN,zh;q=0.9",
    }
    try:
        r = requests.get(url, headers=headers, timeout=15)
        html = r.text
    except Exception:
        return []
    out: List[Dict[str, str]] = []
    for block in re.split(r'<li class="b_algo"', html)[1:]:
        m_url = re.search(r'<h2><a[^>]*href="(https?://[^"]+)"', block) or re.search(
            r'href="(https?://[^"]+)"', block
        )
        if not m_url:
            continue
        u = m_url.group(1)
        if any(s in u for s in ("bing.com", "microsoft", "msn.com", "aka.ms", "go.micro", "cdn", "bingj", "beian")):
            continue
        t = re.search(r"<h2>(?:<a[^>]*>)?([^<]+)", block)
        title = t.group(1).strip() if t else u
        s = re.search(r"<p[^>]*>(.*?)</p>", block, re.S)
        snippet = re.sub(r"<[^>]+>", "", s.group(1)).strip() if s else ""
        out.append({"title": title, "url": u, "snippet": snippet})
        if len(out) >= max_results:
            break
    return out


_chromium_installed_cache: bool | None = None


def _chromium_installed() -> bool:
    """快速判断 Chromium 是否已真正装好（可执行文件存在），结果缓存。

    避免在『下载中/半安装』状态下调用 chromium.launch() 长时间挂起（不抛异常），
    导致整条检索链路卡死。装好前一律走 requests 兜底，装好后再自动启用浏览器渲染。
    """
    global _chromium_installed_cache
    if _chromium_installed_cache is not None:
        return _chromium_installed_cache
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            exe = p.chromium.executable_path
            _chromium_installed_cache = bool(exe) and os.path.exists(exe)
    except Exception:  # noqa: BLE001
        _chromium_installed_cache = False
    return _chromium_installed_cache


def _playwright_search_fallback(query: str, max_results: int = 8) -> List[Dict[str, str]]:
    """Bing 主搜索失败时的兜底：用 Playwright 打开 html.duckduckgo.com 提取结果。"""
    if not _chromium_installed():
        return []
    from playwright.sync_api import sync_playwright

    out: List[Dict[str, str]] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(
                f"https://html.duckduckgo.com/html/?q={_quote(query)}",
                timeout=20000,
            )
            page.wait_for_selector(".result__a", timeout=10000)
            for a in page.query_selector_all(".result__a")[:max_results]:
                title = a.inner_text()
                url = a.get_attribute("href")
                if url:
                    out.append({"title": title, "url": url, "snippet": ""})
        finally:
            browser.close()
    return out


# ----------------------------------------------------------------------------
# 抓取层
# ----------------------------------------------------------------------------
def _requests_fetch(url: str, timeout_ms: int = 20000, max_chars: int = 3500) -> str:
    """静态页面抓取兜底（requests）。去脚本/样式，抽正文并截断。"""
    if requests is None:
        return f"（抓取失败：未安装 requests）"
    try:
        r = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
            timeout=max(5, timeout_ms / 1000),
        )
        text = r.text
        text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", text, flags=re.S | re.I)
        text = re.sub(r"<[^>]+>", "\n", text)
        text = re.sub(r"&[a-z#0-9]+;", " ", text)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()[:max_chars]
    except Exception as e:  # noqa: BLE001
        return f"（抓取失败：{e}）"


# ----------------------------------------------------------------------------
# Playwright 浏览器单例（进程级缓存，避免每次抓取都 launch，省 8s/次）
# ----------------------------------------------------------------------------
_pw_lock = threading.Lock()
_pw_browser = None  # 缓存的 Chromium browser 实例


def _get_browser():
    """惰性启动并复用单个 Chromium 浏览器（线程安全）。失败返回 None。"""
    global _pw_browser
    with _pw_lock:
        if _pw_browser is not None:
            try:
                if _pw_browser.is_connected():
                    return _pw_browser
            except Exception:  # noqa: BLE001
                _pw_browser = None
        if not _chromium_installed():
            return None
        try:
            from playwright.sync_api import sync_playwright

            pw = sync_playwright().start()
            _pw_browser = pw.chromium.launch(headless=True, timeout=20000)
            return _pw_browser
        except Exception:  # noqa: BLE001
            _pw_browser = None
            return None


def _fetch_page_text(url: str, timeout_ms: int = 20000, max_chars: int = 3500) -> str:
    """优先 Playwright（已装 Chromium 时，能渲染 JS/SPA，复用单例浏览器）；
    否则/失败时回退 requests 静态抓取。

    全程持锁，串行化页面生命周期，避免多线程并发复用同一 browser 引发的竞态。
    """
    browser = _get_browser() if _chromium_installed() else None
    if browser is not None:
        with _pw_lock:
            try:
                page = browser.new_page()
                try:
                    page.set_default_timeout(timeout_ms)
                    page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
                    page.wait_for_timeout(800)
                    text = page.evaluate("() => document.body.innerText")
                finally:
                    page.close()
                text = re.sub(r"\n{3,}", "\n\n", text)
                text = re.sub(r"[ \t]{2,}", " ", text)
                return text.strip()[:max_chars]
            except Exception:  # noqa: BLE001
                pass
    # Playwright 不可用（未装 Chromium / 半安装态 / 渲染失败）→ 静态兜底
    return _requests_fetch(url, timeout_ms, max_chars)


# ----------------------------------------------------------------------------
# 对外：搜索 + 抓取
# ----------------------------------------------------------------------------
def search_and_fetch(query: str, top_k: int = 4) -> Dict[str, Any]:
    """搜索 + 抓取 top 页面，返回 {query, sources, combined_text}。"""
    results = _bing_search(query, max_results=top_k + 4)
    if not results:
        try:
            results = _playwright_search_fallback(query, max_results=top_k + 4)
        except Exception:
            results = []
    sources: List[Dict[str, Any]] = []
    texts: List[str] = []
    for r in results[:top_k]:
        if not r.get("url"):
            continue
        content = _fetch_page_text(r["url"])
        sources.append(
            {
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "snippet": r.get("snippet", ""),
                "content": content,
            }
        )
        texts.append(f"## 来源：{r.get('title', '')}\n{r.get('url', '')}\n{content}")
    combined = "\n\n---\n\n".join(texts)
    return {"query": query, "sources": sources, "combined_text": combined[:14000]}
