"""Konstanten für die Cali-Integration."""

DOMAIN = "cali"

# Event, das Cali über seine WebSocket-Subscription empfängt
EVENT_CALI_NOTIFY = "cali_notify"

# Internes Event: die Freigabemenge hat sich geändert → Clients laden neu
EVENT_CALI_ENTITIES_CHANGED = "cali_entities_changed"

# Entities mit diesem Label (auf Entity ODER Gerät) sind für Cali freigegeben,
# zusätzlich zur expliziten Auswahl in den Integrations-Optionen.
CALI_LABEL = "cali"

CONF_ENTITIES = "entities"

VALID_EMOTIONS = [
    "neutral",
    "happy",
    "wink",
    "love",
    "surprised",
    "crazy",
    "sceptic",
    "tired",
    "sad",
    "denying",
    "angry",
    "broken",
]

# Serverseitige Whitelist: Welche Aktion darf Cali pro Domain ausführen und
# auf welchen Service wird sie abgebildet. Domains ohne Eintrag (z. B. lock,
# alarm_control_panel, sensor) sind read-only – Status ja, Steuern nein.
# Format: aktion -> (service_domain, service_name, erlaubte_parameter)
ALLOWED_ACTIONS: dict[str, dict[str, tuple[str, str, set[str]]]] = {
    "scene": {
        "activate": ("scene", "turn_on", set()),
    },
    "script": {
        "start": ("script", "turn_on", set()),
        "stop": ("script", "turn_off", set()),
    },
    "light": {
        "turn_on": ("light", "turn_on", {"brightness_pct"}),
        "turn_off": ("light", "turn_off", set()),
        "toggle": ("light", "toggle", set()),
    },
    "switch": {
        "turn_on": ("switch", "turn_on", set()),
        "turn_off": ("switch", "turn_off", set()),
        "toggle": ("switch", "toggle", set()),
    },
    "input_boolean": {
        "turn_on": ("input_boolean", "turn_on", set()),
        "turn_off": ("input_boolean", "turn_off", set()),
        "toggle": ("input_boolean", "toggle", set()),
    },
    "cover": {
        "open": ("cover", "open_cover", set()),
        "close": ("cover", "close_cover", set()),
        "stop": ("cover", "stop_cover", set()),
        "set_position": ("cover", "set_cover_position", {"position"}),
    },
    "climate": {
        "set_temperature": ("climate", "set_temperature", {"temperature"}),
    },
    "media_player": {
        "play": ("media_player", "media_play", set()),
        "pause": ("media_player", "media_pause", set()),
        "set_volume": ("media_player", "volume_set", {"volume_level"}),
    },
    "vacuum": {
        "start": ("vacuum", "start", set()),
        "return_to_base": ("vacuum", "return_to_base", set()),
    },
    "lawn_mower": {
        "start_mowing": ("lawn_mower", "start_mowing", set()),
        "dock": ("lawn_mower", "dock", set()),
    },
    "button": {
        "press": ("button", "press", set()),
    },
    "todo": {
        "add_item": ("todo", "add_item", {"item"}),
    },
}
