import serial
import time
import threading
from database import get_session, Settings

def open_door():
    session = get_session()
    try:
        settings = session.query(Settings).first()
        if not settings or not settings.door_com_port:
            return
        com_port = settings.door_com_port.strip()
    finally:
        session.close()
        
    if not com_port:
        return
        
    def door_worker():
        try:
            # Try to connect to the COM port
            ser = serial.Serial(com_port, 9600, timeout=1)
            
            # For generic Arduino setup, sending '1' to open
            ser.write(b'1')
            
            # Alternatively, if using an LCUS-1 USB Relay, it needs specific hex codes:
            # Turn ON Relay: A0 01 01 A2
            ser.write(b'\xA0\x01\x01\xA2')
            
            # Wait 3 seconds to keep door open
            time.sleep(3)
            
            # Turn OFF Relay (LCUS-1)
            ser.write(b'\xA0\x01\x00\xA1')
            
            # Generic Arduino OFF
            ser.write(b'0')
            
            ser.close()
        except Exception as e:
            print(f"Failed to open door on {com_port}: {e}")
            
    # Run in thread so GUI doesn't freeze
    thread = threading.Thread(target=door_worker, daemon=True)
    thread.start()
