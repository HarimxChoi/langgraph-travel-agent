"""Travel plan analysis: extract structured TravelPlan from natural-language request."""

from datetime import datetime

from ..config.settings import llm
from ..models import TravelPlan


async def enhanced_travel_analysis(user_request: str) -> TravelPlan:
    """Extract structured trip information from a natural-language request."""
    analysis_prompt = f"""
    You are a world-class travel analyst AI. Extract structured trip information
    from the user's request and output valid JSON matching the provided schema.

    **User Request:** "{user_request}"

    **Today's Date:** {datetime.now().strftime('%Y-%m-%d')}

    **Instructions:**

    1. **Determine User Intent (`user_intent`):**
        - "full_plan": Combination of flights, hotels, or activities
        - "flights_only": Only asking for flights
        - "hotels_only": Only asking for hotels
        - "activities_only": Only asking for activities

    2. **Extract Core Details:**
        - `origin`: Starting location (can be null)
        - `destination`: Final destination (mandatory)
        - `departure_date` & `return_date`: Calculate absolute dates in YYYY-MM-DD format
        - `duration_days`: Calculate days between departure and return
        - `adults`: Number of travelers (default 1)

    3. **Extract Preferences:**
        - `travel_class`: Look for "business", "first class", etc. (default "ECONOMY")
        - `departure_time_pref` & `arrival_time_pref`: Look for time preferences
        - `total_budget`: Extract monetary value as float

    **CRITICAL: Output MUST be valid JSON matching this schema:**
    {TravelPlan.model_json_schema()}

    **JSON Output:**
    """

    try:
        response = await llm.ainvoke(analysis_prompt)

        content = response.content.strip()
        if content.startswith('```json'):
            content = content[7:]
        if content.endswith('```'):
            content = content[:-3]
        content = content.strip()

        extracted_plan = TravelPlan.model_validate_json(content)
        print(f"Travel plan extracted: intent={extracted_plan.user_intent}")
        return extracted_plan

    except Exception as e:
        print(f"Travel analysis failed: {e}")
        raise ValueError(f"Could not understand the travel request: {e}")
