"""표시 변환 검증 — 단위 오표기 회귀 방지."""

from __future__ import annotations

from oc_korea_weather_time_mcp.weather.formatter import format_forecast, format_observation


def _item(category, value, **extra):
    return {"category": category, "fcstValue": value, "fcstDate": "20260811",
            "fcstTime": "1400", **extra}


def test_does_not_append_unit_to_text_value():
    """기상청은 강수량 자리에 '강수없음' 같은 문자열을 섞어 보낸다."""
    out = format_forecast([_item("PCP", "강수없음")])
    assert out["예보"][0]["1시간 강수량"] == "강수없음"


def test_appends_unit_to_numeric_value():
    out = format_forecast([_item("T1H", "31")])
    assert out["예보"][0]["기온"] == "31℃"


def test_decodes_sky_code():
    out = format_forecast([_item("SKY", "1")])
    assert out["예보"][0]["하늘상태"] == "맑음"


def test_unknown_code_is_not_invented():
    out = format_forecast([_item("SKY", "9")])
    assert "알 수 없음(9)" in out["예보"][0]["하늘상태"]


def test_observation_uses_obsr_value():
    items = [{"category": "T1H", "obsrValue": "33", "baseDate": "20260811",
              "baseTime": "1300", "nx": 60, "ny": 127}]
    out = format_observation(items)
    assert out["관측값"]["기온"] == "33℃"
    assert out["관측시각"] == "20260811 1300"
