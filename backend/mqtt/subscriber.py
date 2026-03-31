import json
import os

import paho.mqtt.client as mqtt
from dotenv import load_dotenv

from db.influx import write_sensor
from db.sqlite import record_sensor, record_sensor_combined

load_dotenv()

TOPICS = {
    "autogrow/soil": ("soil", "moisture", "soil"),
    "autogrow/temp": ("climate", "temperature", "temp"),
    "autogrow/humidity": ("climate", "humidity", "humidity"),
    "autogrow/light": ("light", "lux", "light"),
    "autogrow/vibration": ("pump", "vibration", None),  # not in SensorReading table
}
SENSOR_TOPIC_SUFFIX = "/autogrow/sensors"


def _record_combined_sensor(payload: dict):
    soil_raw = payload.get("soil_pct")
    soil = soil_raw if soil_raw is not None else payload.get("soil")
    temp1 = payload.get("temp1")
    temp2 = payload.get("temp2")
    humidity = payload.get("humidity")
    light_raw = payload.get("light_lux")
    light = light_raw if light_raw is not None else payload.get("light")
    vibr = payload.get("vibration")

    try:
        temp_val = (float(temp1) + float(temp2)) / 2 if (temp1 and temp2) else float(temp1 or temp2 or 0)
        record_sensor_combined(
            soil=float(soil) if soil is not None else 0.0,
            temp=temp_val,
            humidity=float(humidity) if humidity is not None else 0.0,
            light=float(light) if light is not None else 0.0,
        )
        print(f"[MQTT] SQLite saved: soil={soil} temp={temp_val} humidity={humidity} light={light}")
    except Exception as e:
        print(f"[MQTT] SQLite combined record error: {e}")

    if vibr is not None:
        try:
            write_sensor("pump", "vibration", float(vibr))
        except Exception as e:
            print(f"[MQTT] vibration record error: {e}")


def on_message(client, userdata, msg):
    topic = msg.topic

    try:
        payload = json.loads(msg.payload.decode())
    except Exception as e:
        print(f"[MQTT] invalid JSON payload: {e}")
        return

    # Legacy per-topic format
    if topic in TOPICS:
        measurement, field, sqlite_field = TOPICS[topic]
        try:
            value = float(payload.get("value"))
        except Exception as e:
            print(f"[MQTT] invalid value for {topic}: {e}")
            return

        write_sensor(measurement, field, value)
        if sqlite_field:
            try:
                record_sensor(sqlite_field, value)
            except Exception as e:
                print(f"[MQTT] SQLite write failed: {e}")

        print(f"[MQTT] {topic} → {value}")

    # New combined JSON payload from ESP32
    elif topic.endswith(SENSOR_TOPIC_SUFFIX):
        _record_combined_sensor(payload)
        print(f"[MQTT] combined payload saved for {topic}")
    else:
        print(f"[MQTT] unhandled topic: {topic}")


def start_subscriber():
    """Start MQTT listener or short-circuit if hardware/broker is not ready."""

    broker = os.getenv("MQTT_BROKER")
    port = os.getenv("MQTT_PORT")

    if not broker or not port:
        print("[MQTT] Skipping subscriber (MQTT_BROKER/MQTT_PORT not set).")
        return

    try:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        client.on_message = on_message
        mqtt_user = os.getenv("MQTT_USER")
        mqtt_pass = os.getenv("MQTT_PASS")
        if mqtt_user and mqtt_pass:
            client.username_pw_set(mqtt_user, mqtt_pass)

        client.connect(broker, int(port))

        for topic in TOPICS:
            client.subscribe(topic)
        client.subscribe("+/autogrow/sensors")  # subscribe dynamic user-topic prefix

        client.loop_start()
        print(f"[MQTT] Subscriber started on {broker}:{port}")
    except Exception as e:
        print(f"[MQTT] Could not connect: {e} — running without MQTT")
