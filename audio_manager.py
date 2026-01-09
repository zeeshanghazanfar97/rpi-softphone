"""
Audio Manager - Handles audio device selection and system-level audio routing
"""
import pyaudio
import subprocess
import logging
import os

logger = logging.getLogger(__name__)


class AudioManager:
    """Manages audio device selection and routing"""
    
    def __init__(self):
        """Initialize audio manager"""
        self.selected_mic_device = None  # Device that captures audio (goes to SIM808 mic in)
        self.selected_speaker_device = None  # Device that plays audio (from SIM808 speaker out)
        self.pyaudio_instance = None
        
    def get_audio_devices(self):
        """
        Get list of available audio devices
        
        Returns:
            dict: Dictionary with 'inputs' and 'outputs' lists
        """
        return self._enumerate_devices()
    
    def _enumerate_devices(self):
        """
        Enumerate audio devices using pyaudio
        
        Returns:
            dict: Dictionary with 'inputs' and 'outputs' lists
        """
        devices = {'inputs': [], 'outputs': []}
        
        try:
            p = pyaudio.PyAudio()
            device_count = p.get_device_count()
            
            for i in range(device_count):
                try:
                    info = p.get_device_info_by_index(i)
                    device_info = {
                        'index': i,
                        'name': info.get('name', f'Device {i}'),
                        'channels': {
                            'input': info.get('maxInputChannels', 0),
                            'output': info.get('maxOutputChannels', 0)
                        },
                        'sample_rate': int(info.get('defaultSampleRate', 44100)),
                        'host_api': p.get_host_api_info_by_index(info.get('hostApi', 0)).get('name', 'Unknown')
                    }
                    
                    if device_info['channels']['input'] > 0:
                        devices['inputs'].append(device_info)
                    
                    if device_info['channels']['output'] > 0:
                        devices['outputs'].append(device_info)
                        
                except Exception as e:
                    logger.debug(f"Error getting info for device {i}: {e}")
                    continue
                    
            p.terminate()
            
        except Exception as e:
            logger.error(f"Error enumerating audio devices: {e}")
        
        return devices
    
    def set_microphone_device(self, device_index):
        """
        Set the microphone device (audio that goes to SIM808 mic in)
        
        Note: This is actually the USB sound card's speaker output,
        which is connected to SIM808's mic in. So we select a device
        that will be used to send audio TO the SIM808.
        
        Args:
            device_index (int): Audio device index
            
        Returns:
            bool: True if device is valid and set
        """
        devices = self._enumerate_devices()
        valid_indices = [d['index'] for d in devices['outputs']]
        
        if device_index in valid_indices:
            self.selected_mic_device = device_index
            logger.info(f"Set microphone device to index {device_index}")
            return True
        else:
            logger.error(f"Invalid microphone device index: {device_index}")
            return False
    
    def set_speaker_device(self, device_index):
        """
        Set the speaker device (audio that comes from SIM808 speaker out)
        
        Note: This is actually the USB sound card's microphone input,
        which receives audio FROM the SIM808's speaker out. So we select
        a device that will be used to receive audio FROM the SIM808.
        
        Args:
            device_index (int): Audio device index
            
        Returns:
            bool: True if device is valid and set
        """
        devices = self._enumerate_devices()
        valid_indices = [d['index'] for d in devices['inputs']]
        
        if device_index in valid_indices:
            self.selected_speaker_device = device_index
            logger.info(f"Set speaker device to index {device_index}")
            return True
        else:
            logger.error(f"Invalid speaker device index: {device_index}")
            return False
    
    def get_selected_devices(self):
        """
        Get currently selected audio devices
        
        Returns:
            dict: Dictionary with 'mic' and 'speaker' device indices
        """
        return {
            'mic': self.selected_mic_device,
            'speaker': self.selected_speaker_device
        }
    
    def configure_audio_routing(self):
        """
        Configure system-level audio routing using ALSA/PulseAudio
        
        This function provides instructions/documentation for manual configuration
        or attempts automatic configuration if possible.
        
        Returns:
            dict: Configuration status and instructions
        """
        config_status = {
            'configured': False,
            'method': None,
            'instructions': []
        }
        
        # Check if PulseAudio is available
        if self._check_pulseaudio():
            config_status['method'] = 'pulseaudio'
            config_status['instructions'] = self._get_pulseaudio_instructions()
        elif self._check_alsa():
            config_status['method'] = 'alsa'
            config_status['instructions'] = self._get_alsa_instructions()
        else:
            config_status['instructions'] = [
                "No audio system detected. Please configure audio routing manually."
            ]
        
        return config_status
    
    def _check_pulseaudio(self):
        """Check if PulseAudio is running"""
        try:
            result = subprocess.run(
                ['pulseaudio', '--check'],
                capture_output=True,
                timeout=1
            )
            return result.returncode == 0
        except:
            return False
    
    def _check_alsa(self):
        """Check if ALSA is available"""
        return os.path.exists('/proc/asound')
    
    def _get_pulseaudio_instructions(self):
        """Get instructions for PulseAudio configuration"""
        instructions = [
            "PulseAudio detected. To configure audio routing:",
            "",
            "1. List available devices:",
            "   pactl list short sources  # for inputs",
            "   pactl list short sinks    # for outputs",
            "",
            "2. Set default source (speaker - receives from SIM808):",
            f"   pactl set-default-source <device_name>",
            "",
            "3. Set default sink (microphone - sends to SIM808):",
            f"   pactl set-default-sink <device_name>",
            "",
            "Note: The selected devices in the web app indicate which devices",
            "should be configured. Audio routing happens at the system level."
        ]
        return instructions
    
    def _get_alsa_instructions(self):
        """Get instructions for ALSA configuration"""
        instructions = [
            "ALSA detected. To configure audio routing:",
            "",
            "1. List available devices:",
            "   arecord -l  # for inputs",
            "   aplay -l    # for outputs",
            "",
            "2. Create/edit ~/.asoundrc to set default devices",
            "",
            "3. Test audio:",
            "   arecord -D <device> test.wav",
            "   aplay -D <device> test.wav",
            "",
            "Note: The selected devices in the web app indicate which devices",
            "should be configured. Audio routing happens at the system level."
        ]
        return instructions
    
    def get_device_name(self, device_index):
        """
        Get the name of an audio device by index
        
        Args:
            device_index (int): Audio device index
            
        Returns:
            str: Device name or None
        """
        try:
            p = pyaudio.PyAudio()
            info = p.get_device_info_by_index(device_index)
            name = info.get('name', f'Device {device_index}')
            p.terminate()
            return name
        except:
            return None
