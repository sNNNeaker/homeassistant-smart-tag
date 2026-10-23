"""Custom types for smart_tag."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from homeassistant.util import dt as dt_util

from .const import STATUS_DROPPED_OFF, STATUS_NO_RIDE_TODAY, STATUS_ON_BUS

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

    from .api import SmartTagApiClient
    from .coordinator import SmartTagCoordinator


type SmartTagEntry = ConfigEntry[SmartTagData]


def _clean(value: str | None) -> str | None:
    """Strip the padding the API adds to text fields."""
    return (value.strip() or None) if isinstance(value, str) else value


@dataclass
class SmartTagData:
    """Runtime data for the SMART tag integration."""

    client: SmartTagApiClient
    coordinator: SmartTagCoordinator


@dataclass
class Student:
    """A student from the SMART tag portal."""

    @classmethod
    def from_dict(cls, value: dict) -> Student:
        """Convert a dict to a Student."""
        return cls(
            campus=value.get("campus"),
            external_id=value.get("externalId"),
            full_name=_clean(value.get("fullName")) or "Student",
            id=value["id"],
            grade=value.get("grade"),
        )

    campus: str | None
    external_id: str | None
    full_name: str
    id: int
    grade: str | None


@dataclass
class RideEndpoint:
    """Either the start or the end of a ride."""

    time: datetime
    lat: float | None
    long: float | None


@dataclass
class Ride:
    """A single bus ride."""

    DATE_FORMAT = "%m/%d/%Y %H:%M:%S"

    @classmethod
    def _parse_endpoint(
        cls, value: dict, date_key: str, lat_key: str, long_key: str
    ) -> RideEndpoint | None:
        """Parse one endpoint of a ride, or None if it has no date."""
        raw = value.get(date_key)
        if not raw:
            return None
        naive = datetime.strptime(raw, cls.DATE_FORMAT)  # noqa: DTZ007
        return RideEndpoint(
            time=naive.replace(tzinfo=dt_util.get_default_time_zone()),
            lat=value.get(lat_key),
            long=value.get(long_key),
        )

    @classmethod
    def from_dict(cls, value: dict) -> Ride | None:
        """Convert a dict from the API to a Ride (None if it has no start)."""
        start = cls._parse_endpoint(
            value, "embarkationDate", "embarkationLatitude", "embarkationLongtitude"
        )
        if start is None:
            return None
        return cls(
            id=value.get("activityId"),
            bus_id=_clean(value.get("busName")),
            start=start,
            end=cls._parse_endpoint(
                value,
                "disembarkationDate",
                "disembarkationLatitude",
                "disembarkationLongtitude",
            ),
            driver=_clean(value.get("driverName")),
            route_name=_clean(value.get("friendlyRouteDisplay")),
            shift=_clean(value.get("shift")),
            route_id=value.get("routeId"),
        )

    id: int | None
    bus_id: str | None
    start: RideEndpoint
    end: RideEndpoint | None
    driver: str | None
    shift: str | None
    route_id: int | None
    route_name: str | None


@dataclass
class StudentData:
    """A student and their most recent rides (newest first)."""

    student: Student
    rides: list[Ride]


def ride_status(rides: list[Ride], now: datetime) -> tuple[str, Ride | None]:
    """Return the bus status and the relevant ride for the given time."""
    if not rides:
        return (STATUS_NO_RIDE_TODAY, None)
    ride = rides[0]
    if ride.start.time.date() != now.date():
        return (STATUS_NO_RIDE_TODAY, None)
    if ride.end is None:
        return (STATUS_ON_BUS, ride)
    return (STATUS_DROPPED_OFF, ride)
