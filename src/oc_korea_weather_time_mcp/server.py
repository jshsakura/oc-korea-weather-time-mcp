"""oc-korea-weather-time-mcp — 기상청 날씨 + 시간대 MCP 서버.

툴 6개(날씨 3 + 시간 3). MCP 툴 정의는 매 요청마다 프롬프트에 실리므로
필요 없는 쪽은 환경변수로 꺼서 비용을 줄일 수 있다.
"""

from __future__ import annotations

import os
from typing import Any, Final

from mcp.server import MCPServer

from .timezone import tools as time_tools
from .weather import formatter, kma_client, places
from .weather.grid import OutOfServiceAreaError, to_grid
from .weather.kma_client import KmaError
from .weather.places import UnknownPlaceError

SERVER_NAME: Final[str] = "oc-korea-weather-time"

DEFAULT_ULTRA_SHORT_SLOTS: Final[int] = 6
DEFAULT_VILLAGE_SLOTS: Final[int] = 24
MAX_SLOTS: Final[int] = 100

# 한쪽만 쓰고 싶을 때 — 0/false/no 로 끄면 그쪽 툴 정의가 프롬프트에서 빠진다
ENABLE_WEATHER_ENV: Final[str] = "OC_KOREA_MCP_WEATHER"
ENABLE_TIME_ENV: Final[str] = "OC_KOREA_MCP_TIME"
_DISABLED_VALUES: Final[frozenset[str]] = frozenset({"0", "false", "no", "off"})

mcp = MCPServer(SERVER_NAME)


def _is_enabled(env_name: str) -> bool:
    return os.environ.get(env_name, "1").strip().lower() not in _DISABLED_VALUES


def _error(message: str) -> dict[str, Any]:
    """실패를 예외 대신 구조화해 돌려준다 — LLM 이 다음 행동을 정할 수 있게."""
    return {"오류": message}


def _clamp_slots(value: int, default: int) -> int:
    if value <= 0:
        return default
    return min(value, MAX_SLOTS)


def _locate(location: str):
    place = places.resolve(location)
    return place, to_grid(place.latitude, place.longitude)


# --- 날씨 -------------------------------------------------------------------

if _is_enabled(ENABLE_WEATHER_ENV):

    @mcp.tool()
    async def get_current_weather(location: str = "") -> dict[str, Any]:
        """지금 관측된 날씨를 조회한다 (기상청 초단기실황).

        기온·습도·강수형태·풍향·풍속·1시간 강수량을 돌려준다.

        Args:
            location: 지역명 (예: 서울, 인천, 부산). 생략하면 기본 지역.
                      '위도,경도' 형식도 받는다.
        """
        try:
            place, grid = _locate(location)
            base = kma_client.resolve_ultra_short_base()
            items = await kma_client.fetch("getUltraSrtNcst", grid, base)
        except (UnknownPlaceError, OutOfServiceAreaError, KmaError) as exc:
            return _error(str(exc))
        return {"지역": place.name, **formatter.format_observation(items)}

    @mcp.tool()
    async def get_hourly_forecast(
        location: str = "",
        hours: int = DEFAULT_ULTRA_SHORT_SLOTS,
    ) -> dict[str, Any]:
        """앞으로 6시간까지의 시간별 예보를 조회한다 (기상청 초단기예보).

        Args:
            location: 지역명. 생략하면 기본 지역.
            hours: 돌려받을 시각 개수 (기본 6, 최대 100)
        """
        try:
            place, grid = _locate(location)
            base = kma_client.resolve_ultra_short_base()
            items = await kma_client.fetch("getUltraSrtFcst", grid, base)
        except (UnknownPlaceError, OutOfServiceAreaError, KmaError) as exc:
            return _error(str(exc))
        return {
            "지역": place.name,
            **formatter.format_forecast(
                items, _clamp_slots(hours, DEFAULT_ULTRA_SHORT_SLOTS)
            ),
        }

    @mcp.tool()
    async def get_daily_forecast(
        location: str = "",
        slots: int = DEFAULT_VILLAGE_SLOTS,
    ) -> dict[str, Any]:
        """앞으로 3일까지의 예보를 조회한다 (기상청 단기예보).

        강수확률·일최저/최고기온이 여기에만 있다.

        Args:
            location: 지역명. 생략하면 기본 지역.
            slots: 돌려받을 예보시각 개수 (기본 24, 최대 100)
        """
        try:
            place, grid = _locate(location)
            base = kma_client.resolve_village_base()
            items = await kma_client.fetch("getVilageFcst", grid, base)
        except (UnknownPlaceError, OutOfServiceAreaError, KmaError) as exc:
            return _error(str(exc))
        return {
            "지역": place.name,
            **formatter.format_forecast(
                items, _clamp_slots(slots, DEFAULT_VILLAGE_SLOTS)
            ),
        }


# --- 시간 -------------------------------------------------------------------

if _is_enabled(ENABLE_TIME_ENV):

    @mcp.tool()
    def get_current_time(timezone: str = time_tools.DEFAULT_TIMEZONE) -> dict[str, Any]:
        """지정한 시간대의 현재 시각을 조회한다.

        Args:
            timezone: IANA 시간대 이름 (기본 Asia/Seoul)
        """
        return time_tools.get_current_time(timezone)

    @mcp.tool()
    def convert_time(
        time: str, from_timezone: str, to_timezone: str
    ) -> dict[str, Any]:
        """한 시간대의 시각을 다른 시간대로 변환한다.

        Args:
            time: 변환할 시각. `YYYY-MM-DD HH:MM` 또는 ISO 8601
            from_timezone: 원본 IANA 시간대
            to_timezone: 대상 IANA 시간대
        """
        return time_tools.convert_time(time, from_timezone, to_timezone)

    @mcp.tool()
    def find_timezone(query: str) -> dict[str, Any]:
        """IANA 시간대 이름을 부분 문자열로 검색한다.

        Args:
            query: 검색어 (예: Seoul, New_York, Europe)
        """
        return time_tools.find_timezone(query)


def main() -> None:
    """stdio 트랜스포트로 서버를 띄운다."""
    mcp.run()


if __name__ == "__main__":
    main()
