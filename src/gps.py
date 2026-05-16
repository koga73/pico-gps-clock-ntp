import asyncio

from lib.l76x import L76X

_DELAY = 300

class GPS(object):
    # Constructor
    def __init__(self):
        self.gps = L76X()
        self.gps.L76X_Set_Baudrate(9600)

    # Scroll during loop
    async def loop(self):
        gps = self.gps
        
        # Increase BAUD rate for faster NMEA parsing
        gps.L76X_Send_Command(gps.SET_NMEA_BAUDRATE_115200)
        await asyncio.sleep_ms(1000)
        gps.L76X_Set_Baudrate(115200)

        # Timing
        gps.L76X_Send_Command(gps.SET_POS_FIX_400MS)
        gps.L76X_Send_Command(gps.SET_SYNC_PPS_NMEA_ON)
        
        # Output format
        gps.L76X_Send_Command(gps.SET_NMEA_OUTPUT)
        gps.L76X_Exit_BackupMode()
    
        while True:
            gps.L76X_Loop()
            await asyncio.sleep_ms(_DELAY)

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
