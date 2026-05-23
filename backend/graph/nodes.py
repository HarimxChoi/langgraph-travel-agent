"""Graph nodes: call_model, synthesize_results, generate_travel_packages."""

import asyncio
import json
import traceback
from datetime import datetime
from typing import Dict, List

from langchain_core.messages import AIMessage, ToolMessage

from ..config.settings import llm
from ..models import FlightOption, HotelOption, ActivityOption, TravelPlan, TravelPackage
from ..tools.flights import search_flights
from ..tools.hotels import search_and_compare_hotels
from ..tools.activities import search_activities_by_city
from ..tools.crm import send_to_hubspot
from ..utils.helpers import get_representative_options, calculate_default_dates
from .analysis import enhanced_travel_analysis
from .state import TravelAgentState


async def generate_travel_packages(trip_plan: TravelPlan, all_options: Dict) -> List[TravelPackage]:
    """Generate up to 3 travel packages (Budget, Balanced, Premium)."""
    if not trip_plan.total_budget or trip_plan.total_budget <= 0:
        print("Cannot generate packages without valid budget")
        return []

    sorted_flights = sorted(all_options.get('flights', []), key=lambda x: float(x.price.split(' ')[0]))
    sorted_hotels = sorted(all_options.get('hotels', []), key=lambda x: float(x.price.split(' ')[0]))
    sorted_activities = sorted(all_options.get('activities', []), key=lambda x: float(x.price.split(' ')[0]))

    if not sorted_flights or not sorted_hotels:
        print("Insufficient options for package generation")
        return []

    rep_flights = get_representative_options(sorted_flights, 'price')
    rep_hotels = get_representative_options(sorted_hotels, 'name')
    rep_activities = get_representative_options(sorted_activities, 'name', max_items=10)

    generation_prompt = f"""
    You are an expert travel consultant. Create up to 3 compelling travel packages
    for a client based on their plan and available options.

    **CLIENT'S PLAN:**
    - Destination: {trip_plan.destination}
    - Duration: {trip_plan.duration_days} nights
    - Budget: ${trip_plan.total_budget}

    **AVAILABLE OPTIONS (choose from these lists):**
    - Flights: {json.dumps([f.model_dump() for f in rep_flights])}
    - Hotels: {json.dumps([h.model_dump() for h in rep_hotels])}
    - Activities: {json.dumps([a.model_dump() for a in rep_activities])}

    **YOUR TASK:**
    1. Check if basic trip is possible within budget
    2. Create packages:
       - If cheapest combo is OVER budget: Create ONE "Budget" package only
       - If budget is reasonable: Create THREE packages (Budget, Balanced, Premium)
    3. Each package must contain:
       - EXACTLY ONE flight
       - EXACTLY ONE hotel
       - 0 to 2 activities
    4. Calculate `total_cost` = flight + (hotel x {trip_plan.duration_days} nights) + activities
    5. Calculate `budget_comment` based on difference from total budget
    6. Create creative `name` for each package

    **OUTPUT: Valid JSON array matching this schema:**
    {TravelPackage.model_json_schema()}

    **JSON Array Output:**
    """

    try:
        response = await llm.ainvoke(generation_prompt)
        packages = [TravelPackage.model_validate(p) for p in json.loads(response.content)]

        print(f"Generated {len(packages)} packages")
        return packages

    except Exception as e:
        print(f"Package generation failed: {e}")
        return []


async def call_model_node(state: TravelAgentState) -> dict:
    """Analysis and execution node."""
    print("NODE: Analysis & Execution")

    is_continuation = state.get("is_continuation", False)

    if (not is_continuation and
            not state.get('customer_info') and
            state.get('current_step') in [None, "initial"] and
            len(state.get('messages', [])) <= 1):

        return {
            "messages": [],
            "current_step": "collecting_info",
            "form_to_display": "customer_info",
            "original_request": state['messages'][-1].content,
        }

    user_request = state['messages'][-1].content
    customer_info = state.get('customer_info', {})

    try:
        print("Phase 1: Analyzing request")
        travel_plan = await enhanced_travel_analysis(user_request)

        if customer_info.get('budget'):
            try:
                budget_str = customer_info['budget'].upper().replace("USD", "").replace("$", "").strip()
                travel_plan.total_budget = float(budget_str)
                print(f"Budget injected: ${travel_plan.total_budget}")
            except (ValueError, TypeError):
                print(f"Could not parse budget: {customer_info.get('budget')}")

        state['travel_plan'] = travel_plan

        print(f"Phase 2: Preparing tools (intent: {travel_plan.user_intent})")

        tasks_and_names = []
        default_checkin, default_checkout = calculate_default_dates(travel_plan)

        departure_date = travel_plan.departure_date or default_checkin
        return_date = travel_plan.return_date or default_checkout

        try:
            datetime.strptime(departure_date, '%Y-%m-%d')
            if return_date:
                datetime.strptime(return_date, '%Y-%m-%d')
        except ValueError as e:
            print(f"Invalid date, using defaults: {e}")
            departure_date = default_checkin
            return_date = default_checkout

        if travel_plan.user_intent in ["full_plan", "flights_only"] and travel_plan.origin and travel_plan.destination:
            task = search_flights.ainvoke({
                "originLocationCode": travel_plan.origin,
                "destinationLocationCode": travel_plan.destination,
                "departureDate": departure_date,
                "returnDate": return_date,
                "adults": travel_plan.adults,
                "currencyCode": "USD",
                "travelClass": travel_plan.travel_class,
                "departureTime": travel_plan.departure_time_pref,
                "arrivalTime": travel_plan.arrival_time_pref,
            })
            tasks_and_names.append((task, "search_flights"))

        if travel_plan.user_intent in ["full_plan", "hotels_only"] and travel_plan.destination:
            task = search_and_compare_hotels.ainvoke({
                "city_code": travel_plan.destination,
                "check_in_date": departure_date,
                "check_out_date": return_date,
                "adults": travel_plan.adults,
            })
            tasks_and_names.append((task, "search_and_compare_hotels"))

        if travel_plan.user_intent in ["full_plan", "activities_only"] and travel_plan.destination:
            task = search_activities_by_city.ainvoke({"city_name": travel_plan.destination})
            tasks_and_names.append((task, "search_activities_by_city"))

        if not tasks_and_names:
            print("No tools to call")
            return {
                "messages": [AIMessage(content="I've understood your request, but there's no specific search I can perform. How else can I help?")],
                "current_step": "complete",
                "travel_plan": travel_plan,
            }

        print(f"Phase 3: Executing {len(tasks_and_names)} tools in parallel")

        tasks = [task for task, name in tasks_and_names]
        tool_results = await asyncio.gather(*tasks, return_exceptions=True)
        processed_messages = []

        for i, (result, (_, tool_name)) in enumerate(zip(tool_results, tasks_and_names)):
            if isinstance(result, Exception):
                print(f"Tool {tool_name} failed: {result}")
                content = "[]"
            else:
                try:
                    content = json.dumps([item.model_dump() for item in result])
                except Exception as e:
                    print(f"Serialization failed for {tool_name}: {e}")
                    content = "[]"

            processed_messages.append(ToolMessage(
                content=content,
                name=tool_name,
                tool_call_id=f"call_{tool_name}_{i}",
            ))

        print("All tools executed")
        return {
            "messages": processed_messages,
            "current_step": "synthesizing",
            "travel_plan": travel_plan,
        }

    except ValueError as e:
        print(f"Analysis failed: {e}")
        response = AIMessage(content="I'm sorry, I had trouble understanding your request. Could you rephrase it?")
        return {"messages": [response], "current_step": "complete"}
    except Exception as e:
        print(f"Unexpected error: {e}")
        traceback.print_exc()
        response = AIMessage(content="I apologize, but a system error occurred. Please try again.")
        return {"messages": [response], "current_step": "complete"}


