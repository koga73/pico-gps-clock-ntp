import os
import binascii
import network
import socket
import time
import json

from machine import Pin

led = Pin("LED", Pin.OUT)

PROJECT_NAME = "Connect to wifi"
AP_SSID = "rpi_pico_2_wh"
AP_PASS = None
MAX_NETWORKS = 10

STATUS_OK = "HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n"
STATUS_BAD_REQUEST = """HTTP/1.1 400 Bad Request
Content-Type: text/plain
\r\n
"Bad Request"
"""

# Scan for networks
def wlan_scan():
    print("\nwlan_scan")

    wlan = network.WLAN()
    wlan.active(True)
    networks = wlan.scan()
    wlan.active(False)

    networks = [{
        "ssid": n[0].decode(),
        "bssid": binascii.hexlify(n[1]).decode(),
        "channel": n[2],
        "rssi": n[3],
        "security": n[4],
        "hidden": n[5]
    } for n in networks]
    networks = [n for n in networks if n["ssid"] != ""] # Filter out networks with empty
    networks.sort(key=lambda n:n["rssi"], reverse=True)

    for n in networks:
        print(n)
    
    return networks

def wlan_ap(ssid, password = None, htmlDefault = None, htmlSubmit = None):
    print("\nwlan_ap")

    # Create access point
    ap = network.WLAN(network.AP_IF)
    if (password == None):
        ap.config(essid=ssid, security=0)
    else:
        ap.config(essid=ssid, password=password)
    ap.active(True)
    
    # Wait until active
    while(ap.active() == False):
        pass
    passStr = f"\"{str(password)}\"" if password != None else "None"
    print(f'{{"ssid":"{ssid}", "password":{passStr}, "gateway":"{ap.ifconfig()[0]}"}}')

    if (htmlDefault == None or htmlSubmit == None):
        return
    
    # Setup web server on gateway
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 80))
    s.listen(5)

    # Accept web connections
    while True:
        conn, addr = s.accept()
        print("client:", addr)
        
        request = conn.recv(1024)
        print("\nrequest:\n" + str(request))
        
        path = getPath(request)
        if (path.startswith("/connect")):
            body = getBody(request)
            paramSsid = getParam(body, "ssid")
            paramPassword = getParam(body, "password")
            if (paramSsid != None and paramPassword != None):
                wifi = {"ssid":paramSsid, "password":paramPassword}

                print("\n", wifi)
                with open("wifi.txt", "w") as f:
                    f.write(json.dumps(wifi))

                conn.send(STATUS_OK)
                conn.send(htmlSubmit)
            else:
                conn.send(STATUS_BAD_REQUEST)
        else:
            conn.send(htmlDefault)

        conn.close()

def wlan_connect(ssid, password):
    max_wait = 10

    html = """<!DOCTYPE html>
    <html>
        <head><title>Hello World!</title></head>
        <body>
            <h1>Hello World!</h1>
        </body>
    </html>
    """

    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ssid, password)

    # Wait for connect or fail
    while max_wait > 0:
        if (wlan.status() < 0 or wlan.status() >= 3):
            break
        max_wait -= 1
        print("waiting for connection...")
        time.sleep(1)

    # Handle connection error
    if (wlan.status() != 3):
        raise RuntimeError("network connection failed")
    else:
        print("connected!")
        status = wlan.ifconfig()
        print("ip:" + status[0])

    # Open socket 
    addr = socket.getaddrinfo("0.0.0.0", 80)[0][-1]
    s = socket.socket()
    s.bind(addr)
    s.listen(1)
    print("listening on", addr)

    # Listen for connections
    while True:
        try:
            cl, addr = s.accept()
            print("client connected from", addr)
            request = cl.recv(1024)
            print(request)
            
            cl.send(STATUS_OK)
            cl.send(html)
            cl.close()
        except OSError as err:
            cl.close()
            print("connection closed")

def getPath(request):
    requestStr = request.decode("utf-8")
    headers = requestStr.split("\n")
    path = headers[0].split(" ")[1]
    return path

def getBody(request):
    requestStr = request.decode("utf-8")
    headers = requestStr.split("\n")
    body = headers[-1]
    return body

def getParam(str, param):
    params = (str.split("?")[1] if "?" in str else str).split("&")
    keyval = next(filter(lambda p: p.startswith(param), params), None)
    if (keyval == None):
        return None
    if ("=" in keyval):
        return keyval.split("=")[1]
    else:
        return True

def mode_ap():
    networks = wlan_scan()

    apHtmlDefault = f"""<!DOCTYPE html>
    <html>
        <head>
            <title>{PROJECT_NAME}</title>
            <meta name="viewport" content="width=device-width,initial-scale=1" />
        </head>
        <body>
            <h1 style="margin-bottom:24px;">{PROJECT_NAME}</h1>

            <form action="/connect" method="POST">
                <div style="margin:16px 0;">
                    <label for="sltWifi">Network:</label>
                    <select id="sltWifi" name="ssid">
                        {[f'<option value="{n["ssid"]}">{n["ssid"]}</option>' for n in networks[:MAX_NETWORKS]]}
                    </select>
                </div>

                <div style="margin:16px 0;">
                    <label for="txtPass">Password:</label>
                    <input id="txtPass" type="text" name="password" minlength="8"/>
                </div>

                <button type="submit">Connect</button>
            </form>
        </body>
    </html>
    """

    apHtmlSubmit = f"""<!DOCTYPE html>
    <html>
        <head>
            <title>{PROJECT_NAME}</title>
            <meta name="viewport" content="width=device-width,initial-scale=1" />
        </head>
        <body>
            <h1 style="margin-bottom:24px;">{PROJECT_NAME}</h1>
            <p>Please wait while the device reboots</p>
        </body>
    </html>
    """

    wlan_ap(AP_SSID, AP_PASS, apHtmlDefault, apHtmlSubmit)

def main():
    # os.remove("wifi.txt")
    # return

    try:
        with open("wifi.txt", "r") as f:
            data = f.read()
        print(data)
        wifi = json.loads(data)
        wlan_connect(wifi["ssid"], wifi["password"])
    except OSError as err:
        print('not found "wifi.txt"')
        mode_ap()
    
main()