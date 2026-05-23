"""Flight option model."""

from typing import Optional
from pydantic import BaseModel, Field


class FlightOption(BaseModel):
    """Structured flight offer data."""
    airline: str = Field(description="Airline name")
    price: str = Field(description="Total flight cost")
    departure_time: str = Field(description="Departure time (YYYY-MM-DDTHH:MM:SS)")
    arrival_time: str = Field(description="Arrival time (YYYY-MM-DDTHH:MM:SS)")
    duration: Optional[str] = Field(description="Flight duration", default=None)
