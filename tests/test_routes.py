"""Tests for the scheduled routes and the next pickup calculation."""

from __future__ import annotations

from datetime import datetime, time
from zoneinfo import ZoneInfo

from custom_components.smart_tag.data import Student, StudentRoute, next_pickup

TZ = ZoneInfo("America/New_York")

ROUTES = [
    {
        "routeId": 101,
        "friendlyRouteDisplay": "Route A",
        "routeGroup": "AM",
        "pickupStopTimes": "07:10 AM",
        "dropOffStopTimes": "07:40 AM",
    },
    {
        "routeId": 102,
        "friendlyRouteDisplay": "Route A-L",
        "routeGroup": "AM",
        "pickupStopTimes": "09:05 AM",
        "dropOffStopTimes": "09:35 AM",
    },
    {
        "routeId": 103,
        "friendlyRouteDisplay": "Route B",
        "routeGroup": "PM",
        "pickupStopTimes": "02:45 PM",
        "dropOffStopTimes": "03:15 PM",
    },
]


def _routes(items: list[dict]) -> list[StudentRoute]:
    """Build routes from API-style dicts."""
    routes = [StudentRoute.from_dict(item) for item in items]
    return [route for route in routes if route is not None]


def _at(day: int, hour: int, minute: int = 0) -> datetime:
    """Return a datetime in March 2025 (3rd = Monday, 7th = Friday)."""
    return datetime(2025, 3, day, hour, minute, tzinfo=TZ)


def test_parse_routes() -> None:
    """The student keeps all routes with usable times."""
    student = Student.from_dict(
        {"id": 1, "fullName": "Jane Doe", "student2Routes": ROUTES}
    )
    assert len(student.routes) == 3
    assert student.routes[0].pickup == time(7, 10)
    assert student.routes[0].group == "AM"


def test_bad_time_skipped() -> None:
    """A route with an unusable time is skipped."""
    bad = {**ROUTES[0], "pickupStopTimes": "later"}
    student = Student.from_dict(
        {"id": 1, "fullName": "Jane Doe", "student2Routes": [*ROUTES, bad]}
    )
    assert len(student.routes) == 3


def test_no_routes_key() -> None:
    """A student without a routes key has no routes."""
    assert Student.from_dict({"id": 1}).routes == []


def test_monday_morning() -> None:
    """Before the pickup on a normal day, the earliest AM route is used."""
    result = next_pickup(_routes(ROUTES), _at(3, 6), {4}, weekdays_only=True)
    assert result is not None
    assert result[0] == _at(3, 7, 10)
    assert result[1].name == "Route A"


def test_after_pickup() -> None:
    """After today's pickup, the next day is used."""
    result = next_pickup(_routes(ROUTES), _at(3, 7, 30), {4}, weekdays_only=True)
    assert result is not None
    assert result[0] == _at(4, 7, 10)


def test_thursday_evening() -> None:
    """The day after is a delayed-start day: the later route is used."""
    result = next_pickup(_routes(ROUTES), _at(6, 18), {4}, weekdays_only=True)
    assert result is not None
    assert result[0] == _at(7, 9, 5)
    assert result[1].name == "Route A-L"


def test_no_delayed_days() -> None:
    """Without delayed-start days the earliest route is always used."""
    result = next_pickup(_routes(ROUTES), _at(6, 18), set(), weekdays_only=True)
    assert result is not None
    assert result[0] == _at(7, 7, 10)


def test_friday_after_pickup() -> None:
    """After the Friday pickup, weekends are skipped."""
    result = next_pickup(_routes(ROUTES), _at(7, 10), {4}, weekdays_only=True)
    assert result is not None
    assert result[0] == _at(10, 7, 10)


def test_weekends_allowed() -> None:
    """With weekends allowed, Saturday is next."""
    result = next_pickup(_routes(ROUTES), _at(7, 10), {4}, weekdays_only=False)
    assert result is not None
    assert result[0] == _at(8, 7, 10)


def test_one_am_route_on_delayed_day() -> None:
    """With a single AM route the delayed-start rule changes nothing."""
    result = next_pickup(_routes(ROUTES[:1]), _at(6, 18), {4}, weekdays_only=True)
    assert result is not None
    assert result[0] == _at(7, 7, 10)


def test_no_am_route() -> None:
    """Without an AM route there is no pickup."""
    assert next_pickup(_routes(ROUTES[2:]), _at(3, 6), {4}, weekdays_only=True) is None


def test_timezone_kept() -> None:
    """The result uses the time zone of the given time."""
    result = next_pickup(_routes(ROUTES), _at(3, 6), {4}, weekdays_only=True)
    assert result is not None
    assert result[0].tzinfo is TZ
