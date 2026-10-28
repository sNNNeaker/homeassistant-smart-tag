"""Device tracker platform for smart_tag."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.device_tracker import (
    SourceType,
    TrackerEntity,
    TrackerEntityDescription,
)
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN
from .entity import SmartTagEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .coordinator import SmartTagCoordinator
    from .data import SmartTagEntry

ENTITY_DESCRIPTION = TrackerEntityDescription(
    key="school_bus",
    translation_key="school_bus",
    icon="mdi:bus-school",
)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: SmartTagEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the device_tracker platform."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        SmartTagBusTracker(coordinator, student_id) for student_id in coordinator.data
    )


class SmartTagBusTracker(SmartTagEntity, TrackerEntity):
    """Live position of the bus a student is riding."""

    _attr_location_accuracy = 0

    def __init__(self, coordinator: SmartTagCoordinator, student_id: int) -> None:
        """Initialize the tracker."""
        super().__init__(coordinator, student_id, ENTITY_DESCRIPTION.key)
        self.entity_description = ENTITY_DESCRIPTION

    @property
    def entity_picture(self) -> str | None:
        """Return the student's photo (map marker), if the account has one."""
        registry = er.async_get(self.hass)
        photo_id = registry.async_get_entity_id(
            "image", DOMAIN, self.unique_id.removesuffix("school_bus") + "photo"
        )
        state = self.hass.states.get(photo_id) if photo_id else None
        # An image entity always has a proxy URL; only use it when a photo exists.
        if state is None or state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            return None
        return state.attributes.get("entity_picture")

    @property
    def source_type(self) -> SourceType:
        """Return the source type."""
        return SourceType.GPS

    @property
    def latitude(self) -> float | None:
        """Return the latitude of the bus."""
        data = self.student_data
        return data.live.latitude if data and data.live else None

    @property
    def longitude(self) -> float | None:
        """Return the longitude of the bus."""
        data = self.student_data
        return data.live.longitude if data and data.live else None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return details of the live position."""
        data = self.student_data
        if data is None or data.live is None:
            return None
        live = data.live
        return {
            "speed_mph": live.speed_mph,
            "heading": live.heading,
            "direction": live.direction,
            "gps_time": live.gps_time,
            "bus": live.bus,
            "route": live.route,
            "home_stop": live.home_stop_name,
        }
