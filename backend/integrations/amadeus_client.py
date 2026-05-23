"""Amadeus client: hotel search, location conversion."""

import re
import asyncio
from datetime import datetime
from typing import List

from amadeus import ResponseError

from ..config.settings import amadeus, llm
from ..models import HotelOption


async def search_amadeus_hotels(city_code: str, check_in_date: str, check_out_date: str, adults: int) -> List[HotelOption]:
    """Search hotels via Amadeus API with fallback logic."""
    print(f"Amadeus: Searching {city_code}")

    if not amadeus:
        print("Amadeus client not initialized")
        return []

    try:
        loop = asyncio.get_running_loop()

        # Step 1: Get hotel IDs in the city
        list_response = await loop.run_in_executor(
            None,
            lambda: amadeus.reference_data.locations.hotels.by_city.get(cityCode=city_code, radius=5),
        )

        if not list_response.data:
            print(f"Amadeus: No hotels found for {city_code}")
            return []

        hotel_ids = [hotel['hotelId'] for hotel in list_response.data[:5]]
        print(f"Amadeus: Found {len(hotel_ids)} hotel IDs")

        # Step 2: Validate date format
        try:
            datetime.strptime(check_in_date, '%Y-%m-%d')
            datetime.strptime(check_out_date, '%Y-%m-%d')
        except ValueError as e:
            print(f"Invalid date format: {e}")
            return []

        # Step 3: Get offers for hotels
        try:
            offer_response = await loop.run_in_executor(
                None,
                lambda: amadeus.shopping.hotel_offers_search.get(
                    hotelIds=','.join(hotel_ids),
                    checkInDate=check_in_date,
                    checkOutDate=check_out_date,
                    adults=adults,
                    roomQuantity=1,
                    currency='USD',
                ),
            )
        except Exception as api_error:
            print(f"Amadeus API error: {api_error}")
            return await fallback_individual_hotel_search(hotel_ids[:3], check_in_date, check_out_date, adults)

        offers = []
        if offer_response.data:
            for hotel_offer in offer_response.data:
                if not hotel_offer.get('available', True):
                    continue

                hotel_info = hotel_offer.get('hotel', {})
                offer_list = hotel_offer.get('offers', [])

                if not offer_list:
                    continue

                offer = offer_list[0]
                price_info = offer.get('price', {})

                offers.append(HotelOption(
                    name=hotel_info.get('name', 'N/A'),
                    category=f"{hotel_info.get('rating', 'N/A')}-star",
                    price_per_night=f"{price_info.get('total', 'N/A')} {price_info.get('currency', 'USD')}",
                    source="Amadeus",
                ))

        print(f"Amadeus: {len(offers)} hotels found")
        return offers

    except ResponseError as e:
        print(f"Amadeus error: {e}")
        return []
    except Exception as e:
        print(f"Unexpected error: {e}")
        return []


async def fallback_individual_hotel_search(hotel_ids: List[str], check_in_date: str, check_out_date: str, adults: int) -> List[HotelOption]:
    """Fallback: Search hotels individually when batch search fails."""
    print("Using fallback individual hotel search")

    offers = []
    loop = asyncio.get_running_loop()

    for hotel_id in hotel_ids:
        try:
            offer_response = await loop.run_in_executor(
                None,
                lambda: amadeus.shopping.hotel_offers_by_hotel.get(
                    hotelId=hotel_id,
                    checkInDate=check_in_date,
                    checkOutDate=check_out_date,
                    adults=adults,
                ),
            )

            if offer_response.data and offer_response.data.get('offers'):
                hotel_info = offer_response.data.get('hotel', {})
                offer = offer_response.data['offers'][0]
                price_info = offer.get('price', {})

                offers.append(HotelOption(
                    name=hotel_info.get('name', 'N/A'),
                    category=f"{hotel_info.get('rating', 'N/A')}-star",
                    price_per_night=f"{price_info.get('total', 'N/A')} {price_info.get('currency', 'USD')}",
                    source="Amadeus",
                ))

        except Exception as e:
            print(f"Individual search failed for {hotel_id}: {e}")
            continue

    return offers


async def location_to_airport_code(location_name: str) -> str:
    """Convert location name to IATA airport code using LLM."""
    if not location_name:
        return ""

    if len(location_name) == 3 and location_name.isalpha() and location_name.isupper():
        return location_name

    conversion_prompt = f"""
    Convert this location to the main international airport IATA code.

    Examples:
    - "Seoul" -> "ICN"
    - "Tokyo" -> "NRT"
    - "Paris" -> "CDG"
    - "New York" -> "JFK"
    - "London" -> "LHR"

    Location: "{location_name}"
    IATA Code:
    """

    try:
        response = await llm.ainvoke(conversion_prompt)
        airport_code = response.content.strip().upper()

        if len(airport_code) == 3 and airport_code.isalpha():
            return airport_code
        codes = re.findall(r'[A-Z]{3}', response.content.upper())
        return codes[0] if codes else location_name

    except Exception as e:
        print(f"Location conversion failed for {location_name}: {e}")
        return location_name


async def location_to_city_code(location_name: str) -> str:
    """Convert location to city code for hotel search."""
    conversion_prompt = f"""
    Convert this location to the appropriate city code for hotel booking.

    Examples:
    - "Seoul" -> "SEL"
    - "ICN" -> "SEL" (Seoul city for hotels)
    - "Tokyo" -> "TYO"
    - "NRT" -> "TYO" (Tokyo city for hotels)
    - "Paris" -> "PAR"
    - "CDG" -> "PAR" (Paris city for hotels)

    Location: "{location_name}"
    City Code:
    """

    try:
        response = await llm.ainvoke(conversion_prompt)
        city_code = response.content.strip().upper()

        if len(city_code) == 3 and city_code.isalpha():
            return city_code
        codes = re.findall(r'[A-Z]{3}', response.content.upper())
        return codes[0] if codes else location_name

    except Exception as e:
        print(f"City code conversion failed for {location_name}: {e}")
        return location_name


async def location_to_coordinates(location_name: str) -> tuple:
    """Convert location to city center coordinates for activity search."""
    conversion_prompt = f"""
    Provide the city center coordinates for this location.

    Examples:
    - "Seoul" -> 37.566, 126.978
    - "ICN" -> 37.566, 126.978 (Seoul city center)
    - "Tokyo" -> 35.676, 139.650
    - "Paris" -> 48.8566, 2.3522

    Location: "{location_name}"
    Coordinates:
    """

    try:
        response = await llm.ainvoke(conversion_prompt)
        coords_text = response.content.strip()

        coords = re.findall(r'-?\d+\.?\d*', coords_text)
        if len(coords) >= 2:
            return float(coords[0]), float(coords[1])
        return 0.0, 0.0

    except Exception as e:
        print(f"Coordinate conversion failed for {location_name}: {e}")
        return 0.0, 0.0
