# Weather Cube

Set an LED to specific colors and patterns based on the current weather. This script uses the
[openweathermap](https://openweathermap.org/) api to collect the current weather conditions and calculates a color based on the
current temperature. If there are rain-like conditions the like will also be told to alternate
between the temperature color and an out-of-specturm color indicating rain.

## Configuration

The `weather_cube.py` script expects a single command line argument indicating the path to a yaml
config file. The following can be used as a template:

```yaml
mqtt:
  username: 'some_homeassistant_user'
  password: '***'
  broker: '<MQTT Broker ip address>'
  port: 1883
  topic: 'weather_cube'
  client_id: 'weather_cube_controller'
weather:
  lat: '<Your Latitude>'
  lon: '<Your Longitude>'
  api_key: '<Your openweathermap.org API key>'
```

## Hardware and Setup

### Light
The light for this project simply an LED board connected directly into a small, wifi-capable
microcontroller.

- [WS2812B](https://cdn-shop.adafruit.com/datasheets/WS2812B.pdf) x 7
- [Wemos D1 Mini](https://www.wemos.cc/en/latest/d1/d1_mini.html)
- [Tasmota](https://tasmota.github.io/docs/About/) Image flashed on the D1 Mini

### MQTT Broker
I am running an [MQTT broker](https://en.wikipedia.org/wiki/MQTT#MQTT_broker) via an [add on](https://www.home-assistant.io/docs/mqtt/broker/) to [Home Assistant](https://www.home-assistant.io/getting-started/).
This entire set up is running on a separate raspberry pi currently, but in the future it might
be more resource conscious to run both the home assistant logic and the weather cube script
on the same machine.

### Dedicated Script-Running Raspberry Pi
Currently the `weather_cube.py` script is being run on a raspberry pi via a systemd service.
The `weather_cube.py` script will not work this way out of the box. The following steps were used to
get this whole thing working.

1. Install `python3`. (Sadly, my raspberry pi was too old to install `nix` on so I had to add a dependencies file)
2. Install dependencies via `pip3 install -r dependencies.txt`
3. Modify the script so that `systemd` will be willing to run it. `chmod u+x`
4. `systemd` will not run scripts from within a users `home` directory. For my installation I created symlinks to the
scripts

```bash
ln -s `pwd`/weather_cube.py /usr/local/bin
ln -s `pwd`/config.yaml /etc/weather_cube_config.yaml
```

Alternatively, you could install the script in `/opt` or something and avoid needing to do this altogether (I suspect, that claim is untested).

5. Create a service file in `/etc/systemd/system`. For example:

```
# weather-cube.service
[Unit]
Description=Weather Cube

[Service]
ExecStart=/usr/local/bin/weather_cube.py /etc/weather_cube_config.yaml
# Specifying StandardOutput may or may not be necessary.
# I did not see logs until I did this and added flush=True logic to the print statements
# in the script. It's possible this is unnecessary
StandardOutput=syslog+console

[Install]
WantedBy=multi-user.target
```

6. Enable the service with `systemctl enable weather-cube` (or whatever the service is titled)

You can confirm if the service is running with `systemctl status weather-cube` and you should be able to watch the output via `journalctl -u weather-cube`
