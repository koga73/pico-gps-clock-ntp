from machine import UART, Pin

class L76_Config(object):
    def __init__(self, Baudrate = 9600, tx_pin = 0, rx_pin = 1, force_pin = 14, standby_pin = 17):
        self.tx_pin = tx_pin
        self.rx_pin = rx_pin
        self.force_pin = force_pin
        self.standby_pin = standby_pin
        
        self.ser = UART(0, baudrate = Baudrate, tx = Pin(tx_pin) , rx = Pin(rx_pin))
        self.StandBy = Pin(standby_pin, Pin.OUT)
        self.Force = Pin(force_pin, Pin.IN)
        self.StandBy.value(0)
        self.Force.value(0)

    def Uart_SendByte(self, value): 
        self.ser.write(value) 

    def Uart_SendString(self, value): 
        self.ser.write(value)
    
    # Read all available bytes without blocking
    def Uart_ReceiveAll(self):
        ser = self.ser

        data = b""
        while ser.any() > 0:
            chunk = ser.read(ser.any())
            if chunk:
                data += chunk
        return data

    def Uart_Set_Baudrate(self, Baudrate):
        self.ser = UART(0,baudrate=Baudrate,tx=Pin(0),rx=Pin(1))