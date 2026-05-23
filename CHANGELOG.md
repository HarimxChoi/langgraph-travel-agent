# Changelog

## v0.2.0 - production refactor

- Split `agent_graph.py` (1707 lines) into 7 modules: `models`, `integrations`, `tools`, `graph`, `utils`, `config`, `api`
- Move FastAPI app to `backend/api/main.py`
- Centralize env loading and client init in `backend/config/settings.py`
- README v2 with architecture diagram and integration matrix
- CI workflow (ruff)

## v0.1.0 - initial

- Multi-agent travel booking with Amadeus, Hotelbeds, Twilio, HubSpot
- Async parallel tool execution
- LLM-driven package generation (Budget / Balanced / Premium)
- Human-in-the-loop customer-info form
