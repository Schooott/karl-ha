"""WebSocket-API für Karl: Entities lesen, Aktionen ausführen, Events abonnieren."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.core import Event, HomeAssistant, callback

from .const import (
    ALLOWED_ACTIONS,
    DOMAIN,
    EVENT_KARL_ENTITIES_CHANGED,
    EVENT_KARL_NOTIFY,
)


@callback
def async_register(hass: HomeAssistant) -> None:
    websocket_api.async_register_command(hass, ws_entities)
    websocket_api.async_register_command(hass, ws_action)
    websocket_api.async_register_command(hass, ws_subscribe)


@websocket_api.websocket_command({vol.Required("type"): "karl/entities"})
@callback
def ws_entities(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Alle für Karl freigegebenen Entities, kompakt aufbereitet."""
    from . import entity_payload, exposed_entity_ids

    entities = [
        payload
        for entity_id in sorted(exposed_entity_ids(hass))
        if (payload := entity_payload(hass, entity_id)) is not None
    ]
    connection.send_result(msg["id"], {"entities": entities})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "karl/action",
        vol.Required("entity_id"): str,
        vol.Required("action"): str,
        vol.Optional("params"): dict,
    }
)
@websocket_api.async_response
async def ws_action(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Whitelisted Aktion auf einer freigegebenen Entity ausführen."""
    from . import entity_payload, exposed_entity_ids

    entity_id: str = msg["entity_id"]
    action: str = msg["action"]
    params: dict = msg.get("params") or {}

    if entity_id not in exposed_entity_ids(hass):
        connection.send_error(
            msg["id"], "not_exposed", f"{entity_id} ist nicht für Karl freigegeben."
        )
        return

    domain = entity_id.split(".")[0]
    domain_actions = ALLOWED_ACTIONS.get(domain, {})
    if action not in domain_actions:
        connection.send_error(
            msg["id"],
            "action_not_allowed",
            f"Aktion '{action}' ist für {domain} nicht erlaubt. "
            f"Erlaubt: {sorted(domain_actions) or 'keine (read-only)'}.",
        )
        return

    service_domain, service_name, allowed_params = domain_actions[action]
    service_data: dict[str, Any] = {"entity_id": entity_id}
    for key, value in params.items():
        if key in allowed_params:
            service_data[key] = value

    await hass.services.async_call(
        service_domain, service_name, service_data, blocking=True
    )
    connection.send_result(
        msg["id"], {"ok": True, "entity": entity_payload(hass, entity_id)}
    )


@websocket_api.websocket_command({vol.Required("type"): "karl/subscribe"})
@callback
def ws_subscribe(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Abonniert karl_notify-Events und Zustandsänderungen freigegebener Entities."""
    from . import entity_payload, exposed_entity_ids

    @callback
    def forward_notify(event: Event) -> None:
        connection.send_message(
            websocket_api.event_message(
                msg["id"],
                {
                    "event": "notify",
                    "message": event.data.get("message", ""),
                    "emotion": event.data.get("emotion"),
                    "wake": event.data.get("wake", True),
                },
            )
        )

    @callback
    def forward_state(event: Event) -> None:
        entity_id = event.data.get("entity_id")
        if entity_id not in exposed_entity_ids(hass):
            return
        connection.send_message(
            websocket_api.event_message(
                msg["id"],
                {
                    "event": "state",
                    "entity": entity_payload(hass, entity_id),
                },
            )
        )

    @callback
    def forward_entities_changed(event: Event) -> None:
        connection.send_message(
            websocket_api.event_message(msg["id"], {"event": "entities_changed"})
        )

    unsub_notify = hass.bus.async_listen(EVENT_KARL_NOTIFY, forward_notify)
    unsub_state = hass.bus.async_listen("state_changed", forward_state)
    unsub_changed = hass.bus.async_listen(
        EVENT_KARL_ENTITIES_CHANGED, forward_entities_changed
    )

    @callback
    def unsubscribe() -> None:
        unsub_notify()
        unsub_state()
        unsub_changed()

    connection.subscriptions[msg["id"]] = unsubscribe
    connection.send_result(msg["id"])
