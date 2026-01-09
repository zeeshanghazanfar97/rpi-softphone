"""
Device Manager - Discovers and manages available serial ports and audio devices
"""
import glob
import os
import pyaudio


def discover_serial_ports():
    """
    Discover available /dev/ttyUSB* devices
    
    Returns:
        list: List of available serial port paths
    """
    ports = []
    # Check for common USB serial devices
    patterns = ['/dev/ttyUSB*', '/dev/ttyACM*', '/dev/ttyAMA*']
    
    for pattern in patterns:
        ports.extend(glob.glob(pattern))
    
    # Filter to only existing, readable devices
    valid_ports = []
    for port in ports:
        if os.path.exists(port) and os.access(port, os.R_OK | os.W_OK):
            valid_ports.append(port)
    
    return sorted(valid_ports)


def discover_audio_devices():
    """
    Discover available audio input and output devices using pyaudio
    
    Returns:
        dict: Dictionary with 'inputs' and 'outputs' lists, each containing
              device info dictionaries with 'index', 'name', and 'channels'
    """
    audio = pyaudio.PyAudio()
    devices = {'inputs': [], 'outputs': []}
    
    try:
        device_count = audio.get_device_count()
        
        for i in range(device_count):
            try:
                info = audio.get_device_info_by_index(i)
                device_info = {
                    'index': i,
                    'name': info.get('name', f'Device {i}'),
                    'channels': {
                        'input': info.get('maxInputChannels', 0),
                        'output': info.get('maxOutputChannels', 0)
                    },
                    'sample_rate': int(info.get('defaultSampleRate', 44100))
                }
                
                # Add to inputs if it has input channels
                if device_info['channels']['input'] > 0:
                    devices['inputs'].append(device_info)
                
                # Add to outputs if it has output channels
                if device_info['channels']['output'] > 0:
                    devices['outputs'].append(device_info)
                    
            except Exception as e:
                # Skip devices that can't be queried
                continue
                
    finally:
        audio.terminate()
    
    return devices


def validate_serial_port(port_path):
    """
    Validate that a serial port exists and is accessible
    
    Args:
        port_path (str): Path to serial port
        
    Returns:
        bool: True if port is valid and accessible
    """
    if not port_path:
        return False
    
    return os.path.exists(port_path) and os.access(port_path, os.R_OK | os.W_OK)


def get_audio_device_info(device_index):
    """
    Get detailed information about a specific audio device
    
    Args:
        device_index (int): Audio device index
        
    Returns:
        dict: Device information or None if device doesn't exist
    """
    audio = pyaudio.PyAudio()
    
    try:
        if device_index >= audio.get_device_count():
            return None
            
        info = audio.get_device_info_by_index(device_index)
        return {
            'index': device_index,
            'name': info.get('name', f'Device {device_index}'),
            'channels': {
                'input': info.get('maxInputChannels', 0),
                'output': info.get('maxOutputChannels', 0)
            },
            'sample_rate': int(info.get('defaultSampleRate', 44100)),
            'host_api': info.get('hostApi', 0)
        }
    finally:
        audio.terminate()
