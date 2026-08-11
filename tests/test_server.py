"""서버 조립 검증 — 툴이 실제로 등록되는지, 토글이 먹는지.

서버 모듈은 import 시점에 환경변수를 읽어 툴을 등록한다.
그래서 테스트마다 모듈을 다시 불러와야 한다.
"""

from __future__ import annotations

import importlib
import sys

import pytest

MODULE = "oc_korea_weather_time_mcp.server"

WEATHER_TOOLS = {"get_current_weather", "get_hourly_forecast", "get_daily_forecast"}
TIME_TOOLS = {"get_current_time", "convert_time", "find_timezone"}


def load_server(monkeypatch, **env):
    """환경변수를 세팅한 뒤 서버 모듈을 새로 불러온다."""
    for key in ("OC_KOREA_MCP_WEATHER", "OC_KOREA_MCP_TIME"):
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    sys.modules.pop(MODULE, None)
    return importlib.import_module(MODULE)


async def tool_names(server) -> set[str]:
    return {tool.name for tool in await server.mcp.list_tools()}


@pytest.mark.asyncio
async def test_registers_all_tools_by_default(monkeypatch):
    server = load_server(monkeypatch)
    assert await tool_names(server) == WEATHER_TOOLS | TIME_TOOLS


@pytest.mark.asyncio
async def test_time_toggle_removes_time_tools(monkeypatch):
    server = load_server(monkeypatch, OC_KOREA_MCP_TIME="0")
    assert await tool_names(server) == WEATHER_TOOLS


@pytest.mark.asyncio
async def test_weather_toggle_removes_weather_tools(monkeypatch):
    server = load_server(monkeypatch, OC_KOREA_MCP_WEATHER="0")
    assert await tool_names(server) == TIME_TOOLS


@pytest.mark.parametrize("value", ["0", "false", "no", "off", "FALSE", "Off"])
@pytest.mark.asyncio
async def test_disabled_values_are_case_insensitive(monkeypatch, value):
    server = load_server(monkeypatch, OC_KOREA_MCP_TIME=value)
    assert await tool_names(server) == WEATHER_TOOLS


@pytest.mark.parametrize("value", ["1", "true", "yes", ""])
@pytest.mark.asyncio
async def test_other_values_keep_tools_enabled(monkeypatch, value):
    server = load_server(monkeypatch, OC_KOREA_MCP_TIME=value)
    assert TIME_TOOLS <= await tool_names(server)


class TestSlotClamping:
    """예보 개수 인자는 서버에서 잘라낸다 — 무한정 받아 프롬프트를 키우지 않는다."""

    def test_zero_falls_back_to_default(self, monkeypatch):
        server = load_server(monkeypatch)
        assert server._clamp_slots(0, 6) == 6

    def test_negative_falls_back_to_default(self, monkeypatch):
        server = load_server(monkeypatch)
        assert server._clamp_slots(-5, 24) == 24

    def test_caps_at_maximum(self, monkeypatch):
        server = load_server(monkeypatch)
        assert server._clamp_slots(9999, 6) == server.MAX_SLOTS

    def test_passes_through_valid_value(self, monkeypatch):
        server = load_server(monkeypatch)
        assert server._clamp_slots(12, 6) == 12


@pytest.mark.asyncio
async def test_weather_tool_reports_missing_key_without_raising(monkeypatch):
    """키가 없어도 서버는 죽지 않고 구조화된 오류를 돌려준다."""
    monkeypatch.setenv("KMA_SERVICE_KEY", "")
    server = load_server(monkeypatch)
    result = await server.get_current_weather("서울")
    assert "오류" in result
    assert "KMA_SERVICE_KEY" in result["오류"]


@pytest.mark.asyncio
async def test_weather_tool_reports_unknown_location(monkeypatch):
    server = load_server(monkeypatch)
    result = await server.get_current_weather("평양")
    assert "오류" in result
    assert "서울" in result["오류"]  # 지원 목록을 같이 준다
