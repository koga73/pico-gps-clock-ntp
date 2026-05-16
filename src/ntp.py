import asyncio
import socket
import ustruct
import errno
import time

# NTP timestamp starts Jan 1, 1900. Unix epoch starts Jan 1, 1970
# Difference is 2,208,988,800 seconds
_EPOCH_OFFSET = 2208988800

_PRECISION_MILLISECOND = -10 # 2 ^ -10 = ~1 millisecond: Standard precision for a microcontroller
_PRECISION_MICROSECOND = -20 # 2 ^ -20 = ~1 microsecond

POLL_INTERVAL = 6 # 2 ^ 6 = 64 seconds: Standard starting default interval for most Linux systems
PRECISION = _PRECISION_MICROSECOND

async def ntp_server(time_func = time.time):
    print("\nntp_server")

    transport = await start_udp(
        NtpProtocol,
        "0.0.0.0",
        123,
        time_func
    )
    return transport

async def start_udp(protocol, host, port, time_func):
    transport = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    transport.bind((host, port))
    transport.setblocking(False)
    p = protocol(transport)

    asyncio.create_task(_udp_loop(p, transport, time_func))

    return transport

async def _udp_loop(protocol, transport, time_func):
    while True:
        await asyncio.sleep_ms(50)
        
        try:
            data, addr = transport.recvfrom(48)
            recv_time = time_func()  # T2: capture receive timestamp immediately
            protocol.datagram_received(data, addr, time_func, recv_time)
        
        except OSError as e:
            # If transport is closed, break the loop
            if e.args[0] == errno.EBADF:
                break

class NtpProtocol():
    def __init__(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr, time_func, recv_time):
        # NTP packages are ALWAYS 48 bytes
        if (len(data) != 48):
            raise ValueError("invalid ntp packet length: " + str(len(data)))
        
        self.process_packet(data, addr, time_func, recv_time)
    
    def process_packet(self, data, addr, time_func, recv_time):
        print(f"\nntp request from {addr[0]}")

        # Extract Client Transmit Timestamp (bytes 40-47 in request)
        client_transmit_timestamp = data[40:48]

        # Mirror the version number from the client request (bits 5-3 of byte 0)
        client_vn = (data[0] >> 3) & 0x7

        # T2: Receive timestamp — captured at recvfrom, before any processing delay
        recv_seconds, recv_frac = recv_time
        recv_ntp_sec = recv_seconds + _EPOCH_OFFSET
        # Convert fractional microseconds to NTP fraction (2^32 / 1_000_000 ≈ 4294.967)
        recv_ntp_frac = recv_frac * 4295

        # Construct NTP Response Packet (48 bytes)
        response = bytearray(48)
        response[0] = (client_vn << 3) | 0x04   # LI=0 (no warning), VN=mirrored from client, Mode=4 (server)
        response[1] = 1                         # Stratum 1 (Primary reference)
        response[2] = POLL_INTERVAL             # Poll interval
        response[3] = PRECISION & 0xFF          # Precision encoded to fit in a byte

        # Reference ID
        response[12:16] = b'GPSD'

        # Reference Timestamp (last time synced, approximation: same as receive)
        response[16:20] = ustruct.pack("!I", recv_ntp_sec)
        response[20:24] = ustruct.pack("!I", recv_ntp_frac)
        
        # Origin Timestamp (echo client transmit)
        response[24:32] = client_transmit_timestamp

        # Receive Timestamp (T2: when packet arrived at server)
        response[32:36] = ustruct.pack("!I", recv_ntp_sec)
        response[36:40] = ustruct.pack("!I", recv_ntp_frac)

        # T3: Transmit timestamp — captured just before sending to exclude server processing time
        xmit_seconds, xmit_frac = time_func()
        xmit_ntp_sec = xmit_seconds + _EPOCH_OFFSET
        xmit_ntp_frac = xmit_frac * 4295

        # Transmit Timestamp (T3: when packet leaves server)
        response[40:44] = ustruct.pack("!I", xmit_ntp_sec)
        response[44:48] = ustruct.pack("!I", xmit_ntp_frac)

        # Send packet back to client
        self.transport.sendto(response, addr)
