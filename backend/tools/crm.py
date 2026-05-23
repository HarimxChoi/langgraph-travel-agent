"""CRM integration tool (HubSpot by default).

To use a different CRM (Salesforce, Pipedrive, etc.):
1. Replace HUBSPOT_API_KEY with your CRM's API key
2. Update the API endpoint URL below
3. Modify the payload structure to match your CRM's API
4. Update custom property names as needed
"""

import json
from typing import Dict, List

import httpx
from langchain_core.tools import tool
from pydantic import BaseModel

from ..config.settings import HUBSPOT_API_KEY
from ..models import TravelPlan, TravelPackage


class HubSpotArgs(BaseModel):
    """CRM integration data structure."""
    customer_info: Dict[str, str]
    travel_plan: TravelPlan
    recommendations: Dict[str, List]
    original_request: str


@tool(args_schema=HubSpotArgs)
async def send_to_hubspot(
    customer_info: Dict[str, str],
    travel_plan: TravelPlan,
    recommendations: Dict[str, List],
    original_request: str,
) -> str:
    """Send final travel plan to CRM (HubSpot by default)."""
    if not HUBSPOT_API_KEY:
        print("CRM integration disabled (no API key)")
        return "CRM integration is not configured."

    print("Preparing CRM data")

    description = f"""**Original Request:**\n{original_request}\n\n---
**AI-Generated Travel Plan:**
- **Origin:** {travel_plan.origin or 'N/A'}
- **Destination:** {travel_plan.destination}
- **Dates:** {travel_plan.departure_date} to {travel_plan.return_date}
- **Travelers:** {travel_plan.adults} adult(s)
- **Budget:** ${travel_plan.total_budget or 'Not specified'}
---
"""

    if "packages" in recommendations and recommendations["packages"]:
        description += "\n**AI-Generated Packages:**\n"
        packages = [TravelPackage.model_validate(p) for p in recommendations["packages"]]

        for i, pkg in enumerate(packages):
            description += (
                f"\n**{i+1}. {pkg.name} - ${pkg.total_cost:.2f}** ({pkg.budget_comment})\n"
                f"- **Flight:** {pkg.selected_flight.airline} ({pkg.selected_flight.price})\n"
                f"- **Hotel:** {pkg.selected_hotel.name} ({pkg.selected_hotel.price_per_night})\n"
                f"- **Activities:** {', '.join([a.name for a in pkg.selected_activities]) or 'None'}\n"
            )
    else:
        description += "\n**AI Search Results:**\n"
        if recommendations.get("flights"):
            description += f"- {len(recommendations['flights'])} flight option(s)\n"
        if recommendations.get("hotels"):
            description += f"- {len(recommendations['hotels'])} hotel option(s)\n"
        if recommendations.get("activities"):
            description += f"- {len(recommendations['activities'])} activity option(s)\n"

    hubspot_data = {
        "properties": {
            "dealname": f"AI Plan: {travel_plan.destination} for {customer_info.get('name', 'New Lead')}",
            "amount": str(travel_plan.total_budget or 0),
            "dealstage": "appointmentscheduled",
            "description": description,
            "customer_name": customer_info.get("name", ""),
            "customer_email": customer_info.get("email", ""),
            "customer_phone": customer_info.get("phone", ""),
            "original_travel_request": original_request,
            "travel_origin": travel_plan.origin or "Not specified",
            "travel_destination": travel_plan.destination,
            "departure_date": travel_plan.departure_date,
            "return_date": travel_plan.return_date,
            "number_of_travelers": travel_plan.adults,
            "flight_class_preference": travel_plan.travel_class,
            "ai_generated_content": json.dumps(recommendations),
        }
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.hubapi.com/crm/v3/objects/deals",
                headers={"Authorization": f"Bearer {HUBSPOT_API_KEY}"},
                json=hubspot_data,
            )
            response.raise_for_status()
            print("Data sent to CRM successfully")
            return "Customer data sent to CRM successfully"
    except Exception as e:
        print(f"CRM integration failed: {e}")
        return f"Failed to send to CRM: {e}"
