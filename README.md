# SIM808 Softphone Web Application

A web-based softphone application for controlling a SIM808 GSM/GPRS module connected to a Raspberry Pi. This application provides a user-friendly interface to make and receive phone calls through the SIM808 module.

## Hardware Setup

### UART Connection (AT Commands)
- **SIM808 RXD** ↔ **TTL Adapter TXD**
- **SIM808 TXD** ↔ **TTL Adapter RXD**
- **SIM808 GND** ↔ **TTL Adapter GND**
- **TTL Adapter** ↔ **Raspberry Pi USB Port**

### Audio Connection
- **SIM808 MIC IN** ↔ **USB Sound Card Speaker OUT**
- **SIM808 Speaker OUT** ↔ **USB Sound Card MIC IN**
- **USB Sound Card** ↔ **Raspberry Pi USB Port**

### Important Audio Routing Note
Due to the reversed audio connections:
- **Web app "Microphone" selection** → USB sound card speaker output → SIM808 mic in (what you speak)
- **Web app "Speaker" selection** → USB sound card mic input → SIM808 speaker out (what you hear)

## Software Requirements

- Raspberry Pi OS (or compatible Linux distribution)
- Python 3.7 or higher
- pip (Python package manager)

## Installation

1. **Clone or download this repository to your Raspberry Pi**

2. **Install system dependencies** (if not already installed):
   ```bash
   sudo apt-get update
   sudo apt-get install -y python3-pip python3-dev portaudio19-dev
   ```

3. **Install Python dependencies**:
   ```bash
   pip3 install -r requirements.txt
   ```

   Note: If you encounter permission issues, use `pip3 install --user -r requirements.txt`

4. **Set up audio system** (choose one):

   **For PulseAudio:**
   ```bash
   sudo apt-get install -y pulseaudio
   ```

   **For ALSA only:**
   ```bash
   sudo apt-get install -y alsa-utils
   ```

## Usage

1. **Start the application**:
   ```bash
   python3 app.py
   ```

2. **Access the web interface**:
   - Open a web browser on any device on the same network
   - Navigate to `http://<raspberry-pi-ip>:5000`
   - Example: `http://192.168.1.100:5000`

3. **Configure devices**:
   - **Serial Port**: Select the `/dev/ttyUSB*` device connected to your SIM808 (default baudrate: 115200)
   - **Raspberry Pi Audio Devices**:
     - **Microphone Device**: Select the audio output device that connects to SIM808 mic in (USB sound card speaker)
     - **Speaker Device**: Select the audio input device that receives from SIM808 speaker out (USB sound card mic)
   - **Browser Audio Devices** (on your local device):
     - **Browser Microphone**: Select the microphone on the device where you opened the web app
     - **Browser Speaker**: Select the speaker on the device where you opened the web app
   - Click "Connect" to establish serial connection
   - Click "Save Audio Devices" to save your Raspberry Pi audio device selections
   - Browser audio devices are selected automatically when you choose them from the dropdown

4. **Make a call**:
   - Enter a phone number in the "Phone Number" field
   - Click "Dial"
   - Use the DTMF keypad to send tones during the call

5. **Receive a call**:
   - When an incoming call is detected, a notification will appear
   - Click "Answer" to accept or "Reject" to decline

6. **End a call**:
   - Click "Hang Up" to end the active call

## Audio Configuration

The application allows you to select audio devices, but actual audio routing must be configured at the system level using ALSA or PulseAudio.

### PulseAudio Configuration

1. List available devices:
   ```bash
   pactl list short sources  # for inputs (speaker - from SIM808)
   pactl list short sinks    # for outputs (microphone - to SIM808)
   ```

2. Set default devices:
   ```bash
   pactl set-default-source <input_device_name>
   pactl set-default-sink <output_device_name>
   ```

### ALSA Configuration

1. List available devices:
   ```bash
   arecord -l  # for inputs
   aplay -l    # for outputs
   ```

2. Test audio:
   ```bash
   arecord -D hw:1,0 test.wav  # record from device
   aplay -D hw:1,0 test.wav    # play to device
   ```

3. Configure default devices in `~/.asoundrc` if needed

## API Endpoints

The application provides REST API endpoints for programmatic control:

- `GET /api/devices/serial` - List available serial ports
- `GET /api/devices/audio` - List available audio devices
- `POST /api/connect` - Connect to SIM808 (requires `port` and optional `baudrate`)
- `POST /api/disconnect` - Disconnect from SIM808
- `GET /api/status` - Get current connection and call status
- `POST /api/call/dial` - Dial a number (requires `number`)
- `POST /api/call/answer` - Answer incoming call
- `POST /api/call/hangup` - Hang up active call
- `POST /api/call/dtmf` - Send DTMF tone (requires `digit`)
- `POST /api/audio/select` - Select audio devices (requires `mic_device` and/or `speaker_device`)
- `GET /api/audio/selected` - Get currently selected audio devices

## WebSocket Events

The application uses WebSocket (Socket.IO) for real-time status updates:

- `status_update` - Emitted when call status changes
  - Events: `incoming_call`, `call_ended`, `call_busy`, `call_status`

## Troubleshooting

### Serial Port Issues
- Ensure the TTL adapter is properly connected
- Check that the user has permissions to access `/dev/ttyUSB*`:
  ```bash
  sudo usermod -a -G dialout $USER
  ```
  (Log out and back in for changes to take effect)
- Verify the port with: `ls -l /dev/ttyUSB*`

### Audio Issues
- Verify USB sound card is detected: `lsusb`
- Check audio devices: `arecord -l` and `aplay -l`
- Test audio routing manually before using the web app
- Ensure PulseAudio is running: `pulseaudio --check`

### Connection Issues
- Verify SIM808 is powered on
- Check AT command response: `minicom -D /dev/ttyUSB0 -b 115200`
- Test with: `echo "AT" > /dev/ttyUSB0` and check response

### SIM Card Issues
- Ensure SIM card is inserted and activated
- Check network registration with AT command: `AT+CREG?`
- Verify signal strength: `AT+CSQ`

## Security Considerations

- The application runs on `0.0.0.0:5000` by default, making it accessible on your local network
- For production use, consider:
  - Adding authentication
  - Using HTTPS
  - Restricting access with a firewall
  - Running behind a reverse proxy

## AT Commands Used

- `AT` - Test connection
- `ATD<number>;` - Dial number
- `ATH` - Hang up
- `ATA` - Answer call
- `AT+CLCC` - List current calls
- `AT+VTS=<digit>` - Send DTMF tone
- `AT+CLIP=1` - Enable caller ID presentation

## License

This project is provided as-is for educational and personal use.

## Support

For SIM808-specific issues, refer to the [SIM800 Series AT Command Manual](https://simcom.ee/documents/SIM808/SIM800%20Series_AT%20Command%20Manual_V1.09.pdf).
