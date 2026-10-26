"""Sensor platform for smart_tag."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfLength
from homeassistant.util import dt as dt_util
from homeassistant.util.unit_system import METRIC_SYSTEM

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

DISTANCE_DESCRIPTION = SensorEntityDescription(
    key="bus_distance_to_stop",
    translation_key="bus_distance_to_stop",
    device_class=SensorDeviceClass.DISTANCE,
    native_unit_of_measurement=UnitOfLength.METERS,
    suggested_display_precision=1,
    state_class=SensorStateClass.MEASUREMENT,
)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: SmartTagEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    coordinator = entry.runtime_data.coordinator
    for student_id in coordinator.data:
        async_add_entities(
            [
                SmartTagBusStatusSensor(coordinator, student_id),
                SmartTagBusDistanceSensor(coordinator, student_id),
            ]
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


class SmartTagBusDistanceSensor(SmartTagEntity, SensorEntity):
    """Distance from the bus to the student's home stop."""

    def __init__(self, coordinator: SmartTagCoordinator, student_id: int) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, student_id, DISTANCE_DESCRIPTION.key)
        self.entity_description = DISTANCE_DESCRIPTION
        self._attr_suggested_unit_of_measurement = (
            UnitOfLength.KILOMETERS
            if coordinator.hass.config.units is METRIC_SYSTEM
            else UnitOfLength.MILES
        )

    @property
    def native_value(self) -> float | None:
        """Return the distance in meters, or None without live data."""
        data = self.student_data
        if data is None or data.live is None:
            return None
        return data.live.distance_to_home_stop()
