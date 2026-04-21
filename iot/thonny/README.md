# Thonny / KidBright32 MicroPython

This folder contains the MicroPython code used on the KidBright32 board for AutoGrow.

## Files

- `kidbright32/main.py`: main runtime for sensor reading, actuator control, MQTT publish/subscribe, and LED/NeoPixel behavior.
- `kidbright32/config.example.py`: example values for Wi-Fi, MQTT, and account settings.

## What `main.py` Does

The current `kidbright32/main.py` performs these tasks:

1. Connects the board to Wi-Fi
2. Fetches the current growth stage from the backend
3. Connects to MQTT and subscribes to the command topic
4. Reads onboard sensors and computes a health score
5. Controls pump behavior and NeoPixel lighting based on the current stage
6. Publishes a combined sensor payload to the backend MQTT topic at a fixed interval

## Hardware / Sensors Used

- `DHT11` on pins `27` and `33`
- Soil moisture ADC on pin `35`
- LDR / light ADC on pin `34`
- Vibration sensor on pin `32`
- NeoPixel strip on pin `26`
- iKB motor driver over I2C on pins `SCL=5`, `SDA=4`

## MQTT Topics

- Publish topic: `MQTT_USER + "/autogrow/sensors"`
- Command topic: `MQTT_USER + "/autogrow/cmd"`

With the current code, this becomes:

- Publish topic: `b6710545652/autogrow/sensors`
- Command topic: `b6710545652/autogrow/cmd`

## Published Payload

Each publish includes these fields:

- `lat`
- `lon`
- `stage`
- `stage_name`
- `spectrum`
- `temp1`
- `temp2`
- `humidity`
- `soil_pct`
- `light_lux`
- `vibration`
- `pump_on`
- `pump_status`
- `light_hrs_today`
- `harvest_eta_days`
- `health_score`

## Configuration

The example configuration file is `kidbright32/config.example.py`.

It currently documents:

- `WIFI_SSID`
- `WIFI_PASS`
- `MQTT_BROKER`
- `MQTT_USER`
- `MQTT_PASS`
- `ACCOUNT`

Note: the current `kidbright32/main.py` still has connection values embedded directly in the script, so if you want runtime config to come from a separate file, the code should be refactored to import `config.py`.

## Running With Thonny

1. Open Thonny and connect to the KidBright32 / ESP32 board.
2. Upload `iot/thonny/kidbright32/main.py` to the board as `main.py`.
3. If you use external config, create a local `config.py` from `kidbright32/config.example.py`.
4. Reset the board.
5. Monitor the serial output for Wi-Fi, MQTT, sensor, and publish logs.

## Notes

- The publish interval in the current code is `600` seconds.
- The board also calls the backend stage endpoint directly to initialize the current stage.
- Do not commit real Wi-Fi or MQTT credentials.
