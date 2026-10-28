"""Image platform for smart_tag: the student's photo."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from homeassistant.components.image import ImageEntity, ImageEntityDescription
from homeassistant.core import callback
from homeassistant.util import dt as dt_util

from .api import SmartTagApiError
from .const import LOGGER
from .entity import SmartTagEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .coordinator import SmartTagCoordinator
    from .data import SmartTagEntry

ENTITY_DESCRIPTION = ImageEntityDescription(
    key="photo",
    translation_key="photo",
    icon="mdi:account-box",
)

# School photos change about once a year; check daily.
PHOTO_REFRESH = timedelta(hours=24)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: SmartTagEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the image platform."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        SmartTagStudentPhoto(coordinator, student_id) for student_id in coordinator.data
    )


class SmartTagStudentPhoto(SmartTagEntity, ImageEntity):
    """The student's photo from the parent portal."""

    def __init__(self, coordinator: SmartTagCoordinator, student_id: int) -> None:
        """Initialize the image."""
        SmartTagEntity.__init__(self, coordinator, student_id, ENTITY_DESCRIPTION.key)
        ImageEntity.__init__(self, coordinator.hass)
        self.entity_description = ENTITY_DESCRIPTION
        self._image: bytes | None = None
        self._checked: datetime | None = None
        self._fetching = False

    async def async_added_to_hass(self) -> None:
        """Fetch the photo once the entity is added."""
        await super().async_added_to_hass()
        await self._async_refresh_photo()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Re-check the photo once a day (or after a failed fetch)."""
        if not self._fetching and (
            self._checked is None or dt_util.utcnow() - self._checked >= PHOTO_REFRESH
        ):
            self.hass.async_create_task(self._async_refresh_photo())
        super()._handle_coordinator_update()

    async def _async_refresh_photo(self) -> None:
        """Fetch the photo; keep the old one if the API is unreachable."""
        data = self.student_data
        location = data.student.photo_location if data else None
        self._fetching = True
        try:
            photo = (
                await self.coordinator.client.get_photo(location) if location else None
            )
        except SmartTagApiError as exception:
            LOGGER.debug("Could not fetch photo: %s", exception)
            return
        finally:
            self._fetching = False
        self._checked = dt_util.utcnow()
        image, content_type = photo if photo else (None, "image/jpeg")
        if image != self._image:
            self._image = image
            self._attr_content_type = content_type
            self._attr_image_last_updated = self._checked if image else None
            self.async_write_ha_state()

    async def async_image(self) -> bytes | None:
        """Return the photo bytes."""
        return self._image
