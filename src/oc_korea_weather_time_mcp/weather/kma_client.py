"""기상청 단기예보 조회서비스 API 클라이언트.

공공데이터포털(data.go.kr)의 `VilageFcstInfoService_2.0` 를 호출한다.
서비스 키는 환경변수 `KMA_SERVICE_KEY` 로만 받는다 — 코드에 넣지 않는다.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Final, Literal

import httpx

from .grid import GridPoint

# httpx 는 INFO 로 요청 URL 전체를 찍는다 — 쿼리스트링에 serviceKey 가 들어 있어
# 서비스 키가 로그에 평문으로 남는다. 이 서버에서는 올려 보내지 않는다.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

BASE_URL: Final[str] = (
    "https://apis.data.go.kr/1360000/VilageFcstInfoService_2.0"
)
SERVICE_KEY_ENV: Final[str] = "KMA_SERVICE_KEY"

REQUEST_TIMEOUT_SECONDS: Final[float] = 15.0
MAX_ROWS: Final[int] = 1000

KST: Final[timezone] = timezone(timedelta(hours=9))

# 초단기실황/초단기예보는 매시 40분에 생성된다. 그 전이면 한 시간 전 것을 쓴다.
ULTRA_SHORT_PUBLISH_MINUTE: Final[int] = 40
# 단기예보 발표 시각 (KST)
VILLAGE_BASE_HOURS: Final[tuple[int, ...]] = (2, 5, 8, 11, 14, 17, 20, 23)
# 발표 후 자료가 뜨기까지의 여유
VILLAGE_PUBLISH_DELAY_MINUTES: Final[int] = 10

Endpoint = Literal["getUltraSrtNcst", "getUltraSrtFcst", "getVilageFcst"]


class KmaError(RuntimeError):
    """기상청 API 호출 실패."""


class MissingServiceKeyError(KmaError):
    """서비스 키가 설정되지 않음."""


@dataclass(frozen=True)
class BaseTime:
    """API 가 요구하는 발표일자·발표시각."""

    base_date: str  # YYYYMMDD
    base_time: str  # HHMM


def _now_kst() -> datetime:
    return datetime.now(KST)


def resolve_ultra_short_base(now: datetime | None = None) -> BaseTime:
    """초단기(실황·예보)용 발표 시각을 고른다."""
    moment = now or _now_kst()
    if moment.minute < ULTRA_SHORT_PUBLISH_MINUTE:
        moment = moment - timedelta(hours=1)
    return BaseTime(moment.strftime("%Y%m%d"), moment.strftime("%H00"))


def resolve_village_base(now: datetime | None = None) -> BaseTime:
    """단기예보용 발표 시각을 고른다 — 하루 8회 발표 중 가장 최근 것."""
    moment = now or _now_kst()
    threshold = moment - timedelta(minutes=VILLAGE_PUBLISH_DELAY_MINUTES)

    for hour in reversed(VILLAGE_BASE_HOURS):
        if threshold.hour >= hour:
            return BaseTime(threshold.strftime("%Y%m%d"), f"{hour:02d}00")

    # 02시 발표 전이면 전날 23시 발표분
    yesterday = threshold - timedelta(days=1)
    return BaseTime(yesterday.strftime("%Y%m%d"), "2300")


def _service_key() -> str:
    key = os.environ.get(SERVICE_KEY_ENV, "").strip()
    if not key:
        raise MissingServiceKeyError(
            f"환경변수 {SERVICE_KEY_ENV} 가 비어 있습니다. "
            "공공데이터포털(data.go.kr)에서 '기상청_단기예보 조회서비스' 활용신청 후 "
            "발급받은 일반 인증키(Decoding)를 넣으세요."
        )
    return key


def _check_response_header(payload: dict[str, Any]) -> None:
    """기상청은 HTTP 200 에 에러 코드를 실어 보낸다. 헤더를 반드시 확인한다."""
    header = (payload.get("response") or {}).get("header") or {}
    code = header.get("resultCode")
    message = header.get("resultMsg", "")
    if code not in (None, "00"):
        raise KmaError(f"기상청 API 오류 {code}: {message}")


def _extract_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    body = (payload.get("response") or {}).get("body") or {}
    items = (body.get("items") or {}).get("item")
    if items is None:
        return []
    if isinstance(items, dict):  # 단건이면 dict 로 온다
        return [items]
    return list(items)


async def fetch(
    endpoint: Endpoint,
    grid: GridPoint,
    base: BaseTime,
) -> list[dict[str, Any]]:
    """기상청 엔드포인트를 호출해 item 목록을 돌려준다."""
    params = {
        "serviceKey": _service_key(),
        "pageNo": "1",
        "numOfRows": str(MAX_ROWS),
        "dataType": "JSON",
        "base_date": base.base_date,
        "base_time": base.base_time,
        "nx": str(grid.nx),
        "ny": str(grid.ny),
    }

    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
            response = await client.get(f"{BASE_URL}/{endpoint}", params=params)
            response.raise_for_status()
            payload = response.json()
    except httpx.HTTPStatusError as exc:
        raise KmaError(
            f"기상청 API HTTP {exc.response.status_code} — {endpoint}"
        ) from exc
    except httpx.HTTPError as exc:
        raise KmaError(f"기상청 API 연결 실패 — {exc}") from exc
    except ValueError as exc:
        # 인증키가 틀리면 JSON 대신 XML 에러문서가 온다
        raise KmaError(
            "기상청 응답을 JSON 으로 읽지 못했습니다. "
            f"{SERVICE_KEY_ENV} 가 올바른지(Decoding 키인지) 확인하세요."
        ) from exc

    _check_response_header(payload)
    return _extract_items(payload)
