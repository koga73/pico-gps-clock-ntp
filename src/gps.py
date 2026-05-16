import asyncio
import time
from machine import Pin

from lib.l76x import L76X

class GPS():
    # Constructor
    def __init__(self, pps_pin = 16):
        self.pps_pin = pps_pin

        self._pps_ready = False
        self._pps_tick = time.ticks_us()

    async def init(self):
        gps = L76X()
        gps.L76X_Set_Baudrate(9600)
        await asyncio.sleep_ms(1000)

        # Increase BAUD rate for faster NMEA parsing
        gps.L76X_Send_Command(gps.SET_NMEA_BAUDRATE_115200)
        await asyncio.sleep_ms(1000)
        gps.L76X_Set_Baudrate(115200)

        # Timing
        gps.L76X_Send_Command(gps.SET_POS_FIX_200MS)
        gps.L76X_Send_Command(gps.SET_PPS_ON)

        # Output format
        gps.L76X_Send_Command(gps.SET_NMEA_OUTPUT)
        gps.L76X_Send_Command(gps.SET_NAV_MODE_STATIONARY)
        gps.L76X_Exit_BackupMode()

        self.gps = gps

        pps = Pin(self.pps_pin, Pin.IN)
        pps.irq(trigger = Pin.IRQ_RISING, handler = self._handle_pps)

    # PPS signal IRQ handler
    def _handle_pps(self, _pin):
        # If we are already true then the last message was not processed - so clear the buffer
        if (self._pps_ready == True):
            self.gps.L76X_Flush()
        
        self._pps_ready = True
        self._pps_tick = time.ticks_us()
    
    # Call from main loop
    def try_receive(self):
        if (self._pps_ready == True):
            self._pps_ready = False
            self.gps.L76X_Receive()

    def get_last_pps_tick(self):
        return self._pps_tick

    def get_last_updated(self):
        return self.gps.Last_Updated
    
    def get_satellites(self):
        return self.gps.Satellites

    def get_datetime(self):
        gps = self.gps
        weekday = 0 # Not supported by GPS
        return (gps.Time_Year, gps.Time_Month, gps.Time_Day, weekday, gps.Time_Hours, gps.Time_Minutes, gps.Time_Seconds, gps.Time_Microseconds)

    def get_timestamp(self):
        return self.gps.Timestamp

    def get_coords(self):
        gps = self.gps
        return gps.Lat, gps.Lon

    def get_lat(self):
        return self.gps.Lat

    def get_lon(self):
        return self.gps.Lon
