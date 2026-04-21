# ============================================================
#  AutoGrow - Smart Plant Cultivation System
#  Team 9: PlantIQ | KidBright32 V1.5i
# ============================================================

WIFI_SSID  = "Theewasu_2.4G"
WIFI_PASS  = "Theewasu123"
MQTT_USER  = "b6710545652"
MQTT_PASS  = "natcha.limsu@ku.th"
LATITUDE   = 13.6178
LONGITUDE  = 100.5370
INTERVAL   = 600

PUMP_SPEED = 50

# Imports 
from machine import Pin, ADC, I2C
from neopixel import NeoPixel
import dht
import network
import time
import ujson
from umqtt.robust import MQTTClient
import ikb

# ─── iKB-1 (pump) ────────────────────────────────────────
# scl=Pin(5), sda=Pin(4)
_i2c = I2C(scl=Pin(5), sda=Pin(4), freq=1000000)
ikb1 = ikb.IKB(_i2c)
_pump_running    = False
_pump_start_time = None
PUMP_DURATION    = 3

def pump_on(speed=PUMP_SPEED):
    global _pump_running, _pump_start_time
    if not _pump_running:
        ikb1.fd(speed)
        _pump_running    = True
        _pump_start_time = time.time()
        print("Pump ON (speed={}, will stop in {}s)".format(speed, PUMP_DURATION))

def pump_off():
    global _pump_running, _pump_start_time
    if _pump_running:
        ikb1.stop()
        _pump_running    = False
        _pump_start_time = None
        print("Pump OFF")

def pump_tick():
    if _pump_running and _pump_start_time is not None:
        if time.time() - _pump_start_time >= PUMP_DURATION:
            print("Pump auto-stop after {}s".format(PUMP_DURATION))
            pump_off()
            
# ─── MQTT config ────────────────────────────────────────────
MQTT_BROKER    = "iot.cpe.ku.ac.th"
MQTT_TOPIC     = MQTT_USER + "/autogrow/sensors"
MQTT_CMD_TOPIC = MQTT_USER + "/autogrow/cmd"

# ─── Pin setup ──────────────────────────────────────────────
dht1 = dht.DHT11(Pin(27, Pin.IN, Pin.PULL_UP))
dht2 = dht.DHT11(Pin(33, Pin.IN, Pin.PULL_UP))
time.sleep(1)

vibration = Pin(32, Pin.IN, Pin.PULL_UP)

soil_adc = ADC(Pin(35))
soil_adc.atten(ADC.ATTN_11DB)
soil_adc.width(ADC.WIDTH_12BIT)

ldr_adc = ADC(Pin(34))
ldr_adc.atten(ADC.ATTN_11DB)
ldr_adc.width(ADC.WIDTH_12BIT)

led_green = Pin(12, Pin.OUT, value=1)
led_red   = Pin(2,  Pin.OUT, value=1)

# ─── NeoPixel ───────────────────────────────────────────────
NEOPIXEL_PIN   = 26
NEOPIXEL_COUNT = 12
BRIGHTNESS     = 0.3

np = NeoPixel(Pin(NEOPIXEL_PIN), NEOPIXEL_COUNT)

STAGE_COLORS_RAW = {
    -1: (0,   0,   0  ),  # Stage -1: Harvested -> OFF
     0: (0,   0,   0  ),  # Stage 0: Seedling   -> OFF
     1: (0,   0,   255),  # Stage 1: Blue
     2: (120, 0,   180)   # Stage 2: Blue+Red = Purple
}

def scale_color(r, g, b, brightness=BRIGHTNESS):
    return (int(r * brightness), int(g * brightness), int(b * brightness))

def set_neopixel(stage, effect="solid"):
    raw   = STAGE_COLORS_RAW.get(stage, (0, 0, 0))
    color = scale_color(*raw)

    if effect == "solid":
        for i in range(NEOPIXEL_COUNT):
            np[i] = color
        np.write()

    elif effect == "spin":
        for _ in range(2):
            for i in range(NEOPIXEL_COUNT):
                for j in range(NEOPIXEL_COUNT):
                    np[j] = color if j == i else (0, 0, 0)
                np.write()
                time.sleep_ms(60)
        for i in range(NEOPIXEL_COUNT):
            np[i] = color
        np.write()

    elif effect == "pulse":
        steps = 20
        for step in range(steps + 1):
            factor = (step / steps) * BRIGHTNESS
            c = scale_color(*raw, brightness=factor)
            for i in range(NEOPIXEL_COUNT):
                np[i] = c
            np.write()
            time.sleep_ms(30)

    print("NeoPixel → Stage {} | {} | RGB{}".format(stage, effect, color))
    

