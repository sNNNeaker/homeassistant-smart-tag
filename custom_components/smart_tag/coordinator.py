"""DataUpdateCoordinator for smart_tag."""

from __future__ import annotations

from datetime import datetime, time, timedelta
from typing import TYPE_CHECKING

from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import (
    SmartTagApiAuthError,
    SmartTagApiClient,
    SmartTagApiError,
)
from .const import (
    CONF_ACCESS_TOKEN,
    CONF_AFTERNOON_END,
    CONF_AFTERNOON_START,
    CONF_MORNING_END,
    CONF_MORNING_START,
    CONF_REFRESH_TOKEN,
    CONF_WEEKDAYS_ONLY,
    DEFAULT_AFTERNOON_END,
    DEFAULT_AFTERNOON_START,
    DEFAULT_MORNING_END,
    DEFAULT_MORNING_START,
    DEFAULT_WEEKDAYS_ONLY,
    DOMAIN,
    LOGGER,
    STATUS_ON_BUS,
)
from .data import StudentData, ride_status

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import SmartTagEntry

RIDES_PER_STUDENT = 5
ACTIVE_INTERVAL = timedelta(seconds=60)
IDLE_INTERVAL = timedelta(minutes=30)


def _parse_time(value: str, default: str) -> time:
    """Parse a HH:MM[:SS] string, falling back to the default."""
    return dt_util.parse_time(value) or dt_util.parse_time(default) or time(0, 0)


# https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
class SmartTagCoordinator(DataUpdateCoordinator[dict[int, StudentData]]):
    """Class to manage fetching data from the API."""

    config_entry: SmartTagEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: SmartTagEntry,
        client: SmartTagApiClient,
    ) -> None:
        """Initialize."""
        super().__init__(
            hass,
            LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=ACTIVE_INTERVAL,
        )
        self.client = client

    def _windows(self, day: datetime) -> list[tuple[datetime, datetime]]:
        """Return the configured ride windows for the day of the given datetime."""
        options = self.config_entry.options
        pairs = (
            (
                options.get(CONF_MORNING_START, DEFAULT_MORNING_START),
                DEFAULT_MORNING_START,
                options.get(CONF_MORNING_END, DEFAULT_MORNING_END),
                DEFAULT_MORNING_END,
            ),
            (
                options.get(CONF_AFTERNOON_START, DEFAULT_AFTERNOON_START),
                DEFAULT_AFTERNOON_START,
                options.get(CONF_AFTERNOON_END, DEFAULT_AFTERNOON_END),
                DEFAULT_AFTERNOON_END,
            ),
        )
        return [
            (
                day.replace(
                    hour=start.hour,
                    minute=start.minute,
                    second=start.second,
                    microsecond=0,
                ),
                day.replace(
                    hour=end.hour,
                    minute=end.minute,
                    second=end.second,
                    microsecond=0,
                ),
            )
            for start, end in (
                (_parse_time(s, ds), _parse_time(e, de)) for s, ds, e, de in pairs
            )
        ]

    def _compute_interval(self, now: datetime, *, on_bus: bool) -> timedelta:
        """Return the polling interval to use after an update."""
        if on_bus:
            return ACTIVE_INTERVAL

        weekdays_only = self.config_entry.options.get(
            CONF_WEEKDAYS_ONLY, DEFAULT_WEEKDAYS_ONLY
        )
        next_start: datetime | None = None
        for offset in range(8):
            day = now + timedelta(days=offset)
            if weekdays_only and day.weekday() >= 5:
                continue
            for start, end in self._windows(day):
                if offset == 0 and start <= now <= end:
                    return ACTIVE_INTERVAL
                if start > now and (next_start is None or start < next_start):
                    next_start = start

        if next_start is None:
            return IDLE_INTERVAL
        return max(ACTIVE_INTERVAL, min(IDLE_INTERVAL, next_start - now))

    def _persist_tokens(self) -> None:
        """Store refreshed tokens in the config entry."""
        entry = self.config_entry
        access = self.client.access_token
        refresh = self.client.refresh_token
        if access is None or refresh is None:
            return
        if (
            entry.data.get(CONF_ACCESS_TOKEN) != access
            or entry.data.get(CONF_REFRESH_TOKEN) != refresh
        ):
            self.hass.config_entries.async_update_entry(
                entry,
                data={
                    **entry.data,
                    CONF_ACCESS_TOKEN: access,
                    CONF_REFRESH_TOKEN: refresh,
                },
            )

    async def _async_update_data(self) -> dict[int, StudentData]:
        """Update data via library."""
        try:
            students = await self.client.get_students()
            result: dict[int, StudentData] = {}
            for student in students:
                rides = await self.client.get_rides(student.id, RIDES_PER_STUDENT)
                rides.sort(key=lambda ride: ride.start.time, reverse=True)
                result[student.id] = StudentData(student=student, rides=rides)
        except SmartTagApiAuthError as exception:
            raise ConfigEntryAuthFailed(exception) from exception
        except SmartTagApiError as exception:
            raise UpdateFailed(exception) from exception

        self._persist_tokens()

        now = dt_util.now()
        on_bus = any(
            ride_status(data.rides, now)[0] == STATUS_ON_BUS for data in result.values()
        )
        self.update_interval = self._compute_interval(now, on_bus=on_bus)
        return result
