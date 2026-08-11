"""격자 변환 검증 — 기상청이 공개한 표준 좌표와 대조한다."""

from __future__ import annotations

import pytest

from oc_korea_weather_time_mcp.weather.grid import OutOfServiceAreaError, to_grid

# 널리 인용되는 기상청 표준 검증 좌표
KNOWN_POINTS = [
    ("서울시청", 37.5665, 126.9780, 60, 127),
    ("부산시청", 35.1796, 129.0756, 98, 76),
    ("제주시청", 33.4996, 126.5312, 53, 38),
]


@pytest.mark.parametrize(("name", "lat", "lon", "nx", "ny"), KNOWN_POINTS)
def test_known_points_map_to_official_grid(name, lat, lon, nx, ny):
    # Arrange / Act
    point = to_grid(lat, lon)

    # Assert
    assert (point.nx, point.ny) == (nx, ny), name


def test_rejects_coordinates_outside_korea():
    with pytest.raises(OutOfServiceAreaError):
        to_grid(50.0, 100.0)


def test_rejects_swapped_latitude_and_longitude():
    """위경도를 바꿔 넣는 실수를 잡아낸다 (127, 37 은 국외)."""
    with pytest.raises(OutOfServiceAreaError):
        to_grid(126.9780, 37.5665)


def test_grid_is_deterministic():
    """같은 입력은 항상 같은 격자 — 상태를 들고 있지 않다."""
    first = to_grid(37.5665, 126.9780)
    second = to_grid(37.5665, 126.9780)
    assert first == second
