# Node-RED

This folder contains the Node-RED flow used to receive AutoGrow sensor payloads from MQTT and store them in the remote MySQL database.

## Files

- `flows/autogrow-flow.json`: Node-RED flow export for the AutoGrow pipeline.

## What This Flow Does

The flow in `flows/autogrow-flow.json` performs this pipeline:

1. Subscribes to the MQTT topic `b6710545652/autogrow/sensors`
2. Parses the incoming JSON payload
3. Builds an SQL `INSERT` statement for the `Autogrow` table
4. Writes the payload into MySQL on `iot.cpe.ku.ac.th`
5. Sends a copy of the parsed payload to a debug node in Node-RED

## Input Topic

- MQTT topic: `b6710545652/autogrow/sensors`

## Stored Table

- MySQL table: `Autogrow`

## Expected Payload Fields

The current flow expects a JSON payload with these fields:

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

## Import Steps

1. Open the Node-RED editor.
2. Click `Menu -> Import`.
3. Select `iot/node-red/flows/autogrow-flow.json`.
4. Reconfigure the MQTT broker and MySQL connection if needed.
5. Click `Deploy`.

## Notes

- The exported flow currently contains broker/database host metadata. Keep credentials in Node-RED credential storage or environment variables instead of committing secrets.
- The MySQL node writes raw AutoGrow sensor snapshots and does not perform aggregation by itself.
