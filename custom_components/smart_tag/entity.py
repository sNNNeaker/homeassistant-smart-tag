"""SmartTagEntity class."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DOMAIN
from .coordinator import SmartTagCoordinator

if TYPE_CHECKING:
    from .data import StudentData


class SmartTagEntity(CoordinatorEntity[SmartTagCoordinator]):
    """Base entity for one student of a SMART tag account."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SmartTagCoordinator,
        student_id: int,
        key: str,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._student_id = student_id
        entry_id = coordinator.config_entry.entry_id
        self._attr_unique_id = f"{entry_id}_{student_id}_{key}"

        student = coordinator.data[student_id].student
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_{student_id}")},
            name=student.full_name,
            manufacturer="SMART tag",
            model=f"Grade {student.grade}" if student.grade else None,
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def student_data(self) -> StudentData | None:
        """Return the current data for this student."""
        return self.coordinator.data.get(self._student_id)

    @property
    def available(self) -> bool:
        """Return whether the entity is available."""
        return super().available and self.student_data is not None
