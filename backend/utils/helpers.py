"""Helper functions: offer parsing, time sorting, default dates, representative sampling."""

from datetime import datetime, timedelta
from typing import List, Dict

from ..models import FlightOption, TravelPlan


def parse_and_prepare_offers(response_data: dict) -> List[Dict]:
    """Parse Amadeus flight search response into sortable format."""
    if 'data' not in response_data or not response_data['data']:
        return []

    prepared_offers = []
    carriers = response_data.get('dictionaries', {}).get('carriers', {})

    for offer in response_data['data']:
        try:
            price_float = float(offer['price']['total'])

            itinerary = offer['itineraries'][0]
            first_segment = itinerary['segments'][0]
            last_segment = itinerary['segments'][-1]

            option_obj = FlightOption(
                airline=carriers.get(first_segment['carrierCode'], first_segment['carrierCode']),
                price=f"{offer['price']['total']} {offer['price']['currency']}",
                departure_time=first_segment['departure']['at'],
                arrival_time=last_segment['arrival']['at'],
                duration=itinerary.get('duration'),
            )

            prepared_offers.append({"price_numeric": price_float, "option_object": option_obj})
        except (ValueError, KeyError, IndexError, TypeError) as e:
            print(f"Skipping malformed flight offer: {e}")
            continue

    return prepared_offers


def find_closest_flight(offers: List[Dict], target_time_str: str) -> List[Dict]:
    """Sort flights by proximity to target departure time."""
    try:
        target_hour = int(target_time_str.split(':')[0])
    except (ValueError, IndexError):
        print(f"Invalid target time: {target_time_str}")
        return offers

    def get_time_difference(prepared_offer):
        try:
            departure_dt = datetime.fromisoformat(prepared_offer['option_object'].departure_time)
            return abs(departure_dt.hour - target_hour)
        except (ValueError, TypeError):
            return float('inf')

    return sorted(offers, key=get_time_difference)


def get_representative_options(options: List, key_attr: str, max_items: int = 7) -> List:
    """Select representative sample (cheapest, mid-range, priciest)."""
    if not options or len(options) <= max_items:
        return options

    try:
        if key_attr == 'price':
            options.sort(key=lambda x: float(getattr(x, key_attr).split(' ')[0]))
    except (ValueError, TypeError, IndexError):
        pass

    cheapest = options[:2]
    most_expensive = options[-2:]
    mid_index = len(options) // 2
    mid_range = options[mid_index - 1: mid_index + 2]

    representative_sample = cheapest + mid_range + most_expensive
    seen = set()
    unique_sample = []
    for item in representative_sample:
        val = getattr(item, key_attr)
        if val not in seen:
            unique_sample.append(item)
            seen.add(val)
    return unique_sample


def calculate_default_dates(travel_plan: TravelPlan) -> tuple:
    """Calculate reasonable default dates for searches."""
    today = datetime.now()
    default_checkin = today + timedelta(days=30)
    default_checkout = default_checkin + timedelta(days=3)

    departure_date = travel_plan.departure_date
    return_date = travel_plan.return_date

    if not departure_date:
        departure_date = default_checkin.strftime('%Y-%m-%d')

    if not return_date:
        if travel_plan.duration_days:
            try:
                dep_dt = datetime.strptime(departure_date, '%Y-%m-%d')
                return_dt = dep_dt + timedelta(days=travel_plan.duration_days)
                return_date = return_dt.strftime('%Y-%m-%d')
            except ValueError:
                return_date = default_checkout.strftime('%Y-%m-%d')
        else:
            return_date = default_checkout.strftime('%Y-%m-%d')

    return departure_date, return_date
