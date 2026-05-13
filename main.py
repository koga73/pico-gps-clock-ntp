import time
import json
import asyncio
import machine
from machine import Pin, RTC

from src.filesystem import wifi_read, settings_read
from src.display import Display
from src.gps import GPS
from src.wifi import wlan_reset, wlan_scan, wlan_ap, wlan_connect
from src.server import web_server, handle_request_gateway, handle_request_status

AP_SSID = "rpi_pico_2"
AP_PASS = None

SETTINGS_DEFAULTS = {
    "format_24hr": False,
    "tz": -4, # Eastern Time
    "dst": "us"
}
RTC_UPDATE_DELAY = 30000

# region GLOBALS
rtc = RTC()
display = Display(Pin(18), Pin(19), Pin("LED", Pin.OUT))
gps = GPS()

pps = Pin(16, Pin.IN)
pps_ready = False
pps_last_updated = time.ticks_ms()

format_24hr = SETTINGS_DEFAULTS["format_24hr"]
timezone = SETTINGS_DEFAULTS["tz"]
daylight_savings = SETTINGS_DEFAULTS["dst"]
# endregion

# region MODE_DEFAULT
async def mode_default():
    global format_24hr, timezone, daylight_savings
    
    print("\nmode_default")

    # See if we have settings saved
    print("\nsettings")
    f24hr, tz, dst = settings_read()
    if (f24hr != None):
        format_24hr = f24hr
    if (tz != None):
        timezone = tz
    if (dst != None):
        daylight_savings = dst

    print(json.dumps({
        "format_24hr": format_24hr,
        "timezone": timezone,
        "daylight_savings": daylight_savings
    }))
    
    # See if we should connect to wifi
    print("\nwifi")
    ssid, password = wifi_read()
    if (ssid != None):
        display.show("_-^-_-^-_")
        
        # Connect to wifi
        wlan = await wlan_connect(ssid, password)
        ip = wlan.ifconfig()[0]
        
        # Start web server
        await web_server(lambda request: _handle_request(request, ip))
        
        # Show IP address on display once
        await display.show_async(ip.replace(".", "_"), loops = 1)
    
    # Main loop for GPS and display
    await _loop_gps()

def _handle_request(request, ip):
    satellites = gps.get_satellites()
    timestamp = gps.get_timestamp()
    lat, lon = gps.get_coords()

    return handle_request_status(request, {
        "title": "Pico GPS Clock NTP",
        "satellites": satellites,
        "timestamp": timestamp,
        "lat": lat,
        "lon": lon,
        "ip": ip
    })
#endregion

# region LOOP_GPS
async def _loop_gps():
    global pps, pps_ready, pps_last_updated

    last_timestamp = ""

    pps.irq(trigger=Pin.IRQ_RISING, handler = _handle_pps)

    print("\nloop gps")
    display.show("_-^-_-^-_")

    while True:
        # Wait for PPS diff to be greater than RTC_UPDATE_DELAY so we don't update RTC too often
        if (pps_ready == False):
            delta_pps = time.ticks_diff(time.ticks_ms(), pps_last_updated)
            if (delta_pps > RTC_UPDATE_DELAY):
                pps_ready = True

        # Update display
        timestamp = gps.get_timestamp()
        if (timestamp != last_timestamp):
            # If we haven't set RTC yet, go ahead and use NEMA time 
            if (last_timestamp == ""):
                rtc.datetime(gps.get_datetime())

                print("\nnema update")
                print(f"time = {timestamp}")
                print(f"lat = {gps.get_lat()}, lon = {gps.get_lon()}")
                print(f"satellites = {gps.get_satellites()}")
            
            last_timestamp = timestamp
            
            _display_current_time()
        
        # Tick
        await asyncio.sleep_ms(1000)

# Set RTC to GPS time on PPS signal IRQ handler
def _handle_pps(pin):
    global pps_ready, pps_last_updated
    
    # Only update RTC if PPS is ready and delay has passed
    if (pps_ready == False):
        return
    pps_ready = False
    pps_last_updated = time.ticks_ms()

    # NEMA current time
    seconds = time.mktime(gps.get_datetime())
    # Plus difference between now and last NEMA update
    delta = time.ticks_diff(time.ticks_ms(), gps.get_last_updated())
    # Plus 1 second for this tick
    seconds_to_add = (delta // 1000) + 1
    # Set RTC
    rtc.datetime(time.localtime(seconds + seconds_to_add))

    print("\npps update")
    print(f"time = {gps.get_timestamp()}")
    print(f"lat = {gps.get_lat()}, lon = {gps.get_lon()}")
    print(f"satellites = {gps.get_satellites()}")

def _display_current_time():
    now = rtc.datetime()
    hours = now[4]
    minutes = now[5]
    seconds = now[6]
    
    # Format time based on settings
    if (timezone != 0):
        hours = (hours + timezone) % 24

    if (daylight_savings == "none"):
        pass
    elif (daylight_savings == "us"):
        pass # TODO
    elif (daylight_savings == "uk"):
        pass # TODO
    elif (daylight_savings == "au"):
        pass # TODO

    if (not format_24hr):
        hours = hours % 12
        if (hours == 0):
            hours = 12

    hours_str = "{:02d}".format(hours)
    minutes_str = "{:02d}".format(minutes)
    seconds_str = "{:02d}".format(seconds)
    
    display.show(f'{hours_str}{minutes_str}', colon = True)
# endregion

# region MODE_AP
async def mode_ap():
    print("\nmode_ap")

    display.show("SCAN")
    networks = await wlan_scan()

    display.show("HOST")
    ap = await wlan_ap(AP_SSID, AP_PASS)
    ip = ap.ifconfig()[0]

    await web_server(lambda request: handle_request_gateway(request, {
        "title": "Connect to WiFi",
        "networks": networks,
        "ip": ip
    }))

    display.show(AP_SSID)
# endregion

# region MAIN
async def main():
    print("starting...")
    # Add delay to allow for stopping the program if needed
    await asyncio.sleep_ms(2000)

    # Start display loop
    asyncio.create_task(display.loop())
    display.show("----")

    # Reset wlan interfaces
    await wlan_reset()

    # Start gps loop
    asyncio.create_task(gps.loop())

    try:
        await mode_default()
    except RuntimeError as err:
        print(err)
    
    await _reboot()

async def _reboot():
    await asyncio.sleep_ms(1000)
    print("Rebooting...")
    display.show("    ")
    machine.soft_reset()
# endregion

try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("\nstopped by user")
    display.show("    ")
