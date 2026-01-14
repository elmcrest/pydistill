"""Appointment models."""

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field

from project_a.common.types import Address, Status, TimestampMixin
from project_a.vehicles.models import Vehicle


class Customer(BaseModel):
    id: int
    name: str
    email: str
    address: Optional[Address] = None


class Appointment(TimestampMixin):
    id: int
    title: str
    description: Optional[str] = None
    scheduled_at: datetime
    customer: Customer
    vehicle: Optional[Vehicle] = None
    location: Optional[Address] = None
    status: Status = Status.PENDING
    tags: List[str] = Field(default_factory=list)
