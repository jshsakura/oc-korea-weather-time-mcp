"""기상청 원시 item 목록 → LLM 이 그대로 읽을 수 있는 구조로 정리."""

from __future__ import annotations

from typing import Any

from . import codes

# 실황은 시각이 하나뿐이라 묶을 필요가 없다
_OBSERVATION_TIME_KEYS = ("baseDate", "baseTime")
_FORECAST_TIME_KEYS = ("fcstDate", "fcstTime")


def _is_numeric(value: str) -> bool:
    try:
        float(value)
    except ValueError:
        return False
    return True


def _readable_value(category: str, raw: str) -> str:
    """원시 값을 사람이 읽는 문자열로.

    기상청은 강수량 자리에 `강수없음`·`1mm 미만` 같은 **문자열**을 섞어 보낸다.
    수치일 때만 단위를 붙인다 — 안 그러면 `강수없음mm` 이 된다.
    """
    decoded = codes.decode(category, raw)
    if decoded != raw:  # 코드 매핑이 적용됐으면 단위를 붙이지 않는다
        return decoded
    unit = codes.unit_of(category)
    if unit and _is_numeric(decoded):
        return f"{decoded}{unit}"
    return decoded


def format_observation(items: list[dict[str, Any]]) -> dict[str, Any]:
    """초단기실황 — 현재 관측값 한 벌."""
    if not items:
        return {"관측시각": None, "관측값": {}}

    first = items[0]
    observed = {
        codes.label_of(item["category"]): _readable_value(
            item["category"], str(item.get("obsrValue", ""))
        )
        for item in items
        if "category" in item
    }
    return {
        "관측시각": f"{first.get('baseDate', '')} {first.get('baseTime', '')}",
        "격자": {"nx": first.get("nx"), "ny": first.get("ny")},
        "관측값": observed,
    }


def format_forecast(items: list[dict[str, Any]], limit: int | None = None) -> dict[str, Any]:
    """예보 — 예보시각별로 묶는다.

    Args:
        limit: 앞에서부터 몇 개 시각까지만 돌려줄지. None 이면 전부.
    """
    if not items:
        return {"발표시각": None, "예보": []}

    first = items[0]
    grouped: dict[str, dict[str, str]] = {}
    order: list[str] = []

    for item in items:
        category = item.get("category")
        if not category:
            continue
        slot = f"{item.get('fcstDate', '')} {item.get('fcstTime', '')}"
        if slot not in grouped:
            grouped[slot] = {}
            order.append(slot)
        grouped[slot][codes.label_of(category)] = _readable_value(
            category, str(item.get("fcstValue", ""))
        )

    slots = order if limit is None else order[:limit]
    return {
        "발표시각": f"{first.get('baseDate', '')} {first.get('baseTime', '')}",
        "격자": {"nx": first.get("nx"), "ny": first.get("ny")},
        "예보": [{"시각": slot, **grouped[slot]} for slot in slots],
    }
