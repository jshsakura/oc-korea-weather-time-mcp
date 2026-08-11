"""시간대 처리 검증 — 외부 호출 없이 순수 로직만."""

from __future__ import annotations

from oc_korea_weather_time_mcp.timezone.tools import convert_time, find_timezone, get_current_time


class TestGetCurrentTime:
    def test_defaults_to_seoul(self):
        result = get_current_time()
        assert result["시간대"] == "Asia/Seoul"
        assert result["UTC오프셋"] == "+09:00"

    def test_rejects_unknown_zone_without_raising(self):
        result = get_current_time("Mars/Olympus")
        assert "오류" in result
        assert "find_timezone" in result["오류"]


class TestConvertTime:
    def test_seoul_to_new_york(self):
        result = convert_time("2026-08-11 14:00", "Asia/Seoul", "America/New_York")
        assert result["원본"]["일시"] == "2026-08-11 14:00:00"
        # 서울 14:00 = 뉴욕 01:00 (여름, EDT -04:00)
        assert result["변환"]["일시"] == "2026-08-11 01:00:00"
        assert result["변환"]["UTC오프셋"] == "-04:00"

    def test_winter_offset_differs_from_summer(self):
        """서머타임을 zoneinfo 가 처리하는지 확인한다."""
        summer = convert_time("2026-08-11 12:00", "UTC", "America/New_York")
        winter = convert_time("2026-01-11 12:00", "UTC", "America/New_York")
        assert summer["변환"]["UTC오프셋"] == "-04:00"
        assert winter["변환"]["UTC오프셋"] == "-05:00"

    def test_reports_unparseable_time(self):
        result = convert_time("어제 저녁", "Asia/Seoul", "UTC")
        assert "오류" in result


class TestFindTimezone:
    def test_finds_seoul(self):
        result = find_timezone("seoul")
        assert "Asia/Seoul" in result["결과"]

    def test_reports_truncation(self):
        result = find_timezone("america")
        if result["전체건수"] > len(result["결과"]):
            assert "안내" in result

    def test_rejects_empty_query(self):
        assert "오류" in find_timezone("   ")
