"""Hotel option model."""

from typing import Optional
from pydantic import BaseModel, Field


class HotelOption(BaseModel):
    """Structured hotel offer data."""
    name: str = Field(description="Hotel name")
    category: str = Field(description="Star rating, e.g., '5EST' for 5-star")
    price_per_night: str = Field(description="Price per night")
    source: str = Field(description="Data source (e.g., 'Amadeus', 'Hotelbeds')")
    rating: Optional[float] = Field(description="Hotel rating", default=None)
