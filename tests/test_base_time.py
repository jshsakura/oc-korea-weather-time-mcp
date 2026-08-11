"""발표시각 선택 로직 — 기상청 발표 스케줄을 따르는지 검증한다."""

from __future__ import annotations

from datetime import datetime

from oc_korea_weather_time_mcp.weather.kma_client import (
    KST,
    resolve_ultra_short_base,
    resolve_village_base,
)


def at(year, month, day, hour, minute):
    return datetime(year, month, day, hour, minute, tzinfo=KST)


class TestUltraShortBase:
    """초단기 — 매시 40분 생성. 그 전이면 한 시간 전 발표분."""

    def test_after_publish_minute_uses_current_hour(self):
        base = resolve_ultra_short_base(at(2026, 8, 11, 14, 45))
        assert (base.base_date, base.base_time) == ("20260811", "1400")

    def test_before_publish_minute_falls_back_one_hour(self):
        base = resolve_ultra_short_base(at(2026, 8, 11, 14, 5))
        assert (base.base_date, base.base_time) == ("20260811", "1300")

    def test_rolls_back_across_midnight(self):
        base = resolve_ultra_short_base(at(2026, 8, 11, 0, 10))
        assert (base.base_date, base.base_time) == ("20260810", "2300")


class TestVillageBase:
    """단기예보 — 02·05·08·11·14·17·20·23시 발표, 10분 여유."""

    def test_picks_most_recent_slot(self):
        base = resolve_village_base(at(2026, 8, 11, 15, 0))
        assert (base.base_date, base.base_time) == ("20260811", "1400")

    def test_waits_for_publish_delay(self):
        """14:05 는 아직 14시 발표분이 안 떴다고 보고 11시 것을 쓴다."""
        base = resolve_village_base(at(2026, 8, 11, 14, 5))
        assert (base.base_date, base.base_time) == ("20260811", "1100")

    def test_before_first_slot_uses_previous_day_last_slot(self):
        base = resolve_village_base(at(2026, 8, 11, 1, 30))
        assert (base.base_date, base.base_time) == ("20260810", "2300")

    def test_exact_slot_boundary_is_not_used_early(self):
        base = resolve_village_base(at(2026, 8, 11, 2, 0))
        assert (base.base_date, base.base_time) == ("20260810", "2300")
