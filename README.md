# RoborockMqtt

Bridge between `python-miio` and an MQTT broker. Exposes a Roborock (or other miio-compatible) vacuum on MQTT topics so it can be controlled from Home Assistant, Node-RED, scripts, etc.

## How to get your vacuum token

A miio token (32 hex chars) is required. Extract it from the Mi Home Android backup or via your preferred method.

## Configuration

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `VACUUM_IP` | yes | — | IP of the vacuum |
| `VACUUM_TOKEN` | yes | — | Miio token of the vacuum (32 hex chars) |
| `BROKER_IP` | yes | — | MQTT broker host |
| `BROKER_PORT` | no | `1883` | MQTT broker port |
| `BROKER_USERNAME` | no | — | MQTT username |
| `BROKER_PASSWORD` | no | — | MQTT password |
| `TOPIC_PREFIX` | no | `roborock` | Base topic |
| `MIIO_DEVICE` | no | `roborockvacuum` | miiocli device subcommand (e.g. `dreamevacuum`, `viomivacuum`, `g1vacuum`) |
| `STATUS_INTERVAL` | no | `600` | Status publish interval (s) |
| `CONSUMABLE_INTERVAL` | no | `86400` | Consumable status interval (s) |
| `ALIVE_INTERVAL` | no | `240` | Alive heartbeat interval (s) |
| `LOG_LEVEL` | no | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

## Run with Docker (recommended)

```bash
docker compose up -d --build
docker compose logs -f
```

The container uses `network_mode: host` because miio device discovery needs LAN access.

To update after pulling new code:

```bash
git pull
docker compose up -d --build
```

## Run locally

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

## MQTT topics

All topics are prefixed by `TOPIC_PREFIX` (default `roborock`).

| Topic | Direction | Payload |
| --- | --- | --- |
| `roborock/command` | in | Any miiocli subcommand: `start`, `stop`, `home`, `pause`, `find`, `fan_speed`, `set_fan_speed 60`, `consumable_status`, ... |
| `roborock/status` | out | Vacuum status JSON, every `STATUS_INTERVAL` seconds |
| `roborock/consumable_status` | out | Consumable status JSON, every `CONSUMABLE_INTERVAL` seconds |
| `roborock/alive` | out | `1` every `ALIVE_INTERVAL` seconds, retained `0` on disconnect (LWT) |
| `roborock/result` | out | Result of any ad-hoc command sent on `roborock/command` |
| `roborock/error` | out | Error output from miiocli, prefixed by the originating topic |

### Examples

```bash
mosquitto_pub -t roborock/command -m "start"
mosquitto_pub -t roborock/command -m "stop"
mosquitto_pub -t roborock/command -m "home"
mosquitto_pub -t roborock/command -m "set_fan_speed 60"
```

Subscribe to everything:

```bash
mosquitto_sub -t 'roborock/#' -v
```

## Troubleshooting

- **`No such command 'roborockvacuum'`** — your vacuum is a different vendor. Set `MIIO_DEVICE` in `.env` to one of: `dreamevacuum`, `viomivacuum`, `g1vacuum`, ...
- **`TypeError: argument of type 'bool' is not iterable`** — `click` 8.2+ is incompatible with `python-miio` 0.5.12. `requirements.txt` already pins `click<8.2`; rebuild with `docker compose build --no-cache`.
- **Cannot reach the vacuum** — make sure the container can reach `VACUUM_IP`. The compose file uses `network_mode: host` for that reason.
