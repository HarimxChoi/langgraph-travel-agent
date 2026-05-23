"""Hotel search tool: combines Amadeus + Hotelbeds."""

import asyncio
from typing import List

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from ..integrations.amadeus_client import search_amadeus_hotels, location_to_city_code
from ..integrations.hotelbeds_client import search_hotelbeds_hotels
from ..models import HotelOption


class HotelSearchArgs(BaseModel):
    """Hotel search parameters."""
    city_code: str = Field(description="City IATA code (e.g., 'PAR', 'NYC')")
    check_in_date: str = Field(description="Check-in date (YYYY-MM-DD)")
    check_out_date: str = Field(description="Check-out date (YYYY-MM-DD)")
    adults: int = Field(description="Number of guests", default=1)


@tool(args_schema=HotelSearchArgs)
async def search_and_compare_hotels(
    city_code: str,
    check_in_date: str,
    check_out_date: str,
    adults: int = 1,
) -> List[HotelOption]:
    """Search hotels across multiple providers (Amadeus + Hotelbeds)."""
    actual_city_code = await location_to_city_code(city_code)
    print(f"Hotel search: {city_code} -> {actual_city_code}")

    amadeus_task = search_amadeus_hotels(actual_city_code, check_in_date, check_out_date, adults)
    hotelbeds_task = search_hotelbeds_hotels(actual_city_code, check_in_date, check_out_date, adults)

    results = await asyncio.gather(amadeus_task, hotelbeds_task)

    combined_list = []
    for result_list in results:
        combined_list.extend(result_list)

    print(f"Total hotels found: {len(combined_list)}")
    return combined_list
