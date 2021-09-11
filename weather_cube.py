from yaml import load, Loader
from pprint import pprint
from paho.mqtt import client as mqtt_client
from datetime import datetime

import colorsys
import math
import requests
import sys
import time

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
def subscribe(client, topic):
    print(f'Subscribing to {topic}', flush=True)
    def on_message(client, userdata, msg):
        print(f"Received `{msg.payload.decode()}` from `{msg.topic}` topic", flush=True)

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

def handle_color_settings(client, topic, colors, duration):
    temp, special_condition = colors

    if special_condition:
        c1 = makeColorTuple(temp)
        c2 = makeColorTuple(special_condition)
        send_colors(client, topic, [c1, c2])
    else:
        send_colors(client, topic, [makeColorTuple(temp)])

    time.sleep(duration)

## END MQTT LOGIC

## WEATHER SPECIFIC LOGIC

def get_current_weather(weather_config):
    resp = requests.get(f"https://api.openweathermap.org/data/2.5/weather?lat={weather_config['lat']}&lon={weather_config['lon']}&appid={weather_config['api_key']}")
    return resp.json()

code_main_color = {
    'Thunderstorm': '#FF0099',
    'Drizzle': '#FF0099',
    'Rain': '#FF0099',
    'Snow': '#FF0099',
    'Smoke': '#FF0099',
    'Haze': '#FF0099',
    'Dust': '#FF0099',
    'Sand': '#FF0099',
    'Ash': '#FF0099',
    'Squall': '#FF0099',
    'Tornado': '#FF0099',
}

COLD = 265 # K
HOT = 308
# Assume temperature in kelvin
def characterize_weather(weather):
    colors = []
    condition_code = weather['weather'][0]['main']
    temp = weather['main']['temp']

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

## ACTUAL SCRIPT START

# LOAD IN CONFIG
REFRESH_SPEED = 300
if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(f'Usage {sys.argv[0]} <config filename>', flush=True)
        sys.exit(1)

    with open(sys.argv[1], 'r') as configFile:
        config = load(configFile, Loader=Loader)

    if config is None:
        print('Failed to load config.yaml', flush=True)
        sys.exit(1);

    # Configure MQTT
    client = connect_mqtt(config['mqtt'])
    subscribe(client, f"{config['mqtt']['topic']}/#")
    client.loop_start()

    config

    # Begin looping through and checking for weather
    while True:
        now = datetime.now()
        if now.hour < 9 or now.hour > 22:
            print('sleeping until a more reasonable hour', flush=True)
            send_power(client, config['mqtt']['topic'], 'OFF')
            time.sleep(REFRESH_SPEED)
        else:
            weather_now = get_current_weather(config['weather'])
            print('WEATHER UPDATE\n', flush=True)
            colors = characterize_weather(weather_now)
            print(colors, flush=True)
            handle_color_settings(client, config['mqtt']['topic'], colors, REFRESH_SPEED)

