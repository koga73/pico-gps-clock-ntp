import asyncio

from lib.l76x import L76X

_DELAY = 500

class GPS(object):
    # Constructor
    def __init__(self):
        self.gps = L76X()
        self.gps.L76X_Set_Baudrate(9600)

    # Scroll during loop
    async def loop(self):
        gps = self.gps

        # Increase baudrate
        gps.L76X_Send_Command(gps.SET_NMEA_BAUDRATE_115200)
        await asyncio.sleep_ms(2000)
        gps.L76X_Set_Baudrate(115200)
        
        # Timing
        gps.L76X_Send_Command(gps.SET_POS_FIX_1S)
        gps.L76X_Send_Command(gps.SET_SYNC_PPS_NMEA_ON)
        
        # Output format
        gps.L76X_Send_Command(gps.SET_NMEA_OUTPUT)
        gps.L76X_Exit_BackupMode()
    
        while True:
            gps.L76X_Gat_GNRMC()
            if(gps.Status == 1):
                print("gps has lock")
            else:
                print("gps no lock")
            
            print(f"Time = {gps.Time_H}:{gps.Time_M}:{gps.Time_S}")
            print(f"Lat = {gps.Lat}, Lon = {gps.Lon}")

            await asyncio.sleep_ms(_DELAY)
