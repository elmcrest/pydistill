"""Common types used across the project."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class Status(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"


class Address(BaseModel):
    street: str
    city: str
    zip_code: str
    country: str = "Germany"


class TimestampMixin(BaseModel):
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
