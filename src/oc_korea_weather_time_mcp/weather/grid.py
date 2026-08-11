"""위경도 ↔ 기상청 격자(nx, ny) 변환.

기상청 단기예보 API는 위경도를 받지 않고 자체 격자 좌표를 쓴다.
Lambert Conformal Conic 투영이며, 파라미터는 기상청이 공개한 값 그대로다.
"""

from __future__ import annotations

import math
from typing import NamedTuple

# --- 기상청이 고시한 투영 파라미터 (변경 금지) ---
EARTH_RADIUS_KM = 6371.00877
GRID_SPACING_KM = 5.0
STANDARD_PARALLEL_1 = 30.0
STANDARD_PARALLEL_2 = 60.0
ORIGIN_LONGITUDE = 126.0
ORIGIN_LATITUDE = 38.0
ORIGIN_X = 43  # 기준점 X좌표 (격자 단위)
ORIGIN_Y = 136  # 기준점 Y좌표 (격자 단위)

# 격자 유효 범위 (기상청 단기예보 격자 크기)
GRID_MIN_X, GRID_MAX_X = 1, 149
GRID_MIN_Y, GRID_MAX_Y = 1, 253

# 대한민국 대략 경계 — 입력 검증용
LAT_MIN, LAT_MAX = 33.0, 39.0
LON_MIN, LON_MAX = 124.0, 132.0

_DEGRAD = math.pi / 180.0


class GridPoint(NamedTuple):
    """기상청 격자 좌표."""

    nx: int
    ny: int


class OutOfServiceAreaError(ValueError):
    """대한민국 예보 격자 밖 좌표."""


def _projection_constants() -> tuple[float, float, float]:
    """투영 상수 (sn, sf, ro) 를 계산한다. 입력에 의존하지 않는 순수 상수."""
    re = EARTH_RADIUS_KM / GRID_SPACING_KM
    slat1 = STANDARD_PARALLEL_1 * _DEGRAD
    slat2 = STANDARD_PARALLEL_2 * _DEGRAD
    olat = ORIGIN_LATITUDE * _DEGRAD

    sn = math.tan(math.pi * 0.25 + slat2 * 0.5) / math.tan(math.pi * 0.25 + slat1 * 0.5)
    sn = math.log(math.cos(slat1) / math.cos(slat2)) / math.log(sn)

    sf = math.tan(math.pi * 0.25 + slat1 * 0.5)
    sf = (sf**sn) * math.cos(slat1) / sn

    ro = math.tan(math.pi * 0.25 + olat * 0.5)
    ro = re * sf / (ro**sn)
    return sn, sf, ro


def to_grid(latitude: float, longitude: float) -> GridPoint:
    """위경도를 기상청 격자로 변환한다.

    Raises:
        OutOfServiceAreaError: 대한민국 예보 범위를 벗어난 좌표.
    """
    if not (LAT_MIN <= latitude <= LAT_MAX and LON_MIN <= longitude <= LON_MAX):
        raise OutOfServiceAreaError(
            f"대한민국 예보 범위 밖입니다 (위도 {LAT_MIN}~{LAT_MAX}, "
            f"경도 {LON_MIN}~{LON_MAX}). 받은 값: {latitude}, {longitude}"
        )

    sn, sf, ro = _projection_constants()
    re = EARTH_RADIUS_KM / GRID_SPACING_KM

    ra = math.tan(math.pi * 0.25 + latitude * _DEGRAD * 0.5)
    ra = re * sf / (ra**sn)

    theta = longitude * _DEGRAD - ORIGIN_LONGITUDE * _DEGRAD
    if theta > math.pi:
        theta -= 2.0 * math.pi
    if theta < -math.pi:
        theta += 2.0 * math.pi
    theta *= sn

    nx = int(ra * math.sin(theta) + ORIGIN_X + 0.5)
    ny = int(ro - ra * math.cos(theta) + ORIGIN_Y + 0.5)

    if not (GRID_MIN_X <= nx <= GRID_MAX_X and GRID_MIN_Y <= ny <= GRID_MAX_Y):
        raise OutOfServiceAreaError(
            f"격자 범위를 벗어났습니다 (nx={nx}, ny={ny}). "
            f"유효 범위: x {GRID_MIN_X}~{GRID_MAX_X}, y {GRID_MIN_Y}~{GRID_MAX_Y}"
        )

    return GridPoint(nx=nx, ny=ny)
