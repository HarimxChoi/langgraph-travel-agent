"""Activity option model."""

from typing import Optional
from pydantic import BaseModel, Field


class ActivityOption(BaseModel):
    """Structured activity offer data."""
    name: str = Field(description="Activity name")
    description: str = Field(description="Brief description")
    price: str = Field(description="Activity price")
    location: Optional[str] = Field(description="Activity location", default=None)