# ─── Growth stage config ─────────────────────────────────────
STAGE_NAMES = {
    -1: "Harvested",
     0: "Seedling",
     1: "Vegetative",
     2: "Bloom"
}

SOIL_THRESHOLD = {
    -1: 0,
     0: 40,
     1: 40,
     2: 45
}

LIGHT_HOURS = {
    -1: 0,
     0: 0,
     1: 14,
     2: 16
}

LIGHT_SPECTRUM = {
    -1: "OFF",
     0: "OFF",
     1: "Blue",
     2: "Blue+Red Purple"
}

current_stage    = 0
daily_light_secs = 0.0
last_light_check = time.time()
_last_reset_day  = None

def should_light_be_on():
    target_secs = LIGHT_HOURS.get(current_stage, 0) * 3600
    if target_secs == 0:
        return False
    return daily_light_secs < target_secs

def neopixel_off():
    for i in range(NEOPIXEL_COUNT):
        np[i] = (0, 0, 0)
    np.write()

def maybe_reset_daily(now_secs):
    global daily_light_secs, _last_reset_day
    today = now_secs // 86400
    if _last_reset_day is None:
        _last_reset_day = today
    if today != _last_reset_day:
        print("New day — resetting daily_light_secs ({:.1f}s → 0)".format(daily_light_secs))
        daily_light_secs = 0.0
        _last_reset_day  = today

# ─── LED helpers ─────────────────────────────────────────────
def led_ok():
    led_green.value(0); led_red.value(1)
    time.sleep_ms(500)
    led_green.value(1)

def led_error():
    led_green.value(1); led_red.value(0)
    time.sleep_ms(500)
    led_red.value(1)

def led_working():
    for _ in range(3):
        led_green.value(0); led_red.value(0)
        time.sleep_ms(150)
        led_green.value(1); led_red.value(1)
        time.sleep_ms(150)

# ─── Sensor readers ─────────────────────────────────────────
def read_dht(sensor, label="DHT"):
    try:
        sensor.measure()
        time.sleep_ms(100)
        return sensor.temperature(), sensor.humidity()
    except Exception as e:
        print("{} error:".format(label), e)
        return None, None

def read_soil():
    try:
        total = sum(soil_adc.read() for _ in range(10))
        raw   = total // 10
        pct   = round((1.0 - raw / 4095.0) * 100, 1)
        print("Soil raw ADC:", raw, "→", pct, "%")
        return pct
    except Exception as e:
        print("Soil error:", e)
        return None

def read_light():
    try:
        total = sum(ldr_adc.read() for _ in range(10))
        raw   = total // 10
        lux   = round((1.0 - raw / 4095.0) * 1000, 1)
        return lux
    except Exception as e:
        print("Light error:", e)
        return None

def read_vibration():
    try:
        return vibration.value() == 1
    except Exception as e:
        print("Vibration error:", e)
        return None

# ─── Health logic ────────────────────────────────────────────
def get_plant_health_score(soil, temp, humidity, light_lux):
    score  = 0
    detail = {}

    # Soil moisture (30 pts)
    threshold = SOIL_THRESHOLD.get(current_stage, 0)
    if soil is not None:
        if threshold == 0:
            score += 30
            detail["soil"] = "N/A (stage no water) {:.0f}%".format(soil)
        elif soil >= threshold:
            score += 30
            detail["soil"] = "OK ({:.0f}%)".format(soil)
        else:
            pts = max(0, int(30 * soil / threshold))
            score += pts
            detail["soil"] = "LOW ({:.0f}%, need {})".format(soil, threshold)
    else:
        score += 30
        detail["soil"] = "N/A"

    # Temperature (25 pts)
    if temp is not None:
        if 20 <= temp <= 30:
            score += 25
            detail["temp"] = "OK ({:.1f}°C)".format(temp)
        elif 15 <= temp < 20 or 30 < temp <= 35:
            score += 15
            detail["temp"] = "WARN ({:.1f}°C)".format(temp)
        else:
            score += 5
            detail["temp"] = "CRIT ({:.1f}°C)".format(temp)
    else:
        detail["temp"] = "N/A"

    # Light hours (25 pts)
    target_secs = LIGHT_HOURS.get(current_stage, 0) * 3600
    if target_secs > 0:
        ratio = min(1.0, daily_light_secs / target_secs)
        score += int(25 * ratio)
        hrs_done = round(daily_light_secs / 3600, 1)
        detail["light"] = "{}/{}h".format(hrs_done, LIGHT_HOURS.get(current_stage, 0))
    else:
        score += 25
        detail["light"] = "N/A"

    # Humidity (20 pts)
    if humidity is not None:
        score += 20 if 50 <= humidity <= 80 else 10
        detail["humidity"] = "{:.0f}%".format(humidity)
    else:
        score += 20
        detail["humidity"] = "N/A"

    return min(100, score), detail