async def synthesize_results_node(state: TravelAgentState) -> dict:
    """Package generation and final response node."""
    print("NODE: Synthesis & Response")

    tool_results = {}
    for msg in state['messages']:
        if isinstance(msg, ToolMessage):
            try:
                tool_results[msg.name] = msg.content
            except Exception as e:
                print(f"Failed to process {msg.name}: {e}")
                tool_results[msg.name] = "[]"

    travel_plan = state.get('travel_plan')

    all_options = {'flights': [], 'hotels': [], 'activities': []}
    for tool_name, content in tool_results.items():
        try:
            if content and content != "[]":
                parsed_data = json.loads(content)
                if tool_name == "search_flights":
                    all_options['flights'] = [FlightOption.model_validate(f) for f in parsed_data]
                elif tool_name == "search_and_compare_hotels":
                    all_options['hotels'] = [HotelOption.model_validate(h) for h in parsed_data]
                elif tool_name == "search_activities_by_city":
                    all_options['activities'] = [ActivityOption.model_validate(a) for a in parsed_data]
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            print(f"Failed to parse {tool_name}: {e}")

    packages = []
    if (travel_plan and
            travel_plan.user_intent == "full_plan" and
            travel_plan.total_budget and
            all_options['flights'] and
            all_options['hotels']):

        print("Generating travel packages")
        try:
            packages = await generate_travel_packages(travel_plan, all_options)
        except Exception as e:
            print(f"Package generation failed: {e}")
            packages = []

    synthesis_prompt = ""
    hubspot_recommendations = {}

    if packages:
        print(f"Preparing response with {len(packages)} packages")
        synthesis_prompt = f"""You are an AI travel assistant. Present these custom travel packages professionally.

**GENERATED PACKAGES:**
{json.dumps([p.model_dump() for p in packages], indent=2)}

**YOUR TASK:**
- Start with a warm greeting
- Present ALL packages with clear details (flight, hotel, activities)
- Highlight the "Balanced" package as recommended
- End with clear call to action
"""
        hubspot_recommendations = {"packages": [p.model_dump() for p in packages]}
    else:
        print("Preparing response with search results")
        has_results = any(all_options.values())

        if has_results:
            tool_results_for_prompt = {
                "flights": [f.model_dump() for f in all_options.get('flights', [])],
                "hotels": [h.model_dump() for h in all_options.get('hotels', [])],
                "activities": [a.model_dump() for a in all_options.get('activities', [])],
            }
            synthesis_prompt = f"""You are an AI travel assistant. Present these search results clearly.

**SEARCH RESULTS:**
{json.dumps(tool_results_for_prompt, indent=2)}

Organize and present options in a user-friendly format.
"""
            hubspot_recommendations = tool_results_for_prompt
        else:
            synthesis_prompt = """You are an AI travel assistant.
Apologize that no options were found and offer to help refine the search."""
            hubspot_recommendations = {"error": "No results found"}

    try:
        final_response = await llm.ainvoke(synthesis_prompt)
    except Exception as e:
        print(f"Response generation failed: {e}")
        final_response = AIMessage(content="I apologize, but I encountered an issue generating your recommendations. Please try again.")

    if state.get('customer_info') and travel_plan:
        try:
            await send_to_hubspot.ainvoke({
                'customer_info': state['customer_info'],
                'travel_plan': travel_plan,
                'recommendations': hubspot_recommendations,
                'original_request': state.get('original_request', ''),
            })
        except Exception as e:
            print(f"CRM integration warning: {e}")

    return {
        "messages": [final_response],
        "current_step": "complete",
    }
