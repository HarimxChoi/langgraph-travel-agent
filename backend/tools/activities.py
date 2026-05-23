"""Activity search tool."""

import asyncio
from typing import List

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from ..config.settings import amadeus
from ..integrations.amadeus_client import location_to_coordinates
from ..models import ActivityOption


class ActivitySearchArgs(BaseModel):
    """Activity search parameters."""
    city_name: str = Field(description="Full city name for activity search (e.g., 'Paris', 'London')")


@tool(args_schema=ActivitySearchArgs)
async def search_activities_by_city(city_name: str) -> List[ActivityOption]:
    """Search for activities and attractions in a city."""
    print(f"Activity search: {city_name}")

    lat, lng = await location_to_coordinates(city_name)
    print(f"Coordinates: ({lat}, {lng})")

    if lat == 0.0 and lng == 0.0:
        return [ActivityOption(name="Error", description=f"Could not determine coordinates for {city_name}", price="N/A")]

    try:
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None,
            lambda: amadeus.shopping.activities.get(latitude=lat, longitude=lng, radius=15),
        )

        qualified_activities = []
        for act in response.data[:10]:
            price_info = act.get('price')
            description = act.get('shortDescription') or act.get('description')
            activity_name = act.get('name', 'Unnamed Activity')

            if price_info or description:
                if price_info:
                    amount = price_info.get('amount', 'N/A')
                    currency = price_info.get('currencyCode', '')
                    price_str = f"{amount} {currency}".strip()
                else:
                    price_str = "Price on request"

                if not description:
                    description = "Experience this popular local activity"

                qualified_activities.append(ActivityOption(
                    name=activity_name,
                    description=description,
                    price=price_str,
                    location=city_name,
                ))

            if len(qualified_activities) >= 8:
                break

        if not qualified_activities:
            return [ActivityOption(name="No activities found", description="Unable to find activities", price="N/A")]

        print(f"Found {len(qualified_activities)} activities")
        return qualified_activities

    except Exception as e:
        print(f"Activity search failed: {e}")
        return [ActivityOption(name="Error", description=f"Search failed: {e}", price="N/A")]
