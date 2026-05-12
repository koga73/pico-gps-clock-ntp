import json

# region SETTINGS
def settings_write(format_24hr, timezone, daylight_savings):
    settings = {
        "format_24hr": format_24hr,
        "tz":timezone,
        "dst":daylight_savings
    }
    print("\n", settings)
    with open("settings.txt", "w") as f:
        f.write(json.dumps(settings))

def settings_read():
    try:
        with open("settings.txt", "r") as f:
            data = f.read()
        print("settings.txt", data)
        settings = json.loads(data)
        return settings["format_24hr"], settings["tz"], settings["dst"]
    except OSError as err:
        print('not found "settings.txt"')
        return None, None, None
# endregion

# region WIFI
def wifi_write(ssid, password):
    wifi = {
        "ssid": ssid,
        "password": password
    }
    print("\n", wifi)
    with open("wifi.txt", "w") as f:
        f.write(json.dumps(wifi))

def wifi_read():
    try:
        with open("wifi.txt", "r") as f:
            data = f.read()
        print("wifi.txt", data)
        wifi = json.loads(data)
        return wifi["ssid"], wifi["password"]
    except OSError as err:
        print('not found "wifi.txt"')
        return None, None
# endregion