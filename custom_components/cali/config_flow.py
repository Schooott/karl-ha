"""Config- und Options-Flow: Freigabe von Entities für Cali."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import CONF_ENTITIES, DOMAIN


class CaliConfigFlow(ConfigFlow, domain=DOMAIN):
    """Einmalige Einrichtung – die eigentliche Freigabe passiert in den Optionen."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        if user_input is not None:
            return self.async_create_entry(title="Cali", data={})
        return self.async_show_form(step_id="user")

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return CaliOptionsFlow()


class CaliOptionsFlow(OptionsFlow):
    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = self.config_entry.options.get(CONF_ENTITIES, [])

        # Effektive Freigabemenge anzeigen: explizite Auswahl + Label "cali"
        from . import exposed_entity_ids

        exposed = sorted(exposed_entity_ids(self.hass))
        lines = []
        for entity_id in exposed[:40]:
            state = self.hass.states.get(entity_id)
            name = state.attributes.get("friendly_name") if state else None
            if name and name != entity_id:
                lines.append(f"- **{name}** (`{entity_id}`)")
            else:
                lines.append(f"- `{entity_id}`")
        if len(exposed) > 40:
            lines.append(f"- … und {len(exposed) - 40} weitere")
        exposed_text = "\n".join(lines) if lines else "*keine*"

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_ENTITIES, default=list(current)
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(multiple=True)
                    ),
                }
            ),
            description_placeholders={
                "count": str(len(exposed)),
                "exposed": exposed_text,
            },
        )
