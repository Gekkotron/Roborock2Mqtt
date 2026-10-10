"""
Home Assistant MQTT discovery for the Roborock bridge.

Pure functions only (no MQTT, no subprocess) so they can be unit tested:
- discovery_config(): the retained config announcing the vacuum
- vacuum_state(): miiocli status -> JSON state published on <prefix>/ha/state
- command_for() / fan_speed_command(): an HA command -> the miiocli command to run
"""
import json
import re

# miio vacuum state codes -> HA vacuum state; anything unlisted is idle
_STATES = {
    **dict.fromkeys((5, 11, 16, 17, 18), "cleaning"),
    **dict.fromkeys((6, 15), "returning"),
    **dict.fromkeys((8, 100), "docked"),
    10: "paused",
    **dict.fromkeys((9, 12), "error"),
}

# HA command payload -> miiocli subcommand
_ACTIONS = {"start": "start", "pause": "pause", "stop": "stop", "return_to_base": "home", "locate": "find"}

SUPPORTED_FEATURES = ["start", "pause", "stop", "return_home", "locate", "fan_speed", "battery", "status"]


def discovery_enabled(value):
    """ HA_DISCOVERY_ENABLED: off unless true/1/yes/on """
    return (value or "").strip().lower() in ("true", "1", "yes", "on")


def parse_json(text):
    """ miiocli JSON output as a dict, None for errors and anything else """
    try:
        data = json.loads(text)
    except (TypeError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def vacuum_state(status, presets):
    fan_power = status.get("fan_power")
    fan_speed = next((name for name, code in presets.items() if code == fan_power), None)
    return {
        "state": _STATES.get(status.get("state"), "idle"),
        "battery_level": status.get("battery"),
        "fan_speed": fan_speed,
        "error_code": status.get("error_code", 0),
    }


def command_for(action):
    return _ACTIONS.get(action.strip())


def fan_speed_command(name, presets):
    code = presets.get(name.strip())
    return f"set_fan_speed {code}" if code is not None else None


def _unique_id(info, fallback_id):
    raw = (info.get("mac") or "").replace(":", "") or fallback_id
    return "roborock_" + re.sub(r"[^0-9A-Za-z]+", "_", raw).strip("_").lower()


def discovery_config(prefix, discovery_prefix, info, presets, fallback_id):
    """ (topic, payload) announcing the vacuum with the HA state schema """
    uid = _unique_id(info, fallback_id)
    device = {"identifiers": [uid], "name": "Roborock", "manufacturer": "Roborock"}
    if info.get("model"):
        device["model"] = info["model"]
    if info.get("fw_ver"):
        device["sw_version"] = info["fw_ver"]
    payload = {
        "name": None,
        "unique_id": uid,
        "object_id": uid,
        "device": device,
        "state_topic": f"{prefix}/ha/state",
        "command_topic": f"{prefix}/ha/command",
        "set_fan_speed_topic": f"{prefix}/ha/fan_speed/set",
        "fan_speed_list": list(presets),
        "supported_features": list(SUPPORTED_FEATURES),
        "availability_topic": f"{prefix}/alive",
        "payload_available": "1",
        "payload_not_available": "0",
    }
    return f"{discovery_prefix}/vacuum/{uid}/{uid}/config", payload


def redact_info(text):
    """ an `info` result without the miio token; anything else unchanged """
    data = parse_json(text)
    if data is None or "token" not in data:
        return text
    data.pop("token")
    return json.dumps(data, indent=2)


def route(topic, prefix):
    return {
        f"{prefix}/command": "command",
        f"{prefix}/ha/command": "ha_command",
        f"{prefix}/ha/fan_speed/set": "ha_fan_speed",
    }.get(topic)