def check_pump_health(vibrating, pump_commanded):
    if not pump_commanded:
        return "IDLE"
    if vibrating:
        return "OK"
    return "FAILURE - no vibration detected!"

# ─── WiFi ────────────────────────────────────────────────────
def wifi_connect():
    for attempt in range(5):
        try:
            wlan = network.WLAN(network.STA_IF)
            wlan.active(False); time.sleep(1)
            wlan.active(True);  time.sleep(1)
            if wlan.isconnected():
                print("WiFi OK:", wlan.ifconfig()[0])
                return wlan
            print("WiFi attempt {}...".format(attempt + 1))
            led_working()
            wlan.connect(WIFI_SSID, WIFI_PASS) if WIFI_PASS else wlan.connect(WIFI_SSID)
            for _ in range(40):
                if wlan.isconnected():
                    print("WiFi OK:", wlan.ifconfig()[0])
                    return wlan
                time.sleep(0.5)
        except Exception as e:
            print("WiFi error:", e)
            time.sleep(2)
    print("WiFi FAILED after 5 attempts")
    return None

# ─── MQTT callback ───────────────────────────────────────────
def on_mqtt_message(topic, msg):
    global current_stage
    try:
        data = ujson.loads(msg)
        new_stage = int(data.get("stage", current_stage))
        
        if new_stage in STAGE_NAMES and new_stage != current_stage:
            print("Stage update: {} → {}".format(
                STAGE_NAMES.get(current_stage, "Unknown"), STAGE_NAMES.get(new_stage, "Unknown")))
            current_stage = new_stage
            set_neopixel(current_stage, effect="pulse")
        else:
            print("Stage unchanged or out of range:", new_stage)
    except Exception as e:
        print("CMD parse error:", e)

# ─── MQTT persistent ─────────────────────────────────────────
_mqtt_client = None

def mqtt_connect_persistent():
    global _mqtt_client
    try:
        client = MQTTClient(
            "autogrow_" + MQTT_USER,
            MQTT_BROKER,
            port=1883,
            user=MQTT_USER,
            password=MQTT_PASS,
            keepalive=120
        )
        client.set_callback(on_mqtt_message)
        client.connect(clean_session=True)
        client.subscribe(MQTT_CMD_TOPIC)
        print("MQTT OK — subscribed to:", MQTT_CMD_TOPIC)
        _mqtt_client = client
        return client
    except Exception as e:
        print("MQTT FAILED:", e)
        _mqtt_client = None
        return None

def mqtt_check_messages(client):
    try:
        client.check_msg()
    except Exception as e:
        print("MQTT check_msg error:", e)
        return False
    return True

def mqtt_ensure_connected(client):
    if client is None:
        return mqtt_connect_persistent()
    try:
        client.ping()
        return client
    except Exception as e:
        print("MQTT ping failed, reconnecting:", e)
        try:
            client.disconnect()
        except:
            pass
        return mqtt_connect_persistent()

