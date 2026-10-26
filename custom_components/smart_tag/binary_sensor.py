"""Binary sensor platform for smart_tag."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.util import dt as dt_util

from .const import CONF_APPROACH_DISTANCE, DEFAULT_APPROACH_DISTANCE, STATUS_ON_BUS
from .data import ride_status
from .entity import SmartTagEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .coordinator import SmartTagCoordinator
    from .data import SmartTagEntry

ENTITY_DESCRIPTION = BinarySensorEntityDescription(
    key="on_bus",
    translation_key="on_bus",
    icon="mdi:bus-school",
)

APPROACHING_DESCRIPTION = BinarySensorEntityDescription(
    key="bus_approaching",
    translation_key="bus_approaching",
    icon="mdi:bus-alert",
)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: SmartTagEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the binary_sensor platform."""
    coordinator = entry.runtime_data.coordinator
    for student_id in coordinator.data:
        async_add_entities(
            [
                SmartTagOnBusSensor(coordinator, student_id),
                SmartTagBusApproachingSensor(coordinator, student_id),
            ]
        )


class SmartTagOnBusSensor(SmartTagEntity, BinarySensorEntity):
    """Whether a student is currently on the bus."""

    def __init__(self, coordinator: SmartTagCoordinator, student_id: int) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, student_id, ENTITY_DESCRIPTION.key)
        self.entity_description = ENTITY_DESCRIPTION

    @property
    def is_on(self) -> bool | None:
        """Return true if the student is on the bus."""
        data = self.student_data
        if data is None:
            return None
        return ride_status(data.rides, dt_util.now())[0] == STATUS_ON_BUS


class SmartTagBusApproachingSensor(SmartTagEntity, BinarySensorEntity):
    """Whether the bus is close to the student's home stop (afternoon rides)."""

    def __init__(self, coordinator: SmartTagCoordinator, student_id: int) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, student_id, APPROACHING_DESCRIPTION.key)
        self.entity_description = APPROACHING_DESCRIPTION

    @property
    def is_on(self) -> bool | None:
        """Return true if the bus is within the approach distance of the stop."""
        data = self.student_data
        if data is None:
            return None
        status, ride = ride_status(data.rides, dt_util.now())
        if (
            data.live is None
            or status != STATUS_ON_BUS
            or ride is None
            or (ride.shift or "").upper() != "PM"
        ):
            return False
        distance = data.live.distance_to_home_stop()
        if distance is None:
            return False
        limit = self.coordinator.config_entry.options.get(
            CONF_APPROACH_DISTANCE, DEFAULT_APPROACH_DISTANCE
        )
        return distance <= limit
