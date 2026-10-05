"""tests/test_agent_robustness.py — 测试 Agent JSON 容错修复算法与时间解析。"""

import json
import pytest
from wokao.agents.parser import extract_json_safely as _extract_json
from wokao.agents.prompts import current_datetime_raw as _current_datetime_raw
from wokao.agents.prompts import extract_exam_month as _extract_exam_month


def test_extract_valid_markdown_json():
    text = """这是为您生成的方案：
```json
{
  "title": "考研与考公融合计划",
  "summary": "12周双轨推进",
  "horizon_weeks": 12,
  "tracks": [
    {
      "exam_name": "考研",
      "tasks": [
        {"title": "英语真题阅读", "week": 1, "weekday": "周一", "time_block": "08:30-10:00", "duration_hours": 1.5, "metric": "刷2篇", "status": "todo"}
      ]
    }
  ]
}
```
祝您备考顺利！"""
    res = _extract_json(text)
    assert res is not None
    assert res["title"] == "考研与考公融合计划"
    assert len(res["tracks"]) == 1
    assert len(res["tracks"][0]["tasks"]) == 1


def test_extract_truncated_json_repair():
    """测试长 JSON 因 Max Tokens 截断时，自动补全修复算法。"""
    truncated_text = """```json
{
  "title": "申博+考公长方案",
  "summary": "多目标并行",
  "horizon_weeks": 12,
  "tracks": [
    {
      "exam_name": "申博",
      "tasks": [
        {"title": "撰写研究计划初稿", "week": 1, "weekday": "周一", "time_block": "09:00-11:00", "duration_hours": 2.0, "metric": "完成3页", "status": "todo"},
        {"title": "联系导师套磁", "week": 2, "weekday": "周二", "time_block": "14:00-15:30", "duration_hours": 1.5, "metric": "发出2封"
"""
    res = _extract_json(truncated_text)
    assert res is not None
    assert "tracks" in res
    # 哪怕截断，也能解析出包含有效任务的结构
    assert len(res["tracks"]) >= 1


def test_extract_json_with_trailing_commas():
    """测试带有悬空尾部逗号的不规范 JSON。"""
    bad_json = """{
  "title": "方案A",
  "summary": "概述",
  "horizon_weeks": 12,
  "tracks": [
    {
      "exam_name": "国考",
      "tasks": [
        {"title": "行测常识", "week": 1, "weekday": "周三", "time_block": "19:00-20:30", "duration_hours": 1.5, "metric": "刷50题", "status": "todo"},
      ],
    },
  ],
}"""
    res = _extract_json(bad_json)
    assert res is not None
    assert res["title"] == "方案A"


def test_extract_exam_month():
    assert _extract_exam_month("初试 2026-12-20 至 21") == "12月"
    assert _extract_exam_month("每年 3 月笔试") == "3月"
    assert _extract_exam_month("具体时间待公布") == "考前"


def test_current_datetime_raw():
    now_str = _current_datetime_raw()
    assert "年" in now_str
    assert "月" in now_str
    assert "日" in now_str
    assert "ISO:" in now_str
