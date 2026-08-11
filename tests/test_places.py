"""지역명 해석 검증."""

from __future__ import annotations

import pytest

from oc_korea_weather_time_mcp.weather.places import (
    FALLBACK_LOCATION,
    UnknownPlaceError,
    names,
    resolve,
)


class TestResolve:
    def test_known_city(self):
        assert resolve("인천").name == "인천"

    def test_alias(self):
        assert resolve("서울특별시").name == "서울"

    def test_partial_match(self):
        assert resolve("성남시 분당구").name == "성남"

    def test_coordinates_literal(self):
        place = resolve("37.5665,126.978")
        assert (round(place.latitude, 4), round(place.longitude, 3)) == (37.5665, 126.978)

    def test_empty_uses_default(self, monkeypatch):
        monkeypatch.delenv("KMA_DEFAULT_LOCATION", raising=False)
        assert resolve("").name == FALLBACK_LOCATION

    def test_env_overrides_default(self, monkeypatch):
        monkeypatch.setenv("KMA_DEFAULT_LOCATION", "부산")
        assert resolve("").name == "부산"

    def test_unknown_place_lists_options(self):
        with pytest.raises(UnknownPlaceError) as exc:
            resolve("평양")
        assert "서울" in str(exc.value)


def test_all_places_convert_to_valid_grid():
    """표에 든 좌표가 전부 기상청 격자 안에 있는지 확인한다."""
    from oc_korea_weather_time_mcp.weather.grid import to_grid

    for name in names():
        place = resolve(name)
        grid = to_grid(place.latitude, place.longitude)
        assert 1 <= grid.nx <= 149 and 1 <= grid.ny <= 253, name
