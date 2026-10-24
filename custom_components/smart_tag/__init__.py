"""
Custom integration to integrate SMART tag with Home Assistant.

For more details about this integration, please refer to
https://github.com/sNNNeaker/homeassistant-smart-tag
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.const import Platform
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .api import SmartTagApiClient
from .const import CONF_ACCESS_TOKEN, CONF_REFRESH_TOKEN
from .coordinator import SmartTagCoordinator
from .data import SmartTagData

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import SmartTagEntry

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
]


# https://developers.home-assistant.io/docs/config_entries_index/#setting-up-an-entry
async def async_setup_entry(
    hass: HomeAssistant,
    entry: SmartTagEntry,
) -> bool:
    """Set up this integration using UI."""
    client = SmartTagApiClient(
        session=async_create_clientsession(hass),
        access_token=entry.data[CONF_ACCESS_TOKEN],
        refresh_token=entry.data[CONF_REFRESH_TOKEN],
    )
    coordinator = SmartTagCoordinator(hass, entry, client)
    entry.runtime_data = SmartTagData(client=client, coordinator=coordinator)

    # https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
    await coordinator.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Reload only when the options change (token updates modify entry.data).
    options_at_setup = dict(entry.options)

    async def _async_options_updated(
        hass: HomeAssistant, updated_entry: SmartTagEntry
    ) -> None:
        """Reload the entry if its options changed."""
        if dict(updated_entry.options) != options_at_setup:
            hass.config_entries.async_schedule_reload(updated_entry.entry_id)

    entry.async_on_unload(entry.add_update_listener(_async_options_updated))

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: SmartTagEntry,
) -> bool:
    """Handle removal of an entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
