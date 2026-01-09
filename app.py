"""
Flask Web Application for SIM808 Softphone
"""
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import logging
import threading
import time

from sim808_controller import SIM808Controller
from device_manager import discover_serial_ports, discover_audio_devices
from audio_manager import AudioManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'sim808-softphone-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Global instances
sim808 = SIM808Controller()
audio_manager = AudioManager()


def status_callback(event_type, data):
    """Callback for SIM808 status updates"""
    socketio.emit('status_update', {
        'event': event_type,
        'data': data
    })
    logger.info(f"Status update: {event_type} - {data}")


# Register status callback
sim808.register_status_callback(status_callback)


@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')


@app.route('/api/devices/serial', methods=['GET'])
def get_serial_devices():
    """Get list of available serial ports"""
    try:
        ports = discover_serial_ports()
        return jsonify({'success': True, 'devices': ports})
    except Exception as e:
        logger.error(f"Error getting serial devices: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/devices/audio', methods=['GET'])
def get_audio_devices():
    """Get list of available audio devices"""
    try:
        devices = discover_audio_devices()
        return jsonify({'success': True, 'devices': devices})
    except Exception as e:
        logger.error(f"Error getting audio devices: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/connect', methods=['POST'])
def connect_serial():
    """Connect to SIM808 via serial port"""
    try:
        data = request.get_json()
        port = data.get('port')
        baudrate = data.get('baudrate', 115200)
        
        if not port:
            return jsonify({'success': False, 'error': 'Port not specified'}), 400
        
        # Disconnect if already connected
        if sim808.is_connected:
            sim808.disconnect()
        
        # Connect to new port
        if sim808.connect(port):
            return jsonify({
                'success': True,
                'message': f'Connected to {port}',
                'port': port
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to connect'}), 500
            
    except Exception as e:
        logger.error(f"Error connecting: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/disconnect', methods=['POST'])
def disconnect_serial():
    """Disconnect from SIM808"""
    try:
        sim808.disconnect()
        return jsonify({'success': True, 'message': 'Disconnected'})
    except Exception as e:
        logger.error(f"Error disconnecting: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/status', methods=['GET'])
def get_status():
    """Get current connection and call status"""
    try:
        status = {
            'connected': sim808.is_connected,
            'port': sim808.port if sim808.is_connected else None,
            'call_status': sim808.current_call_status,
            'incoming_number': sim808.incoming_call_number
        }
        
        # Get detailed call status if connected
        if sim808.is_connected:
            call_info = sim808.get_call_status()
            if call_info:
                status['call_info'] = call_info
        
        return jsonify({'success': True, 'status': status})
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/call/dial', methods=['POST'])
def dial():
    """Dial a phone number"""
    try:
        if not sim808.is_connected:
            return jsonify({'success': False, 'error': 'Not connected to SIM808'}), 400
        
        data = request.get_json()
        number = data.get('number')
        
        if not number:
            return jsonify({'success': False, 'error': 'Phone number not specified'}), 400
        
        if sim808.dial(number):
            return jsonify({'success': True, 'message': f'Dialing {number}'})
        else:
            return jsonify({'success': False, 'error': 'Failed to dial'}), 500
            
    except Exception as e:
        logger.error(f"Error dialing: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/call/answer', methods=['POST'])
def answer():
    """Answer incoming call"""
    try:
        if not sim808.is_connected:
            return jsonify({'success': False, 'error': 'Not connected to SIM808'}), 400
        
        if sim808.answer():
            return jsonify({'success': True, 'message': 'Call answered'})
        else:
            return jsonify({'success': False, 'error': 'Failed to answer call'}), 500
            
    except Exception as e:
        logger.error(f"Error answering call: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/call/hangup', methods=['POST'])
def hangup():
    """Hang up active call"""
    try:
        if not sim808.is_connected:
            return jsonify({'success': False, 'error': 'Not connected to SIM808'}), 400
        
        if sim808.hangup():
            return jsonify({'success': True, 'message': 'Call ended'})
        else:
            return jsonify({'success': False, 'error': 'Failed to hang up'}), 500
            
    except Exception as e:
        logger.error(f"Error hanging up: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/call/dtmf', methods=['POST'])
def send_dtmf():
    """Send DTMF tone"""
    try:
        if not sim808.is_connected:
            return jsonify({'success': False, 'error': 'Not connected to SIM808'}), 400
        
        data = request.get_json()
        digit = data.get('digit')
        
        if not digit:
            return jsonify({'success': False, 'error': 'DTMF digit not specified'}), 400
        
        if sim808.send_dtmf(digit):
            return jsonify({'success': True, 'message': f'Sent DTMF: {digit}'})
        else:
            return jsonify({'success': False, 'error': 'Failed to send DTMF'}), 500
            
    except Exception as e:
        logger.error(f"Error sending DTMF: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/audio/select', methods=['POST'])
def select_audio_devices():
    """Select audio input and output devices"""
    try:
        data = request.get_json()
        mic_device = data.get('mic_device')
        speaker_device = data.get('speaker_device')
        
        result = {'success': True, 'messages': []}
        
        if mic_device is not None:
            if audio_manager.set_microphone_device(mic_device):
                result['messages'].append(f'Microphone device set to {mic_device}')
            else:
                result['success'] = False
                result['messages'].append(f'Failed to set microphone device {mic_device}')
        
        if speaker_device is not None:
            if audio_manager.set_speaker_device(speaker_device):
                result['messages'].append(f'Speaker device set to {speaker_device}')
            else:
                result['success'] = False
                result['messages'].append(f'Failed to set speaker device {speaker_device}')
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Error selecting audio devices: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/audio/selected', methods=['GET'])
def get_selected_audio_devices():
    """Get currently selected audio devices"""
    try:
        devices = audio_manager.get_selected_devices()
        config = audio_manager.configure_audio_routing()
        
        return jsonify({
            'success': True,
            'devices': devices,
            'config': config
        })
    except Exception as e:
        logger.error(f"Error getting selected audio devices: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@socketio.on('connect')
def handle_connect():
    """Handle WebSocket connection"""
    logger.info('Client connected')
    emit('connected', {'message': 'Connected to SIM808 Softphone'})
    
    # Send current status
    status = {
        'connected': sim808.is_connected,
        'port': sim808.port if sim808.is_connected else None,
        'call_status': sim808.current_call_status
    }
    emit('status_update', {'event': 'initial_status', 'data': status})


@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket disconnection"""
    logger.info('Client disconnected')


def status_polling_thread():
    """Background thread to poll call status periodically"""
    while True:
        try:
            if sim808.is_connected:
                call_status = sim808.get_call_status()
                if call_status:
                    socketio.emit('status_update', {
                        'event': 'call_status',
                        'data': call_status
                    })
            time.sleep(2)  # Poll every 2 seconds
        except Exception as e:
            logger.error(f"Error in status polling: {e}")
            time.sleep(5)


if __name__ == '__main__':
    # Start status polling thread
    polling_thread = threading.Thread(target=status_polling_thread, daemon=True)
    polling_thread.start()
    
    # Run Flask app
    logger.info("Starting SIM808 Softphone web application...")
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)
