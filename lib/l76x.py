# https://github.com/waveshare/L76X-GPS-Module/blob/master/python/L76X.py

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

    # $PMTK Commands are for MediaTek, but the L76X uses $PCAS commands
    # https://raw.githubusercontent.com/Seeed-Projects/Seeed_L76K-GNSS_for_XIAO/fb74b715224e0ac153c3884e578ee8e024ed8946/docs/Quectel_L76K_GNSS_Protocol_Specification_V1.1.pdf

    #Startup mode
    # SET_HOT_START       = '$PMTK101'
    # SET_WARM_START      = '$PMTK102'
    # SET_COLD_START      = '$PMTK103'
    # SET_FULL_COLD_START = '$PMTK104'

    #Standby mode -- Exit requires high level trigger
    # SET_PERPETUAL_STANDBY_MODE      = '$PMTK161'

    # SET_PERIODIC_MODE               = '$PMTK225'
    # SET_NORMAL_MODE                 = '$PMTK225,0'
    # SET_PERIODIC_BACKUP_MODE        = '$PMTK225,1,1000,2000'
    # SET_PERIODIC_STANDBY_MODE       = '$PMTK225,2,1000,2000'
    # SET_PERPETUAL_BACKUP_MODE       = '$PMTK225,4'
    # SET_ALWAYSLOCATE_STANDBY_MODE   = '$PMTK225,8'
    # SET_ALWAYSLOCATE_BACKUP_MODE    = '$PMTK225,9'

    #Set the message interval,100ms~10000ms
    SET_POS_FIX         = '$PCAS02'
    SET_POS_FIX_200MS   = '$PCAS02,200'
    SET_POS_FIX_500MS   = '$PCAS02,500'
    SET_POS_FIX_1S      = '$PCAS02,1000'

    #Switching time output
    # SET_SYNC_PPS_NMEA_OFF   = '$PMTK255,0'
    # SET_SYNC_PPS_NMEA_ON    = '$PMTK255,1'
    SET_PPS_OFF = '$PCAS07,0'
    SET_PPS_ON  = '$PCAS07,1'

    #To restore the system default setting
    # SET_REDUCTION               = '$PMTK314,-1'

    #Set NMEA sentence output frequencies 
    # GGA, GLL, GSA, GSV, RMC, VTG, ZDA, ANT
    SET_NMEA_OUTPUT = '$PCAS03,1,1,1,1,1,1,1,1,0,0,,,0,0'
    
    #Baud rate
    SET_NMEA_BAUDRATE          = '$PCAS01'
    SET_NMEA_BAUDRATE_115200   = '$PCAS01,5'
    SET_NMEA_BAUDRATE_57600    = '$PCAS01,4'
    SET_NMEA_BAUDRATE_38400    = '$PCAS01,3'
    SET_NMEA_BAUDRATE_19200    = '$PCAS01,2'
    SET_NMEA_BAUDRATE_9600     = '$PCAS01,1'
    SET_NMEA_BAUDRATE_4800     = '$PCAS01,0'

    # Navigation Mode
    # 1 = Portable/Pedestrian; 2 = Stationary; 3 = Vehicle/Automotive.
    SET_NAV_MODE_PORTABLE = '$PCAS11,1'
    SET_NAV_MODE_STATIONARY = '$PCAS11,2'
    SET_NAV_MODE_VEHICLE = '$PCAS11,3'

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

    # Clear the GPS UART buffer
    def L76X_Flush(self):
        raw_data = self.config.Uart_ReceiveAll()
        if raw_data is None:
            return False
        for b in raw_data:
            try: self.parser.update(chr(b))
            except: continue
    
    # Read from GPS UART, parse and update time
    def L76X_Receive(self):
        self.L76X_Flush()
        
        # Update time
        day, month, year = self.parser.date
        hours, minutes, seconds_raw = self.parser.timestamp
        
        s = str(seconds_raw).split(".")
        seconds = int(s[0])
        microseconds = int(s[1] if len(s) > 1 else "0")

        # Ensure timestamp has changed
        if (year + 2000, month, day, hours, minutes, seconds, microseconds * 1000000) == (self.Time_Year, self.Time_Month, self.Time_Day, self.Time_Hours, self.Time_Minutes, self.Time_Seconds, self.Time_Microseconds):
            return False
        
        self.Last_Updated = time.ticks_us()
        self.Time_Year = year + 2000 # GPS returns year as 2 digit format
        self.Time_Month = month
        self.Time_Day = day
        self.Time_Hours = hours
        self.Time_Minutes = minutes
        self.Time_Seconds = seconds
        self.Time_Microseconds = microseconds * 1000000
        self.Timestamp = self._timestamp(year, month, day, hours, minutes, seconds, microseconds)

        # Update coordinates
        self.Lat = self.parser.latitude
        self.Lon = self.parser.longitude
        
        # Update satellites
        self.Satellites = self.parser.satellites_in_use

        return True
    
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
