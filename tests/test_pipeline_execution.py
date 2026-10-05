"""tests/test_pipeline_execution.py — 测试「LLM 内容池 + 确定性排程引擎」融合管线。

管线契约（见 wokao/agents/planner.py 与 wokao/scheduler/engine.py）：
- LLM 失败/无密钥时降级为兜底内容池，最终方案永远可产出；
- C1 容量：任一轨道任一天学习总时长 ≤ daily_hours / n_tracks；
- C2 冲突：跨轨道任务永不占用同一时段。
"""

import re

import pytest

import wokao.agents.planner as planner
from wokao.agents.planner import run_fused_agent
from wokao.scheduler.engine import (
    WEEKDAYS_ZH,
    build_fused_schedule,
    normalize_llm_tracks,
)

GOALS = [
    {
        "exam_name": "考研",
        "category": "高校/大学生",
        "target_info": "985 计算机",
        "exam_subjects": ["数学", "英语", "政治", "计算机专业课"],
    },
    {
        "exam_name": "国考/省考",
        "category": "公考",
        "target_info": "省直机关",
        "exam_subjects": ["行测", "申论"],
    },
]


@pytest.fixture(autouse=True)
def _no_llm(monkeypatch):
    """让 LLM 实例化直接失败，验证兜底内容池接管（离线、确定性）。"""
    def _boom(*args, **kwargs):
        raise RuntimeError("测试环境不调用真实 LLM")
    monkeypatch.setattr(planner, "_get_llm_instance", _boom)


def _hhmm(text: str) -> float:
    h, m = text.split(":")
    return int(h) + int(m) / 60.0


def test_fused_pipeline_produces_schedule_without_llm():
    """LLM 完全失败时，管线仍应产出含全部目标轨道的合法方案。"""
    result = run_fused_agent({
        "goals_data": GOALS,
        "daily_hours": 4.0,
        "user_feedback": "周末不学",
        "use_web_search": False,
        "llm_config": None,
    })

    fused = result["fused_json"]
    assert result["is_fused"] is True
    assert fused["meta"]["engine"] == "wokao-scheduler/1.0"
    assert fused["meta"]["daily_capacity_hours"] == 4.0

    track_names = {t["exam_name"] for t in fused["tracks"]}
    assert track_names == {"考研", "国考/省考"}
    for track in fused["tracks"]:
        assert track["tasks"], "每条轨道都应有任务（兜底池保证）"
        for task in track["tasks"]:
            assert task["week"] >= 1
            assert task["weekday"] in WEEKDAYS_ZH
            assert re.fullmatch(r"\d{2}:\d{2}-\d{2}:\d{2}", task["time_block"])
            assert task["duration_hours"] > 0


def test_capacity_constraint_per_track_per_day():
    """C1：跨轨道合计每日学习时长不得超过 daily_hours。"""
    daily_hours = 4.0
    result = run_fused_agent({
        "goals_data": GOALS,
        "daily_hours": daily_hours,
        "use_web_search": False,
    })
    fused = result["fused_json"]

    used: dict = {}
    for track in fused["tracks"]:
        for task in track["tasks"]:
            key = (task["week"], task["weekday"])
            used[key] = used.get(key, 0.0) + task["duration_hours"]

    assert used, "应至少存在一个被排入任务的日期"
    for (week, weekday), total in used.items():
        assert total <= daily_hours + 0.02, f"第{week}周{weekday}超容量：{total}"


def test_no_cross_track_time_conflict():
    """C2：同一周同一天，不同轨道的任务时间不得重叠。"""
    result = run_fused_agent({
        "goals_data": GOALS,
        "daily_hours": 9.0,
        "use_web_search": False,
    })
    fused = result["fused_json"]

    by_day: dict = {}
    for track in fused["tracks"]:
        for task in track["tasks"]:
            start_s, end_s = task["time_block"].split("-")
            by_day.setdefault((task["week"], task["weekday"]), []).append(
                (_hhmm(start_s), _hhmm(end_s), track["exam_name"])
            )

    for (week, weekday), spans in by_day.items():
        spans.sort()
        for prev, curr in zip(spans, spans[1:]):
            assert curr[0] >= prev[1] - 1e-9, (
                f"第{week}周{weekday}发生跨轨重叠：{prev} 与 {curr}"
            )


def test_normalize_llm_tracks_matches_and_drops():
    """归一化按名称匹配轨道，无法匹配的 LLM 输出被丢弃，缺失目标保留空池。"""
    raw_tracks = [
        {"exam_name": "考研", "tasks": [
            {"title": "英语真题阅读", "duration_hours": 1.5, "target_week": 2,
             "metric": "精读2篇", "type": "学习"},
            {"title": "   ", "duration_hours": 1.0},          # 无标题 → 丢弃
            {"title": "垃圾任务", "duration_hours": "abc"},    # 时长非法 → 回退 2.0
        ]},
        {"exam_name": "雅思口语冲刺班", "tasks": [             # 与任何目标都不匹配 → 丢弃
            {"title": "口语练习", "duration_hours": 1.0},
        ]},
    ]
    pools = normalize_llm_tracks(raw_tracks, GOALS)

    assert set(pools) == {"考研", "国考/省考"}
    assert [t["title"] for t in pools["考研"]] == ["英语真题阅读", "垃圾任务"]
    assert pools["考研"][0]["target_week"] == 2
    assert pools["考研"][1]["duration_hours"] == 2.0
    assert pools["国考/省考"] == []


def test_llm_content_pool_is_placed_verbatim():
    """LLM 提供的内容池任务应被引擎落位使用，而不是全部落入兜底。"""
    pools = {
        "考研": [{"title": "数据结构专项突破", "duration_hours": 2.0, "type": "攻坚",
                  "metric": "攻克2个高频难点", "target_week": 1}],
    }
    fused = build_fused_schedule(
        goals_data=GOALS[:1], pools_by_name=pools, daily_hours=4.0,
    )

    titles = [t["title"] for track in fused["tracks"] for t in track["tasks"]]
    assert "数据结构专项突破" in titles
