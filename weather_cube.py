#!/usr/bin/env python3
from yaml import load, Loader
from json import loads
from pprint import pprint
from paho.mqtt import client as mqtt_client
from datetime import datetime
from flask import Flask
from threading import Event
from multiprocessing import Process, Value, Array
import ctypes

import colorsys
import math
import requests
import sys

def toHex(num):
    return hex(int(num)).split('x')[1].zfill(2).upper()

def toDec(num):
    return int(num, 16)

## MQTT HELPERS START
# Handle connecting to mqtt
def connect_mqtt(mqtt_config):
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            pprint(userdata)
        else:
            print(f'Failed to connect, return code {rc}', flush=True)

    client = mqtt_client.Client(mqtt_config['client_id'])
    client.username_pw_set(mqtt_config['username'], mqtt_config['password'])
    client.on_connect = on_connect
    client.connect(mqtt_config['broker'], mqtt_config['port'])
    return client

# Subscribe to a topic
def subscribe(client, topic, on_message):
    print(f'Subscribing to {topic}', flush=True)

    client.subscribe(topic)
    client.on_message = on_message

def makeColorTuple(color):
    h = color.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def hsv2rgb(h,s,v):
    r,g,b = tuple(toHex(round(i * 255)) for i in colorsys.hsv_to_rgb(h,s,v))
    return f"#{r}{g}{b}"

def send_power(client, topic, state):
    client.publish(f'{topic}/cmnd/Power', state)

def send_colors(client, topic, colors):
    color_codes = [f'{r},{g},{b}' for r,g,b in colors]
    client.publish(f'{topic}/cmnd/Palette', ' '.join(color_codes))
    client.publish(f'{topic}/cmnd/Scheme', '2')

def handle_color_settings(client, topic, colors):
    temp, special_condition = colors

    if special_condition:
        c1 = makeColorTuple(temp)
        c2 = makeColorTuple(special_condition)
        send_colors(client, topic, [c1, c2])
    else:
        send_colors(client, topic, [makeColorTuple(temp)])

## END MQTT LOGIC

## WEATHER SPECIFIC LOGIC

def get_current_weather(weather_config):
    resp = requests.get(f"https://api.openweathermap.org/data/2.5/weather?lat={weather_config['lat']}&lon={weather_config['lon']}&appid={weather_config['api_key']}")
    return resp.json()

code_main_color = {
    'Ash': '#FF0099',
    'Drizzle': '#FF0099',
    'Dust': '#FF0099',
    'Haze': '#FF0099',
    'Mist': '#FF0099',
    'Rain': '#FF0099',
    'Sand': '#FF0099',
    'Smoke': '#FF0099',
    'Snow': '#FF0099',
    'Squall': '#FF0099',
    'Thunderstorm': '#FF0099',
    'Tornado': '#FF0099',
}

def code_to_condition(code):
    if code == -1:
        return 'Clear'
    return list(code_main_color.keys())[code]

def condition_to_code(condition):
    try:
        return list(code_main_color.keys()).index(condition)
    except ValueError:
        return -1

def get_condition(weather):
    return weather['weather'][0]['main']

def get_temp(weather):
    return weather['main']['temp']

COLD = 273 # K
HOT = 308
# Assume temperature in kelvin
def characterize_weather(weather):
    colors = []
    condition_code = get_condition(weather)
    temp = get_temp(weather)

    if temp <= COLD:
        colors.append(hsv2rgb(0.6, 1, 1))
    elif temp >= HOT:
        colors.append(hsv2rgb(0, 1, 1))
    else:
        hue = 0.6 - (((temp - COLD) / (HOT - COLD)) * 0.6)
        colors.append(hsv2rgb(hue, 1, 1))

    condition_color = code_main_color.get(condition_code)
    colors.append(condition_color)

    return colors

## END WEATHER LOGIC

def cubeStateToStr(state):
    return {
        0: 'Idle',
        1: 'Running',
        2: 'Sleeping until morning...',
    }[state]

## ACTUAL SCRIPT START

# LOAD IN CONFIG
REFRESH_SPEED = 300
SAW_RESTART_SIGNAL = Event()
if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(f'Usage {sys.argv[0]} <config filename>', flush=True)
        sys.exit(1)

    with open(sys.argv[1], 'r') as configFile:
        config = load(configFile, Loader=Loader)

    if config is None:
        print('Failed to load config.yaml', flush=True)
        sys.exit(1);

    tempColor = Array(ctypes.c_uint32, [0, 0, 0], lock=False)
    cubeState = Value('i', 0, lock=False)
    conditionState = Value('i', -1, lock=False)
    tempValue = Value('d', 0.0, lock=False)
    updated = Value('d', datetime.now().timestamp(), lock=False)
    app = Flask(__name__)
    @app.route('/')
    def index():
        return f"""
<!DOCTYPE html>
<html>
  <head>
    <title>Weather Cube</title>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="30">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/water.css@2/out/water.css">

  </head>
  <body>
    <main>
        <h1>Weather Cube</h1>
        <table>
            <tbody>
                <tr>
                    <td>State</td>
                    <td>{cubeStateToStr(cubeState.value)}</td>
                </tr>
                <tr>
                    <td>Updated</td>
                    <td>{datetime.fromtimestamp(updated.value).isoformat()}</td>
                </tr>
                <tr>
                    <td>Temperature</td>
                    <td>{'{0:.2f}'.format(tempValue.value)}°C</td>
                </tr>
                <tr>
                    <td>Condition</td>
                    <td>{code_to_condition(conditionState.value)}</td>
                </tr>
                <tr>
                    <td>Color</td>
                    <td style="display: flex; gap: 10px; color: rgb({tempColor[0]}, {tempColor[1]}, {tempColor[2]})">{tempColor[:]}</td>
                </tr>
            </tbody>
        </table>
    </main>
  </body>
</html>
    """

    # Kick off the webhost
    webhost = Process(target=lambda: app.run(host="0.0.0.0"))
    webhost.start()

    def on_message(client, userdata, msg):
        payload = msg.payload.decode()
        if msg.topic == f"{config['mqtt']['topic']}/INFO3" and 'RestartReason' in loads(payload)['Info3']:
            SAW_RESTART_SIGNAL.set()
        print(f"Received `{payload}` from `{msg.topic}` topic", flush=True)

    # Configure MQTT
    client = connect_mqtt(config['mqtt'])
    subscribe(client, f"{config['mqtt']['topic']}/#", on_message)
    client.loop_start()

    # Begin looping through and checking for weather
    while True:
        SAW_RESTART_SIGNAL.clear()
        now = datetime.now()
        if now.hour < 9 or now.hour > 22:
            cubeState.value = 2
            updated.value = now.timestamp()
            print('sleeping until a more reasonable hour', flush=True)
            send_power(client, config['mqtt']['topic'], 'OFF')
            SAW_RESTART_SIGNAL.wait(REFRESH_SPEED)
        else:
            weather_now = get_current_weather(config['weather'])
            print('WEATHER UPDATE\n', flush=True)
            cubeState.value = 1
            updated.value = datetime.now().timestamp()
            conditionState.value = condition_to_code(get_condition(weather_now))
            tempValue.value = get_temp(weather_now) - 273.15
            pprint(weather_now)
            colors = characterize_weather(weather_now)

            if colors[0] is not None:
                rgb = makeColorTuple(colors[0])
                tempColor[0] = rgb[0]
                tempColor[1] = rgb[1]
                tempColor[2] = rgb[2]

            print(colors, flush=True)
            handle_color_settings(client, config['mqtt']['topic'], colors)
            SAW_RESTART_SIGNAL.wait(REFRESH_SPEED)

