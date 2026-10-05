"""wokao.agents.parser — 大模型输出 JSON 智能自愈与健壮性抽取解析器。"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional


def extract_json_safely(raw_text: str) -> Optional[Dict[str, Any]]:
    """从大模型原始文本中提取并解析 JSON（支持截断自愈、尾逗号修复与 Markdown 剥离）。"""
    if not raw_text or not isinstance(raw_text, str):
        return None

    cleaned: str = raw_text.strip()

    # 1. 提取 ```json ... ``` 或 ``` ... ``` 代码块
    json_block_match = re.search(r"```(?:json)?\s*([\s\S]*?)(?:```|$)", cleaned, re.IGNORECASE)
    if json_block_match:
        cleaned = json_block_match.group(1).strip()
    elif "{" in cleaned:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if end > start:
            cleaned = cleaned[start : end + 1].strip()
        else:
            cleaned = cleaned[start:].strip()

    # 2. 清理悬空尾部逗号
    sanitized = re.sub(r",\s*([\]}])", r"\1", cleaned)

    # 3. 直接尝试 json.loads
    try:
        data = json.loads(sanitized)
        if isinstance(data, dict):
            return data
    except Exception:
        pass

    # 4. 截断修复算法：
    # 如果处于未闭合的双引号字符串内部，补全引号
    # 统计未转义双引号数量
    quotes = len(re.findall(r'(?<!\\)"', sanitized))
    if quotes % 2 != 0:
        sanitized += '"'

    # 去除末尾悬空的逗号或冒号残段
    sanitized = re.sub(r',\s*$', '', sanitized)
    sanitized = re.sub(r':\s*$', ': ""', sanitized)

    # 递归补齐未闭合的括号
    open_curly = sanitized.count("{") - sanitized.count("}")
    open_square = sanitized.count("[") - sanitized.count("]")

    if open_curly > 0 or open_square > 0:
        # 尝试几种常见闭合排列（如先闭合对象再闭合数组再闭合根对象）
        candidates = [
            sanitized + ("}" * max(0, open_curly // 2)) + ("]" * max(0, open_square)) + ("}" * max(0, open_curly - open_curly // 2)),
            sanitized + ("}" * max(0, open_curly)) + ("]" * max(0, open_square)),
            sanitized + ("]" * max(0, open_square)) + ("}" * max(0, open_curly)),
            sanitized + "}" + ("]" * max(0, open_square)) + "}" + ("}" * max(0, open_curly - 2)),
        ]
        for cand in candidates:
            try:
                data = json.loads(cand)
                if isinstance(data, dict):
                    return data
            except Exception:
                pass

        # 暴力尝试修复每个 open 栈
        repaired = sanitized
        # 模拟括号栈
        stack = []
        for ch in sanitized:
            if ch in ('{', '['):
                stack.append(ch)
            elif ch == '}' and stack and stack[-1] == '{':
                stack.pop()
            elif ch == ']' and stack and stack[-1] == '[':
                stack.pop()
        
        closing = ""
        while stack:
            top = stack.pop()
            if top == '{':
                closing += '}'
            elif top == '[':
                closing += ']'
        
        try:
            data = json.loads(repaired + closing)
            if isinstance(data, dict):
                return data
        except Exception:
            pass

    return None
