"""Sensor platform for smart_tag."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.util import dt as dt_util

from .const import STATUS_DROPPED_OFF, STATUS_NO_RIDE_TODAY, STATUS_ON_BUS
from .data import ride_status
from .entity import SmartTagEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .coordinator import SmartTagCoordinator
    from .data import SmartTagEntry

ENTITY_DESCRIPTION = SensorEntityDescription(
    key="bus_status",
    translation_key="bus_status",
    device_class=SensorDeviceClass.ENUM,
    options=[STATUS_ON_BUS, STATUS_DROPPED_OFF, STATUS_NO_RIDE_TODAY],
    icon="mdi:bus-school",
)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: SmartTagEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        SmartTagBusStatusSensor(coordinator, student_id)
        for student_id in coordinator.data
    )


class SmartTagBusStatusSensor(SmartTagEntity, SensorEntity):
    """Bus status of a student."""

    def __init__(self, coordinator: SmartTagCoordinator, student_id: int) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, student_id, ENTITY_DESCRIPTION.key)
        self.entity_description = ENTITY_DESCRIPTION

    @property
    def native_value(self) -> str | None:
        """Return the bus status."""
        data = self.student_data
        if data is None:
            return None
        return ride_status(data.rides, dt_util.now())[0]

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return details of the newest ride, even if it is not from today."""
        data = self.student_data
        if data is None or not data.rides:
            return None
        ride = data.rides[0]
        end = ride.end
        return {
            "bus": ride.bus_id,
            "route": ride.route_name,
            "driver": ride.driver,
            "shift": ride.shift,
            "boarded_at": ride.start.time.isoformat(),
            "boarded_latitude": ride.start.lat,
            "boarded_longitude": ride.start.long,
            "dropped_off_at": end.time.isoformat() if end else None,
            "dropped_off_latitude": end.lat if end else None,
            "dropped_off_longitude": end.long if end else None,
        }
