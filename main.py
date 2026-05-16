import time
import asyncio
import machine
from machine import Pin

from src.clock import Clock
from src.button import Button
from src.display import Display
from src.gps import GPS
from src.wifi import wlan_reset, wlan_scan, wlan_ap, wlan_connect
from src.server import web_server, handle_request_gateway, handle_request_status
from src.ntp import ntp_server
from src.filesystem import boot_read, wifi_read, settings_read

AP_SSID = "rpi_pico_2"
AP_PASS = None

DEFAULT_WIFI = {
    "ssid": None,
    "password": None
}

CLOCK_UPDATE_DELAY = 30 * 1000000  # 30 seconds in microseconds

# region GLOBALS
clock = Clock()
button = Button(22)
display = Display(Pin(18), Pin(19), Pin("LED", Pin.OUT))
gps = GPS()

pps = Pin(16, Pin.IN)
pps_ready = False
pps_last_updated = time.ticks_us()
# endregion

# region MODE_DEFAULT
async def mode_default():
    global format_24hr, timezone, daylight_savings
    
    print("\nmode_default")

    # Start gps loop
    asyncio.create_task(gps.loop())

    # See if we have settings saved
    print("\nsettings")
    f24hr, tz, dst = settings_read()
    clock.init_localtime(f24hr, tz, dst)
    
    # See if we should connect to wifi
    server = None
    transport = None
    
    print("\nwifi")
    ssid = DEFAULT_WIFI["ssid"]
    password = DEFAULT_WIFI["password"]
    file_ssid, file_password = wifi_read()
    if (file_ssid != None):
        ssid = file_ssid
    if (file_password != None):
        password = file_password

    if (ssid != None):
        display.show("_-^-_-^-_")
        
        # Connect to wifi
        wlan = await wlan_connect(ssid, password)
        ip = wlan.ifconfig()[0]
        
        # Start web server
        server = await web_server(lambda request: _handle_request(request, ip))
        
        # Start the ntp server
        transport = await ntp_server(clock.time_seconds)

        # Show IP address on display once
        await display.show_async(ip.replace(".", "_"), loops = 1)
    
    # Main loop for GPS and display
    await _loop_default()

    # Clean up
    if (server != None):
        server.close()
    if (transport != None):
        transport.close()

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

# region LOOP_DEFAULT
async def _loop_default():
    global pps, pps_ready, pps_last_updated

    pps.irq(trigger=Pin.IRQ_RISING, handler = _handle_pps)

    print("\nloop default")
    display.show("_-^-_-^-_")
    
    last_timestamp = ""

    while True:
        # If our check button function returns true, break
        if (button.loop_button(time.ticks_ms(), button.default_released, button.default_held)):
            break

        # Wait for PPS diff to be greater than CLOCK_UPDATE_DELAY so we don't update Clock too often
        if (pps_ready == False):
            delta_pps = time.ticks_diff(time.ticks_us(), pps_last_updated)
            
            if (delta_pps > CLOCK_UPDATE_DELAY):
                pps_ready = True

            # NEMA update if we have a timestamp and PPS is not ready yet
            if (last_timestamp == ""):
                timestamp = gps.get_timestamp()
                if (timestamp != ""):
                    last_timestamp = timestamp
                    
                    clock.set_datetime(gps.get_datetime())

                    print("\nnema update")
                    print(f"time = {timestamp}")
                    print(f"lat = {gps.get_lat()}, lon = {gps.get_lon()}")
                    print(f"satellites = {gps.get_satellites()}")

        # Tick
        await asyncio.sleep_ms(250)
# endregion

# region PPS
# Set Clock to GPS time on PPS signal IRQ handler
def _handle_pps(pin):
    global pps_ready, pps_last_updated
    
    # Only update Clock if PPS is ready and delay has passed
    if (pps_ready == True):
        pps_ready = False

        ticks_now = time.ticks_us()
        pps_last_updated = ticks_now
        
        # NEMA current time
        dt = gps.get_datetime()
        # Plus difference between now and last NEMA update
        delta = time.ticks_diff(ticks_now, gps.get_last_updated())
        # Plus 1 second for this tick
        offset = delta + 1000000
        # Set Clock time to GPS time plus delta
        clock.set_datetime(dt, offset, ticks_now)
        
        print("\npps update")
        print(f"time = {gps.get_timestamp()}")
        print(f"lat = {gps.get_lat()}, lon = {gps.get_lon()}")
        print(f"satellites = {gps.get_satellites()}")

        _display_current_time(False)
    else:
        _display_current_time(True)
# endregion

# region DISPLAY
def _display_current_time(colon = True):
    if (clock.last_time_set == 0):
        return

    now = clock.localtime()
    hours = now[4]
    minutes = now[5]
    seconds = now[6]

    if (not clock.format_24hr):
        hours = hours % 12
        if (hours == 0):
            hours = 12

    hours_str = "{:02d}".format(hours)
    minutes_str = "{:02d}".format(minutes)
    seconds_str = "{:02d}".format(seconds)
    
    display.show(f'{hours_str}{minutes_str}', colon = colon)
# endregion

# region MODE_AP
async def mode_ap():
    print("\nmode_ap")

    display.show("SCAN")
    networks = await wlan_scan()

    display.show("HOST")
    ap = await wlan_ap(AP_SSID, AP_PASS)
    ip = ap.ifconfig()[0]

    server = await web_server(lambda request: handle_request_gateway(request, {
        "title": "Connect to WiFi",
        "networks": networks,
        "ip": ip
    }))

    display.show(AP_SSID)

    # Main loop for AP
    await _loop_ap()

    server.close()
# endregion

# region LOOP_AP
async def _loop_ap():
    print("\nloop ap")

    while True:
        # If our check button function returns true, break
        if (button.loop_button(time.ticks_ms(), button.ap_released, button.ap_held)):
            break

        await asyncio.sleep_ms(250)
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

    try:
        mode = boot_read()
        if (mode == "ap"):
            await mode_ap()
        else:
            await mode_default()
    except RuntimeError as err:
        print(err)
    
    await _reboot()

async def _reboot():
    await asyncio.sleep_ms(1000)
    print("rebooting...")
    display.show("    ")
    machine.soft_reset()
# endregion

try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("\nstopped by user")
    display.show("    ")
