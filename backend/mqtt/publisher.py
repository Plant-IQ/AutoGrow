import json
import os

import paho.mqtt.publish as publish
from dotenv import load_dotenv

load_dotenv()


def publish_light_color(plant_id: int, color_hex: str):
    """Publish desired light color for a plant to MQTT.

    Topic: autogrow/<plant_id>/light/set
    Payload: {"plant_id": <id>, "color": "#RRGGBB"}
    """
    broker = os.getenv("MQTT_BROKER")
    port = os.getenv("MQTT_PORT")
    if not broker or not port:
        # Running without MQTT configured; skip silently but log for debugging
        print("[MQTT] Skipping publish (MQTT_BROKER/MQTT_PORT not set).")
        return

    auth = None
    user = os.getenv("MQTT_USER")
    pwd = os.getenv("MQTT_PASS")
    if user and pwd:
        auth = {"username": user, "password": pwd}

    topic = f"autogrow/{plant_id}/light/set"
    payload = json.dumps({"plant_id": plant_id, "color": color_hex})
    try:
        publish.single(topic, payload, hostname=broker, port=int(port), auth=auth)
        print(f"[MQTT] Published light color {color_hex} to {topic}")
    except Exception as e:
        print(f"[MQTT] Failed to publish light color: {e}")

def publish_stage_update(plant_id: int, stage: int):
    broker = os.getenv("MQTT_BROKER")
    port = os.getenv("MQTT_PORT")
    if not broker or not port:
        print("[MQTT] Skipping publish (MQTT_BROKER/MQTT_PORT not set).")
        return

    user = os.getenv("MQTT_USER")
    pwd = os.getenv("MQTT_PASS")
    auth = {"username": user, "password": pwd} if user and pwd else None

    # ใช้ MQTT_USER นำหน้า topic ให้ตรงกับที่ ESP32 subscribe ไว้
    topic = f"{user}/autogrow/cmd"        # b6710545652/autogrow/cmd
    payload = json.dumps({"stage": stage})  # key เป็น "stage" ตรงกับ on_mqtt_message ใน ESP32
    try:
        publish.single(topic, payload, hostname=broker, port=int(port), auth=auth)
        print(f"[MQTT] Published stage={stage} → {topic}")
    except Exception as e:
        print(f"[MQTT] Failed to publish stage: {e}")
