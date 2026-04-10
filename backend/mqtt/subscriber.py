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

    # ── field ใหม่จาก ESP32 ──────────────────────────────────
    stage         = payload.get("stage")
    stage_name    = payload.get("stage_name")
    spectrum      = payload.get("spectrum")
    pump_on       = payload.get("pump_on")
    pump_status   = payload.get("pump_status")
    light_hrs     = payload.get("light_hrs_today")
    harvest_eta   = payload.get("harvest_eta_days")
    health_score  = payload.get("health_score")

    try:
        temp_val = (float(temp1) + float(temp2)) / 2 if (temp1 and temp2) else float(temp1 or temp2 or 0)
        record_sensor_combined(
            soil=float(soil) if soil is not None else 0.0,
            temp=temp_val,
            humidity=float(humidity) if humidity is not None else 0.0,
            light=float(light) if light is not None else 0.0,
            vibration=float(vibr) if vibr is not None else 0.0,
            # ── เพิ่มเข้าไป ──
            stage=int(stage) if stage is not None else 0,
            stage_name=stage_name or "",
            spectrum=spectrum or "",
            pump_on=bool(pump_on),
            pump_status=pump_status or "",
            light_hrs_today=float(light_hrs) if light_hrs is not None else 0.0,
            harvest_eta_days=int(harvest_eta) if harvest_eta is not None else 0,
            health_score=int(health_score) if health_score is not None else 0,
        )
        print(f"[MQTT] SQLite saved: stage={stage_name} soil={soil} temp={temp_val} health={health_score}")
    except Exception as e:
        print(f"[MQTT] SQLite combined record error: {e}")

    if vibr is not None:
        try:
            write_sensor("pump", "vibration", float(vibr))
            # เพิ่ม field อื่นใน InfluxDB ด้วย
            if stage is not None:
                write_sensor("autogrow", "stage", float(stage))
            if health_score is not None:
                write_sensor("autogrow", "health_score", float(health_score))
            if harvest_eta is not None:
                write_sensor("autogrow", "harvest_eta_days", float(harvest_eta))
        except Exception as e:
            print(f"[MQTT] InfluxDB record error: {e}")

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
    broker = os.getenv("MQTT_BROKER")
    port = os.getenv("MQTT_PORT")

    if not broker or not port:
        print("[MQTT] Skipping subscriber (MQTT_BROKER/MQTT_PORT not set).")
        return

    try:
        import random
        client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=f"autogrow_backend_{random.randint(1000,9999)}"
        )
        client.on_message = on_message

        # ── เพิ่ม on_connect เพื่อ subscribe หลัง connect สำเร็จ ──
        def on_connect(client, userdata, flags, rc, props=None):
            print(f"[MQTT] Connected rc={rc}")
            for topic in TOPICS:
                client.subscribe(topic)
            client.subscribe("+/autogrow/sensors")
            print(f"[MQTT] Subscribed to all topics")

        client.on_connect = on_connect

        mqtt_user = os.getenv("MQTT_USER")
        mqtt_pass = os.getenv("MQTT_PASS")
        if mqtt_user and mqtt_pass:
            client.username_pw_set(mqtt_user, mqtt_pass)

        client.connect(broker, int(port))
        client.loop_start()
        print(f"[MQTT] Subscriber started on {broker}:{port}")
    except Exception as e:
        print(f"[MQTT] Could not connect: {e} — running without MQTT")