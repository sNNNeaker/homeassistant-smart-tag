"""Binary sensor platform for smart_tag."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.util import dt as dt_util

from .const import STATUS_ON_BUS
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


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: SmartTagEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the binary_sensor platform."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        SmartTagOnBusSensor(coordinator, student_id) for student_id in coordinator.data
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
