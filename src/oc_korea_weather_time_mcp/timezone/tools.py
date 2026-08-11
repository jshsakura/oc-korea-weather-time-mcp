"""시간·시간대 조회 로직. 표준 라이브러리만 쓴다."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Final
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError, available_timezones

DEFAULT_TIMEZONE: Final[str] = "Asia/Seoul"
MAX_TIMEZONE_MATCHES: Final[int] = 20



def _error(message: str) -> dict[str, Any]:
    return {"오류": message}


def _zone(name: str) -> ZoneInfo:
    """시간대 이름을 검증해 ZoneInfo 로 바꾼다."""
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError(
            f"알 수 없는 시간대입니다: {name!r}. "
            "IANA 이름을 쓰세요 (예: Asia/Seoul, America/New_York). "
            "find_timezone 툴로 검색할 수 있습니다."
        ) from exc


def _describe(moment: datetime) -> dict[str, Any]:
    """한 시점을 사람이 읽는 형태로 편다."""
    offset = moment.utcoffset() or timedelta(0)
    total_minutes = int(offset.total_seconds() // 60)
    sign = "+" if total_minutes >= 0 else "-"
    hours, minutes = divmod(abs(total_minutes), 60)
    weekday = ("월", "화", "수", "목", "금", "토", "일")[moment.weekday()]
    return {
        "시간대": str(moment.tzinfo),
        "일시": moment.strftime("%Y-%m-%d %H:%M:%S"),
        "요일": f"{weekday}요일",
        "UTC오프셋": f"{sign}{hours:02d}:{minutes:02d}",
        "약어": moment.tzname() or "",
        "ISO8601": moment.isoformat(),
        "유닉스초": int(moment.timestamp()),
    }


def get_current_time(timezone: str = DEFAULT_TIMEZONE) -> dict[str, Any]:
    """지정한 시간대의 현재 시각을 조회한다.

    Args:
        timezone: IANA 시간대 이름 (기본 Asia/Seoul)
    """
    try:
        zone = _zone(timezone)
    except ValueError as exc:
        return _error(str(exc))
    return _describe(datetime.now(zone))


def convert_time(
    time: str,
    from_timezone: str,
    to_timezone: str,
) -> dict[str, Any]:
    """한 시간대의 시각을 다른 시간대로 변환한다.

    Args:
        time: 변환할 시각. `YYYY-MM-DD HH:MM` 또는 ISO 8601
        from_timezone: 원본 IANA 시간대
        to_timezone: 대상 IANA 시간대
    """
    try:
        source = _zone(from_timezone)
        target = _zone(to_timezone)
    except ValueError as exc:
        return _error(str(exc))

    try:
        naive = datetime.fromisoformat(time.strip().replace("/", "-"))
    except ValueError:
        return _error(
            f"시각을 해석하지 못했습니다: {time!r}. "
            "`2026-08-11 14:30` 또는 ISO 8601 형식을 쓰세요."
        )

    aware = naive.replace(tzinfo=source) if naive.tzinfo is None else naive
    return {
        "원본": _describe(aware.astimezone(source)),
        "변환": _describe(aware.astimezone(target)),
    }


def find_timezone(query: str) -> dict[str, Any]:
    """IANA 시간대 이름을 부분 문자열로 검색한다.

    Args:
        query: 검색어 (예: Seoul, New_York, Europe)
    """
    needle = query.strip().lower()
    if not needle:
        return _error("검색어가 비어 있습니다.")

    matches = sorted(z for z in available_timezones() if needle in z.lower())
    return {
        "검색어": query,
        "전체건수": len(matches),
        "결과": matches[:MAX_TIMEZONE_MATCHES],
        **(
            {"안내": f"{MAX_TIMEZONE_MATCHES}건만 표시했습니다. 검색어를 좁히세요."}
            if len(matches) > MAX_TIMEZONE_MATCHES
            else {}
        ),
    }

