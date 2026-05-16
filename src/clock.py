import time
import json

from lib.daylightsaving import StandardTimePolicy, DaylightSavingPolicy, DaylightSaving 

# Clock with microsecond precision, timezones and daylight saving time
class Clock:
    DEFAULT_FORMAT_24HR = False
    DEFAULT_TZ = -5	# EST
    DEFAULT_DST = "us"

    def __init__(self, format_24hr = None, tz = None, dst = None):
        self.time_us = 0
        self.last_time_set = 0

        self._ds = None
        
        self.init_localtime(format_24hr, tz, dst)
    
    # region DST
    def init_localtime(self, format_24hr = None, tz = None, dst = None):
        if (format_24hr == None):
            self.format_24hr = Clock.DEFAULT_FORMAT_24HR
        else:
            self.format_24hr = format_24hr
        
        if (tz == None):
            self.tz = Clock.DEFAULT_TZ
        else:
            self.tz = tz

        if (dst == None):
            self.dst = Clock.DEFAULT_DST
        else:
            self.dst = dst
        
        print("init_local", json.dumps({
            "format_24hr": format_24hr,
            "tz": tz,
            "dst": dst
        }))
        tz_minutes = self.tz * 60

        # US
        if (self.dst == "us"):
            # Daylight Saving starts on second Sunday of March at 2am
            # 0 = Northern hemisphere
            # 2 = Second week of the month
            # 3 = March
            # 6 = Sunday
            # 2 = 2AM
            # Time offset = 60 mins (GMT+1)
            dst_policy = DaylightSavingPolicy(0, 2, 3, 6, 2, tz_minutes + 60)

            # Daylight Saving ends on first Sunday of November at 2AM
            # 0 = Northern hemisphere
            # 1 = First week of the month
            # 11 = November
            # 6 = Sunday
            # 2 = 2AM
            # Time offset = 0 mins (GMT/UTC)
            std_policy = StandardTimePolicy(0, 1, 11, 6, 2, tz_minutes)

            self._ds = DaylightSaving(dst_policy, std_policy)

        # UK / EU   
        elif (self.dst == "uk"):
            # Daylight Saving starts on last Sunday of March at 1AM
            # 0 = Northern hemisphere
            # 0 = Last week of the month
            # 3 = March
            # 6 = Sunday
            # 1 = 1AM
            # Time offset = 60 mins (GMT+1)
            dst_policy = DaylightSavingPolicy(0, 0, 3, 6, 1, tz_minutes + 60)

            # Daylight Saving ends on last Sunday of October at 2AM
            # 0 = Northern hemisphere
            # 0 = Last week of the month
            # 10 = October
            # 6 = Sunday
            # 2 = 2AM
            # Time offset = 0 mins (GMT/UTC)
            std_policy = StandardTimePolicy(0, 0, 10, 6, 2, tz_minutes)

            self._ds = DaylightSaving(dst_policy, std_policy)
        
        # Australia
        elif (self.dst == "au"):
            # Daylight Saving starts on first Sunday of October at 2am
            # 1 = Southern hemisphere
            # 1 = First week of the month
            # 10 = October
            # 6 = Sunday
            # 2 = 2AM
            # Time offset = 60 mins (GMT+1)
            dst_policy = DaylightSavingPolicy(1, 1, 10, 6, 2, tz_minutes + 60)

            # Daylight Saving ends on first Sunday of April at 3AM
            # 1 = Southern hemisphere
            # 1 = First week of the month
            # 4 = April
            # 6 = Sunday
            # 3 = 3AM
            # Time offset = 0 mins (GMT/UTC)
            std_policy = StandardTimePolicy(1, 1, 4, 6, 3, tz_minutes)

            self._ds = DaylightSaving(dst_policy, std_policy)
        
        else:
            self._ds = None
    # endregion
    
    # region DATETIME
    # GET datetime UTC tuple where subseconds = microseconds
    # dt = (year, month, day, weekday, hours, minutes, seconds, subseconds)
    def get_datetime(self):
        if (self.last_time_set == 0):
            return (1970, 1, 1, 4, 0, 0, 0, 0)

        t = self.time_us
        delta = time.ticks_diff(time.ticks_us(), self.last_time_set)
        now = t + delta

        seconds = now // 1000000
        microseconds = now % 1000000
        year, month, mday, hour, minute, second, weekday, yearday = time.gmtime(seconds)
        return (year, month, mday, weekday, hour, minute, second, microseconds)

    # SET datetime UTC where subseconds = microseconds
    # dt = (year, month, day, weekday, hours, minutes, seconds, subseconds)
    def set_datetime(self, dt, offset = 0, set_at = None):
        # Convert datetime tuple to seconds since epoch (UNIX: January 1, 1970)
        seconds = time.mktime((dt[0], dt[1], dt[2], dt[4], dt[5], dt[6], dt[3], 0))
        
        # Assume the subseconds in tuple is in Microseconds
        self.time_us = seconds * 1000000 + dt[7] + offset
        self.last_time_set = set_at if (set_at != None) else time.ticks_us()
    # endregion

    # dt = (year, month, day, weekday, hours, minutes, seconds, subseconds)
    def localtime(self):
        if (self.last_time_set == 0):
            return (1970, 1, 1, 4, 0, 0, 0, 0)
        
        # Get current datetime in UTC as tuple with microsecond precision
        dt = self.get_datetime()

        # Convert datetime tuple to seconds since epoch (UNIX: January 1, 1970)
        seconds = time.mktime((dt[0], dt[1], dt[2], dt[4], dt[5], dt[6], dt[3], 0))
        if (self._ds != None):
            # Adjust seconds for timezone and daylight saving time
            seconds = self._ds.localtime(seconds)
        
        # Convert seconds back to datetime tuple with microsecond precision
        year, month, mday, hour, minute, second, weekday, yearday = time.gmtime(seconds)
        return (year, month, mday, weekday, hour, minute, second, dt[7])

    # GET time in seconds since epoch (UNIX: January 1, 1970)
    def time_seconds(self):
        if (self.last_time_set == 0):
            return 0

        t = self.time_us
        delta = time.ticks_diff(time.ticks_us(), self.last_time_set)
        now = t + delta
        return int(now // 1000000)
    # endregion
