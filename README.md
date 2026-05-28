# RoborockMqtt

Bridge between [python-miio](https://github.com/rytilahti/python-miio/blob/master/miio/vacuum.py) and an MQTT broker.

## Configuration

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `VACUUM_IP` | yes | — | IP of the Roborock vacuum |
| `VACUUM_TOKEN` | yes | — | Miio token of the vacuum |
| `BROKER_IP` | yes | — | MQTT broker host |
| `BROKER_PORT` | no | `1883` | MQTT broker port |
| `BROKER_USERNAME` | no | — | MQTT username (optional) |
| `BROKER_PASSWORD` | no | — | MQTT password (optional) |
| `TOPIC_PREFIX` | no | `roborock` | Base topic |
| `MIIO_DEVICE` | no | `roborockvacuum` | miiocli device subcommand (e.g. `dreamevacuum`, `viomivacuum`) |
| `STATUS_INTERVAL` | no | `600` | Status publish interval (s) |
| `CONSUMABLE_INTERVAL` | no | `86400` | Consumable status interval (s) |
| `ALIVE_INTERVAL` | no | `240` | Alive heartbeat interval (s) |
| `LOG_LEVEL` | no | `INFO` | `DEBUG`, `INFO`, `WARNING`, ... |

## Run with Docker

```bash
docker compose up -d --build
```

Logs:

```bash
docker compose logs -f
```

## Run locally

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Topics

- `roborock/command` — send a miiocli vacuum command (e.g. `start`, `stop`, `home`)
- `roborock/status` — vacuum status, published every `STATUS_INTERVAL` seconds
- `roborock/consumable_status` — published every `CONSUMABLE_INTERVAL` seconds
- `roborock/alive` — heartbeat (`1`) every `ALIVE_INTERVAL` seconds, `0` on disconnect
- `roborock/result` — result of ad-hoc commands
- `roborock/error` — errors

Example:

```bash
mosquitto_pub -t roborock/command -m "start"
mosquitto_pub -t roborock/command -m "stop"
mosquitto_pub -t roborock/command -m "home"
```
