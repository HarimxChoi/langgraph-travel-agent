"""Hotelbeds client: hotel search with X-Signature auth."""

import hashlib
import time
from typing import List, Optional

import httpx

from ..config.settings import HOTELBEDS_API_KEY, HOTELBEDS_API_SECRET
from ..models import HotelOption


def get_hotelbeds_headers() -> Optional[dict]:
    """Generate X-Signature authentication for Hotelbeds API."""
    api_key = HOTELBEDS_API_KEY
    secret = HOTELBEDS_API_SECRET
    if not api_key or not secret:
        return None

    utc_timestamp = int(time.time())
    signature = hashlib.sha256(f"{api_key}{secret}{utc_timestamp}".encode()).hexdigest()

    return {
        "Api-key": api_key,
        "X-Signature": signature,
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
    }


async def search_hotelbeds_hotels(city_code: str, check_in_date: str, check_out_date: str, adults: int = 1) -> List[HotelOption]:
    """Search real-time hotel availability on Hotelbeds."""
    print(f"Hotelbeds: Searching {city_code} ({check_in_date} to {check_out_date})")

    headers = get_hotelbeds_headers()
    if not headers:
        print("Hotelbeds API keys not configured")
        return []

    api_url = "https://api.test.hotelbeds.com/hotel-api/1.0/hotels"

    request_body = {
        "stay": {"checkIn": check_in_date, "checkOut": check_out_date},
        "occupancies": [{"rooms": 1, "adults": adults, "children": 0}],
        "destination": {"code": city_code},
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(api_url, headers=headers, json=request_body)
            response.raise_for_status()
            data = response.json()

            hotels = []
            hotels_data = data.get('hotels', {})
            hotel_list = hotels_data.get('hotels', []) if isinstance(hotels_data, dict) else hotels_data

            for hotel in hotel_list[:5]:
                min_rate = hotel.get('minRate', 'N/A')
                currency = hotel.get('currency', 'USD')

                hotels.append(HotelOption(
                    name=hotel.get('name', 'N/A'),
                    category=hotel.get('categoryName', 'N/A'),
                    price_per_night=f"{min_rate} {currency}",
                    source="Hotelbeds",
                ))

            print(f"Hotelbeds: {len(hotels)} hotels found")
            return hotels

    except httpx.HTTPStatusError as e:
        print(f"Hotelbeds API error: {e.response.status_code}")
        return []
    except Exception as e:
        print(f"Hotelbeds error: {e}")
        return []
