"""Vehicle models."""

from project_a.common.types import Status, TimestampMixin


class Vehicle(TimestampMixin):
    id: int
    license_plate: str
    make: str
    model: str
    year: int
    status: Status = Status.ACTIVE
    notes: str | None = None
