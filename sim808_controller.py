"""
SIM808 Controller - Handles serial communication with SIM808 module via AT commands
"""
import serial
import threading
import time
import re
import logging

logger = logging.getLogger(__name__)


class SIM808Controller:
    """Controller for SIM808 module communication"""
    
    def __init__(self, port=None, baudrate=115200, timeout=1):
        """
        Initialize SIM808 controller
        
        Args:
            port (str): Serial port path (e.g., '/dev/ttyUSB0')
            baudrate (int): Serial baud rate (default 115200)
            timeout (float): Serial timeout in seconds
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial_conn = None
        self.is_connected = False
        self.monitor_thread = None
        self.monitoring = False
        self.status_callbacks = []
        self.current_call_status = None
        self.incoming_call_number = None
        
    def connect(self, port=None):
        """
        Connect to SIM808 module
        
        Args:
            port (str): Serial port path (overrides self.port if provided)
            
        Returns:
            bool: True if connection successful
        """
        if port:
            self.port = port
            
        if not self.port:
            logger.error("No serial port specified")
            return False
            
        try:
            self.serial_conn = serial.Serial(
                self.port,
                self.baudrate,
                timeout=self.timeout,
                write_timeout=self.timeout
            )
            time.sleep(0.1)  # Give serial port time to initialize
            
            # Test connection with AT command
            if self.send_command("AT", expected="OK"):
                self.is_connected = True
                # Enable caller ID presentation
                self.send_command("AT+CLIP=1")
                # Start monitoring thread
                self.start_monitoring()
                logger.info(f"Connected to SIM808 on {self.port}")
                return True
            else:
                self.serial_conn.close()
                self.serial_conn = None
                logger.error("SIM808 did not respond to AT command")
                return False
                
        except serial.SerialException as e:
            logger.error(f"Failed to connect to {self.port}: {e}")
            self.is_connected = False
            return False
    
    def disconnect(self):
        """Disconnect from SIM808 module"""
        self.stop_monitoring()
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
        self.serial_conn = None
        self.is_connected = False
        logger.info("Disconnected from SIM808")
    
    def send_command(self, command, expected=None, timeout=None):
        """
        Send AT command and wait for response
        
        Args:
            command (str): AT command to send (without \r\n)
            expected (str): Expected response substring (optional)
            timeout (float): Override default timeout
            
        Returns:
            str: Response string or None if failed
        """
        if not self.is_connected or not self.serial_conn:
            logger.error("Not connected to SIM808")
            return None
            
        try:
            # Clear input buffer
            self.serial_conn.reset_input_buffer()
            
            # Send command
            cmd_bytes = f"{command}\r\n".encode()
            self.serial_conn.write(cmd_bytes)
            logger.debug(f"Sent: {command}")
            
            # Read response
            read_timeout = timeout if timeout else self.timeout
            response = b""
            start_time = time.time()
            
            while time.time() - start_time < read_timeout:
                if self.serial_conn.in_waiting > 0:
                    response += self.serial_conn.read(self.serial_conn.in_waiting)
                    # Check if we have a complete response
                    if b"OK" in response or b"ERROR" in response:
                        break
                time.sleep(0.01)
            
            response_str = response.decode('utf-8', errors='ignore').strip()
            logger.debug(f"Received: {response_str}")
            
            if expected:
                if expected in response_str:
                    return response_str
                else:
                    logger.warning(f"Expected '{expected}' but got: {response_str}")
                    return None
            
            return response_str
            
        except Exception as e:
            logger.error(f"Error sending command '{command}': {e}")
            return None
    
    def dial(self, number):
        """
        Dial a phone number
        
        Args:
            number (str): Phone number to dial
            
        Returns:
            bool: True if dial command sent successfully
        """
        if not number:
            return False
            
        # Sanitize phone number (remove non-digit characters except +)
        number = re.sub(r'[^\d+]', '', number)
        
        command = f"ATD{number};"
        response = self.send_command(command)
        
        if response and "OK" in response:
            self.current_call_status = "dialing"
            return True
        return False
    
    def hangup(self):
        """
        Hang up active call
        
        Returns:
            bool: True if hangup command sent successfully
        """
        response = self.send_command("ATH")
        if response and "OK" in response:
            self.current_call_status = None
            self.incoming_call_number = None
            return True
        return False
    
    def answer(self):
        """
        Answer incoming call
        
        Returns:
            bool: True if answer command sent successfully
        """
        response = self.send_command("ATA")
        if response and "OK" in response:
            self.current_call_status = "active"
            return True
        return False
    
    def send_dtmf(self, digit):
        """
        Send DTMF tone
        
        Args:
            digit (str): DTMF digit (0-9, *, #, A-D)
            
        Returns:
            bool: True if DTMF command sent successfully
        """
        if not digit or len(digit) != 1:
            return False
            
        # Validate DTMF digit
        valid_digits = "0123456789*#ABCD"
        if digit.upper() not in valid_digits:
            return False
            
        command = f"AT+VTS={digit}"
        response = self.send_command(command)
        return response and "OK" in response
    
    def get_call_status(self):
        """
        Get current call status using AT+CLCC
        
        Returns:
            dict: Call status information or None
        """
        response = self.send_command("AT+CLCC")
        
        if not response:
            return None
            
        # Parse +CLCC response: +CLCC: <id>,<dir>,<stat>,<mode>,<mpty>[,<number>,<type>]
        # dir: 0=MO (Mobile Originated), 1=MT (Mobile Terminated)
        # stat: 0=active, 1=held, 2=dialing, 3=alerting, 4=incoming, 5=waiting
        clcc_match = re.search(r'\+CLCC:\s*(\d+),(\d+),(\d+),(\d+),(\d+)(?:,([^,]+),(\d+))?', response)
        
        if clcc_match:
            call_id, direction, status, mode, mpty = clcc_match.groups()[:5]
            number = clcc_match.group(6) if clcc_match.group(6) else None
            number_type = clcc_match.group(7) if clcc_match.group(7) else None
            
            status_map = {
                '0': 'active',
                '1': 'held',
                '2': 'dialing',
                '3': 'ringing',
                '4': 'incoming',
                '5': 'waiting'
            }
            
            direction_map = {
                '0': 'outgoing',
                '1': 'incoming'
            }
            
            return {
                'id': int(call_id),
                'direction': direction_map.get(direction, 'unknown'),
                'status': status_map.get(status, 'unknown'),
                'number': number,
                'mode': mode,
                'mpty': mpty == '1'
            }
        
        return None
    
    def register_status_callback(self, callback):
        """
        Register a callback function for status updates
        
        Args:
            callback (callable): Function to call with status updates
                                Should accept (event_type, data) parameters
        """
        if callback not in self.status_callbacks:
            self.status_callbacks.append(callback)
    
    def unregister_status_callback(self, callback):
        """Unregister a status callback"""
        if callback in self.status_callbacks:
            self.status_callbacks.remove(callback)
    
    def _notify_callbacks(self, event_type, data):
        """Notify all registered callbacks of a status event"""
        for callback in self.status_callbacks:
            try:
                callback(event_type, data)
            except Exception as e:
                logger.error(f"Error in status callback: {e}")
    
    def start_monitoring(self):
        """Start background thread to monitor serial port for unsolicited responses"""
        if self.monitoring:
            return
            
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop background monitoring thread"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
        self.monitor_thread = None
    
    def _monitor_loop(self):
        """Background loop to monitor serial port for unsolicited responses"""
        if not self.serial_conn:
            return
            
        buffer = b""
        
        while self.monitoring and self.is_connected:
            try:
                if self.serial_conn.in_waiting > 0:
                    buffer += self.serial_conn.read(self.serial_conn.in_waiting)
                    
                    # Process complete lines
                    while b'\r\n' in buffer:
                        line, buffer = buffer.split(b'\r\n', 1)
                        line_str = line.decode('utf-8', errors='ignore').strip()
                        
                        if line_str:
                            self._process_unsolicited(line_str)
                            
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                time.sleep(1)
    
    def _process_unsolicited(self, line):
        """
        Process unsolicited responses from SIM808
        
        Args:
            line (str): Response line from SIM808
        """
        logger.debug(f"Unsolicited: {line}")
        
        # Handle RING (incoming call)
        if line == "RING":
            self.current_call_status = "incoming"
            # Try to get caller ID from next line or use AT+CLCC
            self._notify_callbacks("incoming_call", {"number": self.incoming_call_number})
        
        # Handle +CLIP (Caller ID presentation)
        clip_match = re.search(r'\+CLIP:\s*([^,]+),(\d+)', line)
        if clip_match:
            number = clip_match.group(1).strip('"')
            self.incoming_call_number = number
            self.current_call_status = "incoming"
            self._notify_callbacks("incoming_call", {"number": number})
        
        # Handle NO CARRIER (call ended)
        if "NO CARRIER" in line:
            self.current_call_status = None
            self.incoming_call_number = None
            self._notify_callbacks("call_ended", {})
        
        # Handle BUSY
        if "BUSY" in line:
            self.current_call_status = None
            self._notify_callbacks("call_busy", {})
        
        # Handle call status updates (parse +CLCC response directly)
        clcc_match = re.search(r'\+CLCC:\s*(\d+),(\d+),(\d+),(\d+),(\d+)(?:,([^,]+),(\d+))?', line)
        if clcc_match:
            call_id, direction, status, mode, mpty = clcc_match.groups()[:5]
            number = clcc_match.group(6) if clcc_match.group(6) else None
            
            status_map = {
                '0': 'active',
                '1': 'held',
                '2': 'dialing',
                '3': 'ringing',
                '4': 'incoming',
                '5': 'waiting'
            }
            
            direction_map = {
                '0': 'outgoing',
                '1': 'incoming'
            }
            
            call_status = {
                'id': int(call_id),
                'direction': direction_map.get(direction, 'unknown'),
                'status': status_map.get(status, 'unknown'),
                'number': number,
                'mode': mode,
                'mpty': mpty == '1'
            }
            
            self.current_call_status = call_status['status']
            self._notify_callbacks("call_status", call_status)
