from machine import Pin
import time

from l76_config import L76_Config 
import micropyGPS as Parser

Temp = '0123456789ABCDEF*'

class L76X(object):
    Last_Updated = 0

    Time_Year = 0
    Time_Month = 0
    Time_Day = 0
    Time_Hours = 0
    Time_Minutes = 0
    Time_Seconds = 0
    Time_Microseconds = 0
    Timestamp = "" # "0000-00-00 00:00:00.0" # Unix format

    Lon = 0.0
    Lat = 0.0
    
    Satellites = 0
    
    #Startup mode
    SET_HOT_START       = '$PMTK101'
    SET_WARM_START      = '$PMTK102'
    SET_COLD_START      = '$PMTK103'
    SET_FULL_COLD_START = '$PMTK104'

    #Standby mode -- Exit requires high level trigger
    SET_PERPETUAL_STANDBY_MODE      = '$PMTK161'

    SET_PERIODIC_MODE               = '$PMTK225'
    SET_NORMAL_MODE                 = '$PMTK225,0'
    SET_PERIODIC_BACKUP_MODE        = '$PMTK225,1,1000,2000'
    SET_PERIODIC_STANDBY_MODE       = '$PMTK225,2,1000,2000'
    SET_PERPETUAL_BACKUP_MODE       = '$PMTK225,4'
    SET_ALWAYSLOCATE_STANDBY_MODE   = '$PMTK225,8'
    SET_ALWAYSLOCATE_BACKUP_MODE    = '$PMTK225,9'

    #Set the message interval,100ms~10000ms
    SET_POS_FIX         = '$PMTK220'
    SET_POS_FIX_100MS   = '$PMTK220,100'
    SET_POS_FIX_200MS   = '$PMTK220,200'
    SET_POS_FIX_400MS   = '$PMTK220,400'
    SET_POS_FIX_800MS   = '$PMTK220,800'
    SET_POS_FIX_1S      = '$PMTK220,1000'
    SET_POS_FIX_2S      = '$PMTK220,2000'
    SET_POS_FIX_4S      = '$PMTK220,4000'
    SET_POS_FIX_8S      = '$PMTK220,8000'
    SET_POS_FIX_10S     = '$PMTK220,10000'

    #Switching time output
    SET_SYNC_PPS_NMEA_OFF   = '$PMTK255,0'
    SET_SYNC_PPS_NMEA_ON    = '$PMTK255,1'

    #To restore the system default setting
    SET_REDUCTION               = '$PMTK314,-1'

    #Set NMEA sentence output frequencies 
    SET_NMEA_OUTPUT = '$PMTK314,1,1,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0,1,0'
    #Baud rate
    SET_NMEA_BAUDRATE          = '$PMTK251'
    SET_NMEA_BAUDRATE_115200   = '$PMTK251,115200'
    SET_NMEA_BAUDRATE_57600    = '$PMTK251,57600'
    SET_NMEA_BAUDRATE_38400    = '$PMTK251,38400'
    SET_NMEA_BAUDRATE_19200    = '$PMTK251,19200'
    SET_NMEA_BAUDRATE_14400    = '$PMTK251,14400'
    SET_NMEA_BAUDRATE_9600     = '$PMTK251,9600'
    SET_NMEA_BAUDRATE_4800     = '$PMTK251,4800'

    def __init__(self):
        self.config = L76_Config(9600)
        self.parser = Parser.MicropyGPS()
    
    def L76X_Send_Command(self, data):
        Check = ord(data[1]) 
        for i in range(2, len(data)):
            Check = Check ^ ord(data[i])
        data = data + Temp[16]
        data = data + Temp[int(Check/16)]
        data = data + Temp[int(Check%16)]
        self.config.Uart_SendString(data)
        self.config.Uart_SendByte('\r')
        self.config.Uart_SendByte('\n')
        # print(data)
    
    # Read from GPS UART, parse and update time
    def L76X_Loop(self):
        raw_data = self.config.Uart_ReceiveAll()
        if raw_data is None:
            return
        for b in raw_data:
            try: self.parser.update(chr(b))
            except: continue
        
        # Update time
        day, month, year = self.parser.date
        hours, minutes, seconds_raw = self.parser.timestamp
        
        s = str(seconds_raw).split(".")
        seconds = int(s[0])
        microseconds = int(s[1] if len(s) > 1 else "0")

        # Ensure timestamp has changed
        if (year + 2000, month, day, hours, minutes, seconds, microseconds) == (self.Time_Year, self.Time_Month, self.Time_Day, self.Time_Hours, self.Time_Minutes, self.Time_Seconds, self.Time_Microseconds):
            return
        
        self.Last_Updated = time.ticks_ms()
        self.Time_Year = year + 2000 # GPS returns year as 2 digit format
        self.Time_Month = month
        self.Time_Day = day
        self.Time_Hours = hours
        self.Time_Minutes = minutes
        self.Time_Seconds = seconds
        self.Time_Microseconds = microseconds
        self.Timestamp = self._timestamp(year, month, day, hours, minutes, seconds, microseconds)

        # Update coordinates
        self.Lat = self.parser.latitude
        self.Lon = self.parser.longitude
        
        # Update satellites
        self.Satellites = self.parser.satellites_in_use
    
    def _timestamp(self, year, month, day, hours, minutes, seconds, microseconds = 0):
        # Ensure we have date
        if (year == 0 and month == 0 and day == 0):
            return ""
        
        # Pad with leading zero if needed
        year = "20{:02d}".format(year)
        month = "{:02d}".format(month)
        day = "{:02d}".format(day)
        hours = "{:02d}".format(hours)
        minutes = "{:02d}".format(minutes)
        seconds = "{:02d}".format(seconds)

        return f"{year}-{month}-{day} {hours}:{minutes}:{seconds}.{microseconds}"

    def L76X_Set_Baudrate(self, Baudrate):
        self.config.Uart_Set_Baudrate(Baudrate)

    def L76X_Exit_BackupMode(self):
        self.config.Force.value(1)
        time.sleep(1)
        self.config.Force.value(0)
        time.sleep(1)
        self.config.Force = Pin(self.config.force_pin, Pin.IN)
