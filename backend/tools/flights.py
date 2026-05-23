"""Flight search tool."""

import asyncio
from typing import List, Optional

from amadeus import ResponseError
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from ..config.settings import amadeus
from ..integrations.amadeus_client import location_to_airport_code
from ..models import FlightOption
from ..utils.helpers import parse_and_prepare_offers, find_closest_flight


class FlightSearchArgs(BaseModel):
    """Flight search parameters."""
    originLocationCode: str = Field(description="Departure city IATA code")
    destinationLocationCode: str = Field(description="Arrival city IATA code")
    departureDate: str = Field(description="Departure date (YYYY-MM-DD)")
    returnDate: Optional[str] = Field(description="Return date (YYYY-MM-DD)")
    adults: int = Field(description="Number of adult passengers", default=1)
    currencyCode: str = Field(description="Preferred currency", default="USD")


@tool(args_schema=FlightSearchArgs)
async def search_flights(
    originLocationCode: str,
    destinationLocationCode: str,
    departureDate: str,
    returnDate: Optional[str] = None,
    adults: int = 1,
    travelClass: Optional[str] = None,
    departureTime: Optional[str] = None,
    arrivalTime: Optional[str] = None,
    currencyCode: str = "USD",
) -> List[FlightOption]:
    """Search for flight offers using Amadeus API."""
    print(f"Flight search: {originLocationCode} -> {destinationLocationCode}")

    try:
        origin_task = location_to_airport_code(originLocationCode)
        destination_task = location_to_airport_code(destinationLocationCode)
        actual_origin, actual_destination = await asyncio.gather(origin_task, destination_task)
        print(f"Converted to: {actual_origin} -> {actual_destination}")
    except Exception as e:
        print(f"Location conversion failed: {e}")
        return [FlightOption(airline="Location Error", price="N/A", departure_time="N/A", arrival_time=str(e))]

    if not amadeus:
        return [FlightOption(airline="Error", price="N/A", departure_time="N/A", arrival_time="Amadeus client not available")]

    try:
        search_params = {
            'originLocationCode': actual_origin,
            'destinationLocationCode': actual_destination,
            'departureDate': departureDate,
            'adults': adults,
            'nonStop': False,
            'currencyCode': currencyCode,
            'max': 25,
        }

        if returnDate:
            search_params['returnDate'] = returnDate

        if travelClass and travelClass.upper() in ["ECONOMY", "PREMIUM_ECONOMY", "BUSINESS", "FIRST"]:
            search_params['travelClass'] = travelClass.upper()

        time_windows = {
            "morning": "06:00-12:00",
            "afternoon": "12:00-18:00",
            "evening": "18:00-23:59",
        }
        if departureTime and departureTime.lower() in time_windows:
            search_params['departureWindow'] = time_windows[departureTime.lower()]
        if arrivalTime and arrivalTime.lower() in time_windows:
            search_params['arrivalWindow'] = time_windows[arrivalTime.lower()]

        print(f"Calling Amadeus with params: {search_params}")
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None,
            lambda: amadeus.shopping.flight_offers_search.get(**search_params),
        )

        if not response.data:
            return []

        all_offers = parse_and_prepare_offers(response.result)

        if not all_offers:
            return []

        final_sorted_offers = sorted(all_offers, key=lambda x: x['price_numeric'])

        if departureTime and ":" in departureTime:
            print(f"Re-sorting by proximity to {departureTime}")
            final_sorted_offers = find_closest_flight(final_sorted_offers, departureTime)

        top_3_offers = [item['option_object'] for item in final_sorted_offers[:3]]

        print(f"Returning top 3 of {len(all_offers)} flight options")
        return top_3_offers

    except ResponseError as error:
        print(f"Amadeus API error: {error}")
        return [FlightOption(airline="API Error", price="N/A", departure_time="N/A", arrival_time=str(error))]
    except Exception as e:
        print(f"Flight search error: {e}")
        return [FlightOption(airline="System Error", price="N/A", departure_time="N/A", arrival_time=str(e))]
