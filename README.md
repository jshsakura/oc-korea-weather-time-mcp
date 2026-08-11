# oc-korea-weather-time-mcp

기상청 날씨와 시간대 조회를 제공하는 MCP 서버.

```bash
uvx oc-korea-weather-time-mcp
```

## 왜 만들었나

- 기존 `korea-weather-mcp` 는 개인 개발자가 2025-09 에 v0.1.0 한 번 올리고 방치했고
  초단기실황만 지원한다.
- 자격증명(기상청 서비스 키)을 다루는 물건은 직접 관리한다는 방침.
- 날씨와 시간은 어차피 같이 쓰인다 — "내일 아침 서울 날씨" 를 답하려면 둘 다 필요하다.

## 툴

### 날씨 (기상청 단기예보 조회서비스)

| 툴 | 출처 API | 범위 |
|---|---|---|
| `get_current_weather(location="")` | 초단기실황 | 지금 관측값 |
| `get_hourly_forecast(location="", hours=6)` | 초단기예보 | 앞으로 6시간 |
| `get_daily_forecast(location="", slots=24)` | 단기예보 | 앞으로 3일 |

`location` 은 지역명(`서울`·`인천`·`부산광역시`), 부분 일치(`성남시 분당구`),
또는 `위도,경도` 문자열을 받는다. 생략하면 `KMA_DEFAULT_LOCATION`(기본 `서울`).
모르는 지역이면 오류 응답에 지원 목록을 실어 보낸다 — 목록 전용 툴을 두면
매 요청 프롬프트에 비용이 붙기 때문이다.

강수확률(`POP`)과 일최저/최고기온은 **단기예보에만** 있다.

### 시간

| 툴 | 하는 일 |
|---|---|
| `get_current_time(timezone="Asia/Seoul")` | 지정 시간대의 현재 시각 |
| `convert_time(time, from_timezone, to_timezone)` | 시간대 간 변환 |
| `find_timezone(query)` | IANA 시간대 이름 검색 |

시간 쪽은 파이썬 표준 `zoneinfo` 만 쓴다. 외부 의존이 없다.

## 설정

```bash
export KMA_SERVICE_KEY="발급받은-디코딩-키"    # 날씨 툴에 필수
export KMA_DEFAULT_LOCATION="서울"             # 선택
```

서비스 키는 [공공데이터포털](https://www.data.go.kr) → `기상청_단기예보 조회서비스`
활용신청 → **일반 인증키(Decoding)**. 인코딩 키(`%2B` 가 섞인 것)를 넣으면
이중 인코딩으로 인증에 실패한다.

**키는 환경변수로만 받는다.** `httpx` 가 INFO 레벨에서 요청 URL 전체를 찍는데
쿼리스트링에 `serviceKey` 가 들어 있어 키가 로그에 평문으로 남는다.
그래서 `httpx`·`httpcore` 로거를 WARNING 으로 낮춘다.

### 한쪽만 쓰기

툴 정의는 매 요청마다 프롬프트에 실린다. 필요 없는 쪽은 끄면 그만큼 가벼워진다.

```bash
export OC_KOREA_MCP_TIME=0        # 날씨 툴 3개만
export OC_KOREA_MCP_WEATHER=0     # 시간 툴 3개만
```

## 등록

```bash
# Claude Code
claude mcp add oc-korea-weather-time \
  -e KMA_SERVICE_KEY=발급받은-키 \
  -- uvx oc-korea-weather-time-mcp

# Hermes
hermes mcp add oc-korea-weather-time \
  --command uvx --args oc-korea-weather-time-mcp \
  --env KMA_SERVICE_KEY=발급받은-키
```

## 설계 메모

- **격자 변환** — 기상청 API 는 위경도를 안 받고 자체 격자(nx, ny)를 쓴다.
  Lambert Conformal Conic 투영, 파라미터는 기상청 고시값.
  서울(60,127)·부산(98,76)·제주(53,38) 표준 검증값과 일치를 확인했다.
- **코드 해석** — API 는 `SKY=1` 같은 숫자만 준다. 그대로 넘기면 LLM 이 해석을
  지어내므로 서버에서 `맑음` 으로 풀어 넘긴다. 매핑에 없는 코드는 임의 해석하지 않고
  `알 수 없음(값)` 으로 표시한다.
- **단위** — 기상청은 강수량 자리에 `강수없음` 같은 **문자열**을 섞어 보낸다.
  수치일 때만 단위를 붙인다.
- **발표시각** — 초단기는 매시 40분 생성이라 그 전이면 한 시간 전 발표분을 쓴다.
  단기예보는 하루 8회(02·05·08·11·14·17·20·23시) 발표.
- **오류를 예외로 던지지 않는다.** 툴은 `{"오류": "..."}` 를 돌려준다.
  LLM 이 다음 행동을 정할 수 있어야 한다.

## 개발

```bash
uv venv && uv pip install -e . pytest
uv run pytest tests/ -q
```

외부 호출 없이 격자 변환·발표시각·지역 해석·표시 변환을 검증한다.
API 호출 경로는 네트워크와 키가 필요하므로 테스트에서 제외했다.

## 라이선스

MIT