# ─── Main publish + actuator control ────────────────────────
def publish_once(client):
    global daily_light_secs, last_light_check

    temp1, humidity1 = read_dht(dht1, "DHT1")
    temp2, humidity2 = read_dht(dht2, "DHT2")
    if humidity1 is not None and humidity2 is not None:
        humidity = round((humidity1 + humidity2) / 2, 1)
    else:
        humidity = humidity1 or humidity2
    soil   = read_soil()
    light  = read_light()
    is_vib = read_vibration()

    now     = time.time()
    elapsed = now - last_light_check
    last_light_check = now
    maybe_reset_daily(now)

    LUX_THRESHOLD = 50
    if light is not None and light >= LUX_THRESHOLD:
        daily_light_secs += elapsed

    
    should_pump = (
        soil is not None
        and SOIL_THRESHOLD.get(current_stage, 0) > 0
        and soil < SOIL_THRESHOLD.get(current_stage, 0)
    )

    if should_pump:
        pump_on()
    else:
        pump_off()

    pump_status  = check_pump_health(is_vib, should_pump)
    
    harvest_eta  = max(0, (2 - current_stage) * 7) if current_stage != -1 else 0
    
    health, hdet = get_plant_health_score(soil, temp1, humidity, light)

    if should_light_be_on():
        set_neopixel(current_stage, effect="solid")
    else:
        neopixel_off()

    print("─" * 40)
    print("Stage   : {} - {}".format(current_stage, STAGE_NAMES.get(current_stage, "Unknown")))
    print("Spectrum: {}".format(LIGHT_SPECTRUM.get(current_stage, "OFF")))
    print("Health  : {}/100 | {}".format(health, hdet))
    print("Temp1   : {} °C  Temp2: {} °C".format(temp1, temp2))
    print("Soil    : {} %   (threshold: {}%)".format(soil, SOIL_THRESHOLD.get(current_stage, 0)))
    print("Light   : {} lux".format(light))
    print("Pump    : {} | iKB running: {}".format(pump_status, _pump_running))

    payload = ujson.dumps({
        "lat"             : LATITUDE,
        "lon"             : LONGITUDE,
        "stage"           : current_stage,
        "stage_name"      : STAGE_NAMES.get(current_stage, "Unknown"),
        "spectrum"        : LIGHT_SPECTRUM.get(current_stage, "OFF") if should_light_be_on() else "OFF",
        "temp1"           : temp1,
        "temp2"           : temp2,
        "humidity"        : humidity,
        "soil_pct"        : soil,
        "light_lux"       : light,
        "vibration"       : is_vib,
        "pump_on"         : should_pump,
        "pump_status"     : pump_status,
        "light_hrs_today" : round(daily_light_secs / 3600, 2),
        "harvest_eta_days": harvest_eta,
        "health_score"    : health,
    })

    try:
        client.publish(MQTT_TOPIC, payload)
        print("Published → {}".format(MQTT_TOPIC))
        led_ok()
        return True
    except Exception as e:
        print("Publish error:", e)
        led_error()
        return False

def fetch_stage_from_backend():
    try:
        import urequests
        r = urequests.get("http://192.168.1.167:8000/stage/")
        data = r.json()
        r.close()
        stage = int(data.get("stage", 0))
        print("Stage from backend:", stage)
        return stage
    except Exception as e:
        print("fetch_stage failed:", e)
        return 0
    
# ─── Boot ────────────────────────────────────────────────────
print("=" * 44)
print("  AutoGrow - PlantIQ Team 9")
print("  MQTT topic : " + MQTT_TOPIC)
print("  CMD topic  : " + MQTT_CMD_TOPIC)
print("  Interval   : {} min".format(INTERVAL // 60))

wlan = wifi_connect()
if wlan is None:
    print("FATAL: No WiFi — halting")
    led_error()
    raise SystemExit

current_stage = fetch_stage_from_backend()

set_neopixel(current_stage, effect="spin")
print("  Stage      : {} - {}".format(current_stage, STAGE_NAMES.get(current_stage, "Unknown")))
print("=" * 44)

mqtt = mqtt_connect_persistent()
if mqtt is None:
    print("FATAL: No MQTT — halting")
    led_error()
    raise SystemExit

set_neopixel(current_stage, effect="spin")

# ─── Main loop ───────────────────────────────────────────────
reading_count = 0
last_publish  = time.time() - INTERVAL
_last_ping    = time.time()
_light_on     = None

while True:
    now = time.time()
    
    if not wlan.isconnected():
        print("WiFi lost! Trying to reconnect...")
        wlan = wifi_connect()
        if wlan is not None:
            mqtt = mqtt_connect_persistent()

    mqtt = mqtt_ensure_connected(mqtt)
    mqtt_check_messages(mqtt)
    pump_tick()

    if now - _last_ping >= 30:
        try:
            mqtt.ping()
            _last_ping = now
        except:
            pass

    want_on = should_light_be_on()
    if want_on != _light_on:
        _light_on = want_on
        if want_on:
            set_neopixel(current_stage, effect="solid")
        else:
            neopixel_off()

    if now - last_publish >= INTERVAL:
        reading_count += 1
        print("\nReading #{}".format(reading_count))
        mqtt  = mqtt_ensure_connected(mqtt)
        ok    = publish_once(mqtt)
        last_publish = time.time()
        print("Status:", "OK" if ok else "FAILED")

    time.sleep_ms(500)
