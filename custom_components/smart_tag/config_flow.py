"""Adds config flow for SMART tag."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .api import (
    SmartTagApiAuthError,
    SmartTagApiClient,
    SmartTagApiError,
    SmartTagApiNetworkError,
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
)

if TYPE_CHECKING:
    from collections.abc import Mapping


class SmartTagConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config flow for SMART tag."""

    VERSION = 1

    async def _async_login(
        self, email: str, password: str, errors: dict[str, str]
    ) -> SmartTagApiClient | None:
        """Log in and check for students; set errors and return None on failure."""
        client = SmartTagApiClient(async_create_clientsession(self.hass))
        try:
            await client.login(email, password)
            students = await client.get_students()
        except SmartTagApiAuthError as exception:
            LOGGER.warning(exception)
            errors["base"] = "auth"
        except SmartTagApiNetworkError as exception:
            LOGGER.error(exception)
            errors["base"] = "connection"
        except SmartTagApiError as exception:
            LOGGER.exception(exception)
            errors["base"] = "unknown"
        else:
            if students:
                return client
            errors["base"] = "no_students"
        return None

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle a flow initialized by the user."""
        errors: dict[str, str] = {}
        if user_input is not None:
            email = user_input[CONF_EMAIL].strip()
            client = await self._async_login(email, user_input[CONF_PASSWORD], errors)
            if client is not None:
                await self.async_set_unique_id(email.lower())
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=email,
                    data={
                        CONF_EMAIL: email,
                        CONF_ACCESS_TOKEN: client.access_token,
                        CONF_REFRESH_TOKEN: client.refresh_token,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_EMAIL,
                        # prefill with the email they entered
                        default=user_input.get(CONF_EMAIL, vol.UNDEFINED)
                        if user_input
                        else vol.UNDEFINED,
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.EMAIL,
                        ),
                    ),
                    vol.Required(CONF_PASSWORD): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.PASSWORD,
                        ),
                    ),
                },
            ),
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Handle a reauthentication request."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the password again."""
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            client = await self._async_login(
                entry.data[CONF_EMAIL], user_input[CONF_PASSWORD], errors
            )
            if client is not None:
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={
                        CONF_ACCESS_TOKEN: client.access_token,
                        CONF_REFRESH_TOKEN: client.refresh_token,
                    },
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PASSWORD): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.PASSWORD,
                        ),
                    ),
                },
            ),
            description_placeholders={"email": entry.data[CONF_EMAIL]},
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> SmartTagOptionsFlow:
        """Return the options flow."""
        return SmartTagOptionsFlow()


class SmartTagOptionsFlow(OptionsFlow):
    """Options flow: ride windows used for adaptive polling."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        options = self.config_entry.options
        time_selector = selector.TimeSelector()
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_MORNING_START,
                        default=options.get(CONF_MORNING_START, DEFAULT_MORNING_START),
                    ): time_selector,
                    vol.Required(
                        CONF_MORNING_END,
                        default=options.get(CONF_MORNING_END, DEFAULT_MORNING_END),
                    ): time_selector,
                    vol.Required(
                        CONF_AFTERNOON_START,
                        default=options.get(
                            CONF_AFTERNOON_START, DEFAULT_AFTERNOON_START
                        ),
                    ): time_selector,
                    vol.Required(
                        CONF_AFTERNOON_END,
                        default=options.get(CONF_AFTERNOON_END, DEFAULT_AFTERNOON_END),
                    ): time_selector,
                    vol.Required(
                        CONF_WEEKDAYS_ONLY,
                        default=options.get(CONF_WEEKDAYS_ONLY, DEFAULT_WEEKDAYS_ONLY),
                    ): selector.BooleanSelector(),
                }
            ),
        )
