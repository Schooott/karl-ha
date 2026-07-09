"""Cali – macOS-Desktop-Assistent als Home-Assistant-Gegenstelle.

Stellt bereit:
- WebSocket-Commands cali/entities, cali/action, cali/subscribe
- Service cali.speak als Benachrichtigungsziel für Automationen
- Freigabe von Entities über das Label "cali" oder die Integrations-Optionen
"""

from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers import (
    area_registry as ar,
    config_validation as cv,
    device_registry as dr,
    entity_registry as er,
)
from homeassistant.helpers.event import async_call_later

from . import websocket
from .const import (
    CONF_ENTITIES,
    DOMAIN,
    EVENT_CALI_ENTITIES_CHANGED,
    EVENT_CALI_NOTIFY,
    CALI_LABEL,
    VALID_EMOTIONS,
)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

SPEAK_SCHEMA = vol.Schema(
    {
        vol.Required("message"): cv.string,
        vol.Optional("emotion"): vol.In(VALID_EMOTIONS),
        vol.Optional("wake", default=True): cv.boolean,
    }
)


class ExposureCache:
    """Cached Menge der für Cali freigegebenen entity_ids.

    Quelle: Label "cali" auf Entities oder Geräten + explizite Auswahl in den
    Integrations-Optionen. Invalidiert sich bei Registry- und Options-Änderungen.
    """

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self._hass = hass
        self._entry = entry
        self._cached: set[str] | None = None
        self._last_known: set[str] = set()
        self._debounce_cancel = None
        self._unsubs = [
            hass.bus.async_listen(
                er.EVENT_ENTITY_REGISTRY_UPDATED, self._invalidate
            ),
            hass.bus.async_listen(
                dr.EVENT_DEVICE_REGISTRY_UPDATED, self._invalidate
            ),
            entry.add_update_listener(self._entry_updated),
        ]

    @callback
    def _invalidate(self, _event=None) -> None:
        if self._cached is not None:
            self._last_known = self._cached
        self._cached = None
        # Debounced prüfen, ob sich die Freigabemenge wirklich geändert hat –
        # Registry-Events feuern für JEDE Entity im System.
        if self._debounce_cancel is not None:
            self._debounce_cancel()
        self._debounce_cancel = async_call_later(self._hass, 2.0, self._emit_if_changed)

    @callback
    def _emit_if_changed(self, _now) -> None:
        self._debounce_cancel = None
        new = self.entity_ids()
        if new != self._last_known:
            self._last_known = new
            self._hass.bus.async_fire(EVENT_CALI_ENTITIES_CHANGED)

    async def _entry_updated(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self._invalidate()

    @callback
    def entity_ids(self) -> set[str]:
        if self._cached is not None:
            return self._cached

        ids: set[str] = set(self._entry.options.get(CONF_ENTITIES, []))
        ent_reg = er.async_get(self._hass)
        dev_reg = dr.async_get(self._hass)

        labeled_devices = {
            device.id
            for device in dev_reg.devices.values()
            if CALI_LABEL in device.labels
        }
        for entity in ent_reg.entities.values():
            if entity.disabled_by is not None or entity.hidden_by is not None:
                continue
            if CALI_LABEL in entity.labels or entity.device_id in labeled_devices:
                ids.add(entity.entity_id)

        self._cached = ids
        return ids

    @callback
    def shutdown(self) -> None:
        if self._debounce_cancel is not None:
            self._debounce_cancel()
            self._debounce_cancel = None
        for unsub in self._unsubs:
            unsub()


async def async_setup(hass: HomeAssistant, config) -> bool:
    """Einmalige Registrierung von WebSocket-Commands und Services."""
    websocket.async_register(hass)

    async def handle_speak(call: ServiceCall) -> None:
        hass.bus.async_fire(
            EVENT_CALI_NOTIFY,
            {
                "message": call.data["message"],
                "emotion": call.data.get("emotion"),
                "wake": call.data.get("wake", True),
            },
        )

    hass.services.async_register(DOMAIN, "speak", handle_speak, schema=SPEAK_SCHEMA)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})["exposure"] = ExposureCache(hass, entry)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    cache: ExposureCache | None = hass.data.get(DOMAIN, {}).pop("exposure", None)
    if cache is not None:
        cache.shutdown()
    return True


@callback
def exposed_entity_ids(hass: HomeAssistant) -> set[str]:
    """Aktuelle Freigabemenge – leere Menge, wenn die Integration nicht läuft."""
    cache: ExposureCache | None = hass.data.get(DOMAIN, {}).get("exposure")
    if cache is None:
        return set()
    return cache.entity_ids()


@callback
def entity_payload(hass: HomeAssistant, entity_id: str) -> dict | None:
    """Kompakte Beschreibung einer Entity für Calis Cache."""
    state = hass.states.get(entity_id)
    ent_reg = er.async_get(hass)
    dev_reg = dr.async_get(hass)
    area_reg = ar.async_get(hass)

    entry = ent_reg.async_get(entity_id)
    name = None
    area_name = None
    if entry is not None:
        name = entry.name or entry.original_name
        area_id = entry.area_id
        if area_id is None and entry.device_id:
            device = dev_reg.async_get(entry.device_id)
            if device is not None:
                area_id = device.area_id
        if area_id is not None:
            area = area_reg.async_get_area(area_id)
            if area is not None:
                area_name = area.name
    if state is not None and not name:
        name = state.attributes.get("friendly_name")

    domain = entity_id.split(".")[0]
    from .const import ALLOWED_ACTIONS  # zyklische Importe vermeiden

    payload: dict = {
        "entity_id": entity_id,
        "name": name or entity_id,
        "domain": domain,
        "area": area_name,
        "state": state.state if state is not None else "unavailable",
        "actions": sorted(ALLOWED_ACTIONS.get(domain, {})),
    }
    if state is not None:
        attrs = {}
        for key in (
            "unit_of_measurement",
            "device_class",
            "current_position",
            "temperature",
            "current_temperature",
            "brightness",
            "volume_level",
        ):
            if key in state.attributes:
                attrs[key] = state.attributes[key]
        if attrs:
            payload["attributes"] = attrs
    return payload
