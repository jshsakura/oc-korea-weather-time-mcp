"""지역명 → 좌표 해석.

LLM 이 "인천 날씨" 를 물었을 때 위경도를 지어내지 않게, 서버가 표를 들고 있는다.
좌표는 각 시·도청(또는 시청) 소재지 기준이다.
"""

from __future__ import annotations

import os
from typing import Final, NamedTuple

DEFAULT_LOCATION_ENV: Final[str] = "KMA_DEFAULT_LOCATION"
FALLBACK_LOCATION: Final[str] = "서울"


class Place(NamedTuple):
    name: str
    latitude: float
    longitude: float


# 광역시·도청 + 주요 시. 좌표는 청사 기준.
PLACES: Final[dict[str, Place]] = {
    "서울": Place("서울", 37.5665, 126.9780),
    "인천": Place("인천", 37.4563, 126.7052),
    "부산": Place("부산", 35.1796, 129.0756),
    "대구": Place("대구", 35.8714, 128.6014),
    "광주": Place("광주", 35.1595, 126.8526),
    "대전": Place("대전", 36.3504, 127.3845),
    "울산": Place("울산", 35.5384, 129.3114),
    "세종": Place("세종", 36.4800, 127.2890),
    "수원": Place("수원", 37.2636, 127.0286),
    "성남": Place("성남", 37.4200, 127.1265),
    "용인": Place("용인", 37.2411, 127.1776),
    "고양": Place("고양", 37.6584, 126.8320),
    "부천": Place("부천", 37.5035, 126.7660),
    "안양": Place("안양", 37.3943, 126.9568),
    "화성": Place("화성", 37.1996, 126.8314),
    "남양주": Place("남양주", 37.6360, 127.2165),
    "춘천": Place("춘천", 37.8813, 127.7300),
    "강릉": Place("강릉", 37.7519, 128.8761),
    "원주": Place("원주", 37.3422, 127.9202),
    "청주": Place("청주", 36.6424, 127.4890),
    "충주": Place("충주", 36.9910, 127.9259),
    "천안": Place("천안", 36.8151, 127.1139),
    "전주": Place("전주", 35.8242, 127.1480),
    "군산": Place("군산", 35.9676, 126.7369),
    "여수": Place("여수", 34.7604, 127.6622),
    "순천": Place("순천", 34.9506, 127.4872),
    "목포": Place("목포", 34.8118, 126.3922),
    "포항": Place("포항", 36.0190, 129.3435),
    "경주": Place("경주", 35.8562, 129.2247),
    "안동": Place("안동", 36.5684, 128.7294),
    "창원": Place("창원", 35.2280, 128.6811),
    "김해": Place("김해", 35.2285, 128.8894),
    "진주": Place("진주", 35.1800, 128.1076),
    "제주": Place("제주", 33.4996, 126.5312),
    "서귀포": Place("서귀포", 33.2541, 126.5601),
}

# 흔히 쓰는 다른 표기 → 표준 이름
ALIASES: Final[dict[str, str]] = {
    "서울시": "서울", "서울특별시": "서울",
    "인천시": "인천", "인천광역시": "인천",
    "부산시": "부산", "부산광역시": "부산",
    "대구시": "대구", "대구광역시": "대구",
    "광주시": "광주", "광주광역시": "광주",
    "대전시": "대전", "대전광역시": "대전",
    "울산시": "울산", "울산광역시": "울산",
    "세종시": "세종", "세종특별자치시": "세종",
    "제주시": "제주", "제주도": "제주", "제주특별자치도": "제주",
    "창원시": "창원", "수원시": "수원", "청주시": "청주",
    "전주시": "전주", "포항시": "포항", "천안시": "천안",
}


class UnknownPlaceError(ValueError):
    """표에 없는 지역명."""


def _parse_coordinates(text: str) -> Place | None:
    """`37.5665,126.978` 형태면 좌표로 읽는다."""
    if "," not in text:
        return None
    lat_text, _, lon_text = text.partition(",")
    try:
        return Place(text, float(lat_text.strip()), float(lon_text.strip()))
    except ValueError:
        return None


def default_location() -> str:
    """환경변수로 지정된 기본 지역. 없으면 서울."""
    return os.environ.get(DEFAULT_LOCATION_ENV, "").strip() or FALLBACK_LOCATION


def resolve(location: str = "") -> Place:
    """지역명·별칭·좌표 문자열을 Place 로 바꾼다.

    빈 문자열이면 `KMA_DEFAULT_LOCATION` 을 쓴다.

    Raises:
        UnknownPlaceError: 표에 없고 좌표로도 읽히지 않는 입력.
    """
    text = (location or "").strip()
    if not text:
        text = default_location()

    coordinates = _parse_coordinates(text)
    if coordinates is not None:
        return coordinates

    canonical = ALIASES.get(text, text)
    place = PLACES.get(canonical)
    if place is not None:
        return place

    # 부분 일치 — "성남시 분당구" 같은 입력을 건진다
    partial = [name for name in PLACES if name in text]
    if len(partial) == 1:
        return PLACES[partial[0]]

    raise UnknownPlaceError(
        f"모르는 지역입니다: {location!r}. "
        f"'위도,경도' 로 넘기거나 다음 중에서 고르세요 — {', '.join(names())}"
    )


def names() -> list[str]:
    """지원하는 지역명 목록."""
    return sorted(PLACES)
