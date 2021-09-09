# Notes

## Board Info:

```
Chip is ESP8266EX
Features: WiFi
Crystal is 26MHz
MAC: 84:0d:8e:ab:b3:97
```

## Troubleshooting
Attempted to boot simple logic onto the board but to no avail. I could
get the led blink logic to work but trying to upgrade to a wifi server
caused the board to stop responding and resets didn't help.

For flashmode connect pin d3 to gnd and hold the reset button until
the flashing logic says "Connecting..."

To attempt to flash the board.
1. Disconnect it
2. When a new serial port is assigned, place the board in flash mode hold reset
3. upload the code and release reset

## End of Day
I was able to get someone's code loaded on it via the Arduino IDE that started a server and blinks the onboard led.

## Update 9/8

Installed Tasmota firmware on the D1 mini and set up MQTT with homeassistant.
Now everything about controlling the hardware is handled for me and I can focus on the weather portion of the code.

