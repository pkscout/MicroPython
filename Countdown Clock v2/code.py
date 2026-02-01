# SPDX-FileCopyrightText: 2022 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT
"""
CircuitPython Quad-Alphanumeric Display Countdown.

Requires a separate file named settings.toml on your CIRCUITPY drive, which
should contain:
CIRCUITPY_WIFI_SSID = "xxx"
CIRCUITPY_WIFI_PASSWORD = "xxx"
AIO_USERNAME = "xxx"
AIO_KEY = "xxx"

SWAP_DELAY = 10  #in seconds
SCROLL_SPEED = 30  #between 1 and 100
BRIGHTNESS = 80  #between 1 and 100

EVENT_YEAR = 2026
EVENT_MONTH = 5
EVENT_DAY = 26
EVENT_HOUR = 8 
EVENT_MINUTE = 0
EVENT_NAME = "EVENT NAME"  #must be no more than 4 characters
EVENT_MSG = "HAPPY EVENT NAME * "  #can be as long as you want
"""

import os
import time
import ssl
import wifi
import socketpool
import microcontroller
import board
import adafruit_requests
from adafruit_ht16k33.segments import Seg14x4
from adafruit_io.adafruit_io import IO_HTTP, AdafruitIO_RequestError  # pylint: disable=unused-import

EVENT_YEAR = os.getenv("EVENT_YEAR")
EVENT_MONTH = os.getenv("EVENT_MONTH")
EVENT_DAY = os.getenv("EVENT_DAY")
EVENT_HOUR = os.getenv("EVENT_HOUR")
EVENT_MINUTE = os.getenv("EVENT_MINUTE")
EVENT_NAME = os.getenv("EVENT_NAME")[0:4]
EVENT_MSG = os.getenv("EVENT_MSG")
SWAP_DELAY = os.getenv("SWAP_DELAY")
SCROLL_SPEED = os.getenv("SCROLL_SPEED")/100

i2c = board.STEMMA_I2C()
display = Seg14x4(i2c, address=(0x70, 0x71, 0x72))
display.brightness = os.getenv("BRIGHTNESS")/100


def reset_on_error(delay, error):
    """Resets the code after a specified delay, when encountering an error."""
    print("Error:\n", str(error))
    display.print("Error :(")
    print("Resetting microcontroller in %d seconds" % delay)
    time.sleep(delay)
    # microcontroller.reset()


try:
    wifi.radio.connect(os.getenv("CIRCUITPY_WIFI_SSID"),
                       os.getenv("CIRCUITPY_WIFI_PASSWORD"))
except Exception as e:  # pylint: disable=broad-except
    # any errors, reset MCU
    reset_on_error(10, e)

aio_username = os.getenv("AIO_USERNAME")
aio_key = os.getenv("AIO_KEY")

pool = socketpool.SocketPool(wifi.radio)
requests = adafruit_requests.Session(pool, ssl.create_default_context())
# Initialize an Adafruit IO HTTP API object
try:
    io = IO_HTTP(aio_username, aio_key, requests)
except Exception as e:  # pylint: disable=broad-except
    reset_on_error(10, e)
print("Connected to Adafruit IO")
display.print("% 12s" % "CONNECTED")

event_time = time.struct_time(
    (EVENT_YEAR, EVENT_MONTH, EVENT_DAY, EVENT_HOUR, EVENT_MINUTE, 0, -1, -1, False)
)
while True:
    try:
        now = io.receive_time()
        remaining = time.mktime(event_time) - time.mktime(now)
        # if it's the day of the event...
        if remaining < 0:
            # scroll the event message on a loop
            display.marquee(EVENT_MSG, SCROLL_SPEED, loop=True)
        if remaining >= 86400000:
            # if it's 1000 days or more the display can't show it correctly
            countdown_string = "% 8s" % "FUTURE"
        else:
            # calculate the seconds remaining
            secs_remaining = remaining % 60
            remaining //= 60
            secs_string = "% 3sS" % str(secs_remaining)
            # calculate the minutes remaining
            mins_remaining = remaining % 60
            remaining //= 60
            mins_string = "% 3sM" % str(mins_remaining)
            # calculate the hours remaining
            hours_remaining = remaining % 24
            remaining //= 24
            hours_string = "% 3sH" % str(hours_remaining)
            # calculate the days remaining
            days_remaining = remaining
            days_string = "% 3sD" % str(days_remaining)
            # pack the calculated times into a string to show
            countdown_string = "%s%s" % (days_string, hours_string)
        # show the event name then the countdown once
        display.print("% 4s%s" % (EVENT_NAME, countdown_string))
    except Exception as e:  # pylint: disable=broad-except
        # any errors, reset MCU
        reset_on_error(10, e)
