"""기상청 응답 코드 → 사람이 읽는 값 매핑.

API 는 `SKY=1` 같은 숫자만 돌려준다. LLM 이 그대로 받으면 해석을 지어내므로
서버 단에서 풀어서 넘긴다.
"""

from __future__ import annotations

from typing import Final

# 하늘상태
SKY: Final[dict[str, str]] = {
    "1": "맑음",
    "3": "구름많음",
    "4": "흐림",
}

# 강수형태 (단기예보)
PTY: Final[dict[str, str]] = {
    "0": "없음",
    "1": "비",
    "2": "비/눈",
    "3": "눈",
    "4": "소나기",
    "5": "빗방울",
    "6": "빗방울눈날림",
    "7": "눈날림",
}

# 풍향 16방위 — 각도를 22.5도 단위로 끊는다
WIND_DIRECTIONS: Final[tuple[str, ...]] = (
    "북", "북북동", "북동", "동북동",
    "동", "동남동", "남동", "남남동",
    "남", "남남서", "남서", "서남서",
    "서", "서북서", "북서", "북북서",
)
_DIRECTION_STEP_DEGREES: Final[float] = 360.0 / len(WIND_DIRECTIONS)

# 예보 항목 코드 → 이름·단위
CATEGORIES: Final[dict[str, tuple[str, str]]] = {
    "T1H": ("기온", "℃"),
    "TMP": ("기온", "℃"),
    "TMN": ("일최저기온", "℃"),
    "TMX": ("일최고기온", "℃"),
    "RN1": ("1시간 강수량", "mm"),
    "PCP": ("1시간 강수량", "mm"),
    "SNO": ("1시간 신적설", "cm"),
    "REH": ("습도", "%"),
    "POP": ("강수확률", "%"),
    "WSD": ("풍속", "m/s"),
    "VEC": ("풍향", "deg"),
    "SKY": ("하늘상태", ""),
    "PTY": ("강수형태", ""),
    "LGT": ("낙뢰", ""),
    "UUU": ("동서바람성분", "m/s"),
    "VVV": ("남북바람성분", "m/s"),
    "WAV": ("파고", "M"),
}


def describe_wind_direction(degrees: float) -> str:
    """풍향 각도를 16방위 이름으로 바꾼다."""
    index = int((degrees + _DIRECTION_STEP_DEGREES / 2) % 360 // _DIRECTION_STEP_DEGREES)
    return WIND_DIRECTIONS[index]


def decode(category: str, value: str) -> str:
    """항목 코드와 원시 값을 사람이 읽는 문자열로 바꾼다.

    매핑이 없으면 원본을 그대로 돌려준다 — 임의로 해석하지 않는다.
    """
    if category == "SKY":
        return SKY.get(value, f"알 수 없음({value})")
    if category == "PTY":
        return PTY.get(value, f"알 수 없음({value})")
    if category == "VEC":
        try:
            return f"{describe_wind_direction(float(value))} ({value}°)"
        except ValueError:
            return value
    return value


def label_of(category: str) -> str:
    """항목 코드의 한국어 이름. 모르는 코드는 코드 자체를 쓴다."""
    name, _unit = CATEGORIES.get(category, (category, ""))
    return name


def unit_of(category: str) -> str:
    """항목 코드의 단위. 없으면 빈 문자열."""
    _name, unit = CATEGORIES.get(category, (category, ""))
    return unit
