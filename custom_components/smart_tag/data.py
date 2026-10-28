"""Custom types for smart_tag."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import asin, cos, radians, sin, sqrt
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


def _float(value: object) -> float | None:
    """Convert a string or number to a float, or None if that is not possible."""
    try:
        result = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return result


def distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return the great-circle distance in meters between two coordinates."""
    earth_radius_m = 6371000
    d_lat = radians(lat2 - lat1)
    d_lon = radians(lon2 - lon1)
    a = (
        sin(d_lat / 2) ** 2
        + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lon / 2) ** 2
    )
    return 2 * earth_radius_m * asin(sqrt(a))


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
            photo_location=value.get("photoLocation") or None,
        )

    campus: str | None
    external_id: str | None
    full_name: str
    id: int
    grade: str | None
    photo_location: str | None = None


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
class LiveActivity:
    """Live position of the bus a student is riding."""

    @classmethod
    def from_dict(cls, value: dict) -> LiveActivity | None:
        """Convert a live-activity response to a LiveActivity (None if no position)."""
        live_map = value.get("liveMap") if isinstance(value, dict) else None
        if not live_map or not isinstance(live_map[0], dict):
            return None
        entry = live_map[0]

        raw = entry.get("lastKnownLocation")
        if not isinstance(raw, str):
            return None
        parts = [part.strip() for part in raw.split(",")]
        if len(parts) < 4:
            return None
        longitude = _float(parts[0])
        latitude = _float(parts[1])
        speed = _float(parts[2])
        if (
            longitude is None
            or latitude is None
            or speed is None
            or not -90 <= latitude <= 90
            or not -180 <= longitude <= 180
        ):
            return None
        heading = _float(parts[5]) if len(parts) > 5 else None

        today = value.get("todaysActivity")
        status_text = _clean(today.get("status")) if isinstance(today, dict) else None

        return cls(
            latitude=latitude,
            longitude=longitude,
            speed_mph=speed,
            gps_time=parts[3],
            heading=round(heading) if heading is not None else None,
            direction=(parts[6] if len(parts) > 6 else None)
            or _clean(entry.get("direction")),
            on_bus=bool(entry.get("studentOnBus")),
            bus=_clean(entry.get("busName")),
            route=_clean(entry.get("friendlyRouteDisplay")),
            driver=_clean(entry.get("driverName")),
            home_stop_name=_clean(entry.get("assignedHomeStopName")),
            home_stop_latitude=_float(entry.get("assignedHomeStopLatitude")),
            home_stop_longitude=_float(entry.get("assignedHomeStopLongitude")),
            status_text=status_text,
        )

    def distance_to_home_stop(self) -> float | None:
        """Return the distance in meters from the bus to the home stop."""
        if self.home_stop_latitude is None or self.home_stop_longitude is None:
            return None
        return distance_m(
            self.latitude,
            self.longitude,
            self.home_stop_latitude,
            self.home_stop_longitude,
        )

    latitude: float
    longitude: float
    speed_mph: float
    gps_time: str
    heading: int | None
    direction: str | None
    on_bus: bool
    bus: str | None
    route: str | None
    driver: str | None
    home_stop_name: str | None
    home_stop_latitude: float | None
    home_stop_longitude: float | None
    status_text: str | None


@dataclass
class StudentData:
    """A student and their most recent rides (newest first)."""

    student: Student
    rides: list[Ride]
    live: LiveActivity | None = None


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
