import asyncio
import machine
import re

from src.filesystem import boot_write, wifi_write, settings_write

# region HTTP_STATUS
STATUS_OK = "HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n"
STATUS_BAD_REQUEST = """HTTP/1.1 400 Bad Request
Content-Type: text/plain
\r\n
"Bad Request"
"""
STATUS_NOT_FOUND = """HTTP/1.1 404 Not Found
Content-Type: text/plain
\r\n
"Not Found"
"""
# endregion

# region WEB_SERVER
# Handle incoming HTTP requests and send to the appropriate handler
async def web_server(request_handler):
    print("\nweb_server")

    server = await asyncio.start_server(
        lambda r, w: handle_client(r, w, request_handler),
        "0.0.0.0",
        80
    )
    return server

async def handle_client(reader, writer, request_handler):
    request = await reader.read(1024)
    print("\nhttp request:\n" + str(request))

    response, reset = await request_handler(request)
    
    writer.write(response.encode())
    await writer.drain()
    writer.close()
    await writer.wait_closed()

    # Reboot
    # TODO: Move reboot to reference in main
    if (reset == True):
        await asyncio.sleep_ms(1000)
        print("Rebooting...")
        machine.soft_reset()
#endregion

# region ROUTES_GATEWAY
async def handle_request_gateway(request, template_data):
    path = _get_path(request)

    # GET /
    if (path == "/"):
        title = template_data["title"]
        networks = template_data["networks"]
        options = "\n".join([f'<option value="{n["ssid"]}">{n["ssid"]}</option>' for n in networks])
        
        with open("static/gateway/index.html", "r") as f:
            html = f.read()
        html = html.replace("{TITLE}", title)
        html = html.replace("{WIFI_OPTIONS}", options)
        html = html.replace("{IP_ADDRESS}", template_data["ip"])

        response = STATUS_OK
        response += html
        return response, False

    # POST /connect
    elif (path == "/connect"):
        # Parse params from body
        body = _get_body(request)
        param_ssid = _get_param(body, "ssid")
        param_password = _get_param(body, "password")

        # Ensure required params are present
        if (param_ssid == None or param_password == None):
            response = STATUS_BAD_REQUEST
            response += "Missing required parameters"
            return response, False
        # Validate params
        if (not bool(re.search(r"^[a-zA-Z0-9_ \.\-]+$", str(param_ssid)))):
            response = STATUS_BAD_REQUEST
            response += "Invalid ssid"
            return response, False
        if (not len(str(param_password)) >= 8):
            response = STATUS_BAD_REQUEST
            response += "Invalid password"
            return response, False
        
        # Write wifi credentials to file
        wifi_write(param_ssid, param_password)
        # Set boot mode to default
        boot_write("default")

        # Return HTML
        title = template_data["title"]
        with open("static/gateway/connect.html", "r") as f:
            html = f.read()
        html = html.replace("{TITLE}", title)

        response = STATUS_OK
        response += html
        return response, True

    # Default
    else:
        response = STATUS_NOT_FOUND
        return response, False
# endregion

# region ROUTES_STATUS
async def handle_request_status(request, template_data):
    path = _get_path(request)

    # GET /
    if (path == "/"):
        title = template_data["title"]
        satellites = template_data["satellites"]
        timestamp = template_data["timestamp"]
        lat = template_data["lat"]
        lon = template_data["lon"]
        ip = template_data["ip"]
        
        with open("static/status/index.html", "r") as f:
            html = f.read()
        html = html.replace("{TITLE}", title)
        html = html.replace("{SATELLITES}", str(satellites))
        html = html.replace("{TIMESTAMP}", timestamp)
        html = html.replace("{LAT}", str(lat))
        html = html.replace("{LON}", str(lon))
        html = html.replace("{IP_ADDRESS}", ip)

        response = STATUS_OK
        response += html
        return response, False
    
    # POST /update
    elif (path == "/update"):
        # Parse params from body
        body = _get_body(request)
        param_format_24hr = _get_param(body, "format24hr")
        param_tz = _get_param(body, "tz")
        param_dst = _get_param(body, "dst")

        # Ensure required params are present
        if (param_tz == None or param_dst == None):
            response = STATUS_BAD_REQUEST
            response += "Missing required parameters"
            return response, False
        # Validate params
        if (not bool(re.search(r"^[0-9\-]+$", str(param_tz)))):
            response = STATUS_BAD_REQUEST
            response += "Invalid tz"
            return response, False
        if (not bool(re.search(r"^(none|us|uk|au)$", str(param_dst)))):
            response = STATUS_BAD_REQUEST
            response += "Invalid dst"
            return response, False
        
        # Write settings to file
        settings_write(param_format_24hr, int(param_tz), param_dst)

        # Return HTML
        title = template_data["title"]
        with open("static/status/update.html", "r") as f:
            html = f.read()
        html = html.replace("{TITLE}", title)

        response = STATUS_OK
        response += html
        return response, True
    
    # Default
    else:
        response = STATUS_NOT_FOUND
        return response, False
# endregion

# region HELPERS

# Get path from request
def _get_path(request):
    request_str = request.decode("utf-8")
    headers = request_str.split("\n")
    path = headers[0].split(" ")[1]
    return path

# Get body from request
def _get_body(request):
    requestStr = request.decode("utf-8")
    headers = requestStr.split("\n")
    body = headers[-1]
    return body

# Get param value from query string or body
def _get_param(str, param):
    params = (str.split("?")[1] if "?" in str else str).split("&")
    keyval = next(filter(lambda p: p.startswith(param), params), None)
    if (keyval == None):
        return None
    if ("=" in keyval):
        val = _url_decode(keyval.split("=")[1])
        if (val == "true"):
            return True
        elif (val == "false"):
            return False
        return val
    else:
        return True

# URL decode a string
def _url_decode(value):
    value = value.replace("+", " ")
    result = ""
    i = 0
    while i < len(value):
        if value[i] == "%" and i + 2 < len(value):
            result += chr(int(value[i+1:i+3], 16))
            i += 3
        else:
            result += value[i]
            i += 1
    return result

#endregion