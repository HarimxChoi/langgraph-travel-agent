"""Graph state."""

import operator
from typing import TypedDict, Annotated, List, Optional, Dict, Any
from langchain_core.messages import AnyMessage

from ..models import TravelPlan


class TravelAgentState(TypedDict):
    """Graph state with complete conversation context."""
    messages: Annotated[List[AnyMessage], operator.add]
    travel_plan: Optional[TravelPlan]
    user_preferences: Optional[Dict[str, Any]]
    form_to_display: Optional[str]
    current_step: str  # "initial", "tools_called", "synthesizing", "complete"
    errors: List[str]
    customer_info: Optional[Dict[str, str]]
    trip_details: Optional[Dict[str, Any]]
    original_request: Optional[str]
    is_continuation: Optional[bool]
