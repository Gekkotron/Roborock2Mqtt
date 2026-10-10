import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import ha_discovery as ha

PRESETS = {"Silent": 101, "Standard": 102, "Medium": 103, "Turbo": 104, "Gentle": 105, "Auto": 106}
STATUS = {"state": 8, "battery": 100, "fan_power": 104, "error_code": 0, "in_cleaning": 0}
INFO = {"model": "roborock.vacuum.s5", "fw_ver": "3.5.8_002034", "mac": "40:31:3C:A8:B9:64", "token": "secret"}


class DiscoveryEnabledTest(unittest.TestCase):
    def test_default_off(self):
        self.assertFalse(ha.discovery_enabled(None))
        self.assertFalse(ha.discovery_enabled(""))
        self.assertFalse(ha.discovery_enabled("false"))

    def test_on(self):
        for value in ("true", "1", "yes", "on", " TRUE "):
            self.assertTrue(ha.discovery_enabled(value))


class ParseJsonTest(unittest.TestCase):
    def test_object(self):
        self.assertEqual(ha.parse_json('{"state": 8}'), {"state": 8})

    def test_not_an_object(self):
        self.assertIsNone(ha.parse_json("Error: miiocli timeout"))
        self.assertIsNone(ha.parse_json(""))
        self.assertIsNone(ha.parse_json("[1, 2]"))


class VacuumStateTest(unittest.TestCase):
    def test_docked(self):
        self.assertEqual(ha.vacuum_state(STATUS, PRESETS),
                         {"state": "docked", "battery_level": 100, "fan_speed": "Turbo", "error_code": 0})

    def test_state_mapping(self):
        expected = {
            5: "cleaning", 11: "cleaning", 16: "cleaning", 17: "cleaning", 18: "cleaning",
            6: "returning", 15: "returning", 8: "docked", 100: "docked", 10: "paused",
            9: "error", 12: "error", 1: "idle", 2: "idle", 3: "idle", 13: "idle", 14: "idle", 999: "idle",
        }
        for code, state in expected.items():
            self.assertEqual(ha.vacuum_state({**STATUS, "state": code}, PRESETS)["state"], state, code)

    def test_unknown_fan_power(self):
        self.assertIsNone(ha.vacuum_state({**STATUS, "fan_power": 60}, PRESETS)["fan_speed"])

    def test_missing_fields(self):
        self.assertEqual(ha.vacuum_state({}, PRESETS),
                         {"state": "idle", "battery_level": None, "fan_speed": None, "error_code": 0})


class CommandTest(unittest.TestCase):
    def test_actions(self):
        self.assertEqual(ha.command_for("start"), "start")
        self.assertEqual(ha.command_for("pause"), "pause")
        self.assertEqual(ha.command_for("stop"), "stop")
        self.assertEqual(ha.command_for("return_to_base"), "home")
        self.assertEqual(ha.command_for("locate"), "find")
        self.assertEqual(ha.command_for(" start\n"), "start")

    def test_unknown_action(self):
        self.assertIsNone(ha.command_for("clean_spot"))
        self.assertIsNone(ha.command_for("rm -rf"))

    def test_fan_speed(self):
        self.assertEqual(ha.fan_speed_command("Turbo", PRESETS), "set_fan_speed 104")
        self.assertIsNone(ha.fan_speed_command("Max", PRESETS))


class DiscoveryConfigTest(unittest.TestCase):
    def test_payload(self):
        topic, payload = ha.discovery_config("roborock", "homeassistant", INFO, PRESETS, "192.168.1.200")
        self.assertEqual(topic, "homeassistant/vacuum/roborock_40313ca8b964/roborock_40313ca8b964/config")
        self.assertEqual(payload["unique_id"], "roborock_40313ca8b964")
        self.assertIsNone(payload["name"])
        self.assertEqual(payload["state_topic"], "roborock/ha/state")
        self.assertEqual(payload["command_topic"], "roborock/ha/command")
        self.assertEqual(payload["set_fan_speed_topic"], "roborock/ha/fan_speed/set")
        self.assertEqual(payload["fan_speed_list"], ["Silent", "Standard", "Medium", "Turbo", "Gentle", "Auto"])
        self.assertEqual(payload["supported_features"],
                         ["start", "pause", "stop", "return_home", "locate", "fan_speed", "battery", "status"])
        self.assertEqual(payload["availability_topic"], "roborock/alive")
        self.assertEqual((payload["payload_available"], payload["payload_not_available"]), ("1", "0"))
        self.assertEqual(payload["device"], {
            "identifiers": ["roborock_40313ca8b964"], "name": "Roborock", "manufacturer": "Roborock",
            "model": "roborock.vacuum.s5", "sw_version": "3.5.8_002034",
        })
        self.assertNotIn("secret", json.dumps(payload))

    def test_fallback_id_without_mac(self):
        topic, payload = ha.discovery_config("roborock", "homeassistant", {}, PRESETS, "192.168.1.200")
        self.assertEqual(payload["unique_id"], "roborock_192_168_1_200")
        self.assertNotIn("model", payload["device"])


class RedactInfoTest(unittest.TestCase):
    def test_drops_token(self):
        redacted = ha.redact_info(json.dumps(INFO))
        self.assertNotIn("secret", redacted)
        self.assertEqual(json.loads(redacted)["model"], "roborock.vacuum.s5")

    def test_passthrough(self):
        self.assertEqual(ha.redact_info("Error: timeout"), "Error: timeout")
        self.assertEqual(ha.redact_info('{"a": 1}'), '{"a": 1}')


class RouteTest(unittest.TestCase):
    def test_routes(self):
        self.assertEqual(ha.route("roborock/command", "roborock"), "command")
        self.assertEqual(ha.route("roborock/ha/command", "roborock"), "ha_command")
        self.assertEqual(ha.route("roborock/ha/fan_speed/set", "roborock"), "ha_fan_speed")

    def test_ignored(self):
        for topic in ("roborock/ha/state", "roborock/status", "roborock/result", "roborock/alive", "other/command"):
            self.assertIsNone(ha.route(topic, "roborock"), topic)


if __name__ == "__main__":
    unittest.main()
