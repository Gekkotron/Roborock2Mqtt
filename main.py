import logging
import os
import shlex
import signal
import subprocess
import threading

import paho.mqtt.client as mqtt
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("roborock-mqtt")


def _required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


VACUUM_IP = _required("VACUUM_IP")
VACUUM_TOKEN = _required("VACUUM_TOKEN")
BROKER_IP = _required("BROKER_IP")
BROKER_PORT = int(os.getenv("BROKER_PORT", "1883"))
BROKER_USERNAME = os.getenv("BROKER_USERNAME")
BROKER_PASSWORD = os.getenv("BROKER_PASSWORD")
TOPIC_PREFIX = os.getenv("TOPIC_PREFIX", "roborock").rstrip("/")
MIIO_DEVICE = os.getenv("MIIO_DEVICE", "roborockvacuum")

STATUS_INTERVAL = int(os.getenv("STATUS_INTERVAL", "600"))
CONSUMABLE_INTERVAL = int(os.getenv("CONSUMABLE_INTERVAL", str(24 * 3600)))
ALIVE_INTERVAL = int(os.getenv("ALIVE_INTERVAL", "240"))

shutdown = threading.Event()
timers: list[threading.Timer] = []


def topic(suffix: str) -> str:
    return f"{TOPIC_PREFIX}/{suffix}"


def miiocli(command: str) -> str:
    args = [
        "miiocli",
        "-o", "json_pretty",
        MIIO_DEVICE,
        "--ip", VACUUM_IP,
        "--token", VACUUM_TOKEN,
        *shlex.split(command),
    ]
    try:
        result = subprocess.run(
            args, capture_output=True, text=True, timeout=30, check=False
        )
    except subprocess.TimeoutExpired:
        log.warning("miiocli timed out: %s", command)
        return "Error: miiocli timeout"

    output = (result.stdout or result.stderr).strip()
    if result.returncode != 0:
        log.warning("miiocli failed (%s): %s", result.returncode, output)
    return output


def publish(client: mqtt.Client, dest: str, message: str) -> None:
    if "Error" in message:
        client.publish(topic("error"), message.replace("Error:", dest + " -->"))
    else:
        client.publish(dest, message)


def schedule(interval: int, fn) -> None:
    if shutdown.is_set():
        return
    t = threading.Timer(interval, fn)
    t.daemon = True
    t.start()
    timers.append(t)


def status(client: mqtt.Client) -> None:
    publish(client, topic("status"), miiocli("status"))
    schedule(STATUS_INTERVAL, lambda: status(client))


def consumable_status(client: mqtt.Client) -> None:
    publish(client, topic("consumable_status"), miiocli("consumable_status"))
    schedule(CONSUMABLE_INTERVAL, lambda: consumable_status(client))


def alive(client: mqtt.Client) -> None:
    client.publish(topic("alive"), "1")
    schedule(ALIVE_INTERVAL, lambda: alive(client))


def on_connect(client, userdata, flags, reason_code, properties=None):
    log.info("Connected to MQTT broker (code=%s)", reason_code)
    client.subscribe(topic("#"))
    status(client)
    consumable_status(client)
    alive(client)


def on_disconnect(client, userdata, *args):
    log.warning("Disconnected from MQTT broker")


def on_message(client, userdata, msg):
    payload = msg.payload.decode("utf-8", errors="replace")
    log.debug("MQTT %s: %s", msg.topic, payload)

    if not msg.topic.endswith("/command"):
        return

    result = miiocli(payload)
    if payload == "status":
        publish(client, topic("status"), result)
    elif payload == "consumable_status":
        publish(client, topic("consumable_status"), result)
    else:
        publish(client, topic("result"), result)


def handle_signal(signum, _frame):
    log.info("Signal %s received, shutting down", signum)
    shutdown.set()
    for t in timers:
        t.cancel()


def main() -> None:
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "Roborock")
    if BROKER_USERNAME:
        client.username_pw_set(BROKER_USERNAME, BROKER_PASSWORD)
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    client.will_set(topic("alive"), payload="0", retain=True)

    log.info("Connecting to MQTT %s:%s", BROKER_IP, BROKER_PORT)
    client.connect(BROKER_IP, BROKER_PORT, 60)
    client.loop_forever()


if __name__ == "__main__":
    main()
