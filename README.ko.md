# langgraph-travel-agent

[English](./README.md) | 한국어

여행 플래닝용 production-ready LangGraph multi-agent 시스템. Amadeus, Hotelbeds, Twilio, HubSpot에 걸친 비동기 병렬 tool orchestration.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

![Demo](demo.png)

## What it does

- 자연어 여행 요청 -> 구조화된 `TravelPlan`
- 항공편 (Amadeus), 호텔 (Amadeus + Hotelbeds), 액티비티 (Amadeus) 병렬 검색
- LLM 기반 패키지 생성 (Budget / Balanced / Premium)
- HITL (human-in-the-loop): 대화 중간에 고객 정보 폼 삽입
- CRM (HubSpot) + SMS (Twilio) 연동

## Architecture

```
┌──────────────────────────────────────────────────────┐
│  FastAPI server (backend/api/main.py)                │
│    POST /chat -> task_id (async, background)         │
│    GET  /chat/status/{task_id}                       │
│    POST /chat/customer-info                          │
└────────────────────────┬─────────────────────────────┘
                         ▼
┌──────────────────────────────────────────────────────┐
│  LangGraph                                           │
│    call_model_and_tools  --collecting_info--> END    │
│    call_model_and_tools  --synthesizing----> synth   │
│    synthesize_results    -----------------> END      │
└────────────────────────┬─────────────────────────────┘
                         ▼
┌──────────────────────────────────────────────────────┐
│  Tools (parallel asyncio.gather)                     │
│    search_flights             Amadeus                │
│    search_and_compare_hotels  Amadeus + Hotelbeds    │
│    search_activities_by_city  Amadeus                │
│    send_sms_notification      Twilio                 │
│    send_to_hubspot            HubSpot                │
└──────────────────────────────────────────────────────┘
```

## Layout

```
backend/
  api/main.py             FastAPI app
  config/settings.py      env loading, client init
  models/                 FlightOption, HotelOption, ActivityOption, TravelPackage, TravelPlan
  integrations/
    amadeus_client.py     호텔 검색, location 변환 (airport / city / coords)
    hotelbeds_client.py   X-Signature auth 호텔 검색
  tools/
    flights.py            @tool search_flights
    hotels.py             @tool search_and_compare_hotels
    activities.py         @tool search_activities_by_city
    sms.py                @tool send_sms_notification
    crm.py                @tool send_to_hubspot
  graph/
    state.py              TravelAgentState
    analysis.py           enhanced_travel_analysis (request -> TravelPlan)
    nodes.py              call_model_node, synthesize_results_node, generate_travel_packages
    builder.py            노드 + conditional edges 연결
  utils/helpers.py        offer 파싱, time 정렬, sampling, 기본 날짜
frontend/travel-widget/   React widget (별도 패키지)
tests/                    pytest
```

## Quick Start

```bash
git clone https://github.com/HarimxChoi/langgraph-travel-agent
cd langgraph-travel-agent
pip install -r requirements.txt

cp env.example .env
# GOOGLE_API_KEY, AMADEUS_API_KEY, AMADEUS_API_SECRET 채우기

uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload
```

채팅 요청 POST:

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "4-day trip from Seoul to Paris, $3000 budget", "thread_id": "demo-001"}'
```

이후 `/chat/status/{task_id}`를 status가 `completed`가 될 때까지 폴링.

## Integration matrix

| Service | 필수 | 용도 |
|---------|----------|----------|
| Google Gemini | yes | LLM (분석, 패키지 생성, 최종 응답) |
| Amadeus | yes | 항공편, 호텔, 액티비티 |
| Hotelbeds | optional | 추가 호텔 인벤토리 |
| Twilio | optional | SMS 알림 |
| HubSpot | optional | CRM deal 생성 |

## Notes

- 외부 API 호출 전부 `asyncio.gather`로 병렬 (예: 항공편 + 호텔 + 액티비티 한 라운드트립).
- Conformal logic은 호텔에 Amadeus city code, 항공편에 IATA code 사용. LLM이 자동 변환.
- 고객 정보 폼은 첫 턴에서 트리거 (state: `collecting_info`). 이후 턴은 저장된 정보를 주입.
- HubSpot 대신 다른 CRM을 쓰려면 `backend/tools/crm.py`의 payload / endpoint만 교체.

## License

MIT
