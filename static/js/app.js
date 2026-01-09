// SIM808 Softphone Web Application JavaScript

// Initialize Socket.IO connection
const socket = io();

// State management
let state = {
    connected: false,
    callStatus: null,
    incomingCallNumber: null,
    selectedSerialPort: null,
    selectedMicDevice: null,
    selectedSpeakerDevice: null,
    browserMicDevice: null,
    browserSpeakerDevice: null,
    audioContext: null,
    mediaStream: null,
    audioSource: null,
    currentBrowserMicName: null,
    currentBrowserSpeakerName: null
};

// DOM Elements
const elements = {
    connectionStatus: document.getElementById('connectionStatus'),
    statusIndicator: document.getElementById('statusIndicator'),
    statusText: document.getElementById('statusText'),
    serialPort: document.getElementById('serialPort'),
    refreshSerial: document.getElementById('refreshSerial'),
    connectBtn: document.getElementById('connectBtn'),
    disconnectBtn: document.getElementById('disconnectBtn'),
    micDevice: document.getElementById('micDevice'),
    speakerDevice: document.getElementById('speakerDevice'),
    saveAudioDevices: document.getElementById('saveAudioDevices'),
    callStatus: document.getElementById('callStatus'),
    callStatusText: document.getElementById('callStatusText'),
    callNumber: document.getElementById('callNumber'),
    phoneNumber: document.getElementById('phoneNumber'),
    dialBtn: document.getElementById('dialBtn'),
    answerBtn: document.getElementById('answerBtn'),
    hangupBtn: document.getElementById('hangupBtn'),
    dtmfKeypad: document.getElementById('dtmfKeypad'),
    incomingCallNotification: document.getElementById('incomingCallNotification'),
    incomingCallNumber: document.getElementById('incomingCallNumber'),
    answerIncomingBtn: document.getElementById('answerIncomingBtn'),
    rejectIncomingBtn: document.getElementById('rejectIncomingBtn'),
    messages: document.getElementById('messages'),
    browserMicInfo: document.getElementById('browserMicInfo'),
    browserSpeakerInfo: document.getElementById('browserSpeakerInfo'),
    refreshBrowserDevices: document.getElementById('refreshBrowserDevices'),
    testBrowserAudio: document.getElementById('testBrowserAudio')
};

// Utility functions
function addMessage(message, type = 'info') {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message message-${type}`;
    messageDiv.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
    elements.messages.insertBefore(messageDiv, elements.messages.firstChild);
    
    // Keep only last 50 messages
    while (elements.messages.children.length > 50) {
        elements.messages.removeChild(elements.messages.lastChild);
    }
}

function updateConnectionStatus(connected, port = null) {
    state.connected = connected;
    elements.statusIndicator.className = `status-indicator ${connected ? 'connected' : 'disconnected'}`;
    elements.statusText.textContent = connected ? `Connected to ${port || 'SIM808'}` : 'Disconnected';
    elements.connectBtn.disabled = connected;
    elements.disconnectBtn.disabled = !connected;
    elements.dialBtn.disabled = !connected;
    elements.answerBtn.disabled = !connected;
    elements.hangupBtn.disabled = !connected;
}

function updateCallStatus(status, number = null) {
    state.callStatus = status;
    state.incomingCallNumber = number;
    
    const statusMap = {
        'dialing': 'Dialing...',
        'ringing': 'Ringing...',
        'active': 'Call Active',
        'incoming': 'Incoming Call',
        'held': 'Call Held',
        'waiting': 'Call Waiting'
    };
    
    elements.callStatusText.textContent = status ? statusMap[status] || status : 'No active call';
    elements.callNumber.textContent = number ? number : '';
    
    // Show/hide incoming call notification
    if (status === 'incoming') {
        elements.incomingCallNotification.style.display = 'block';
        elements.incomingCallNumber.textContent = number || 'Unknown number';
    } else {
        elements.incomingCallNotification.style.display = 'none';
    }
}

// API functions
async function apiCall(endpoint, method = 'GET', data = null) {
    try {
        const options = {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            }
        };
        
        if (data) {
            options.body = JSON.stringify(data);
        }
        
        const response = await fetch(`/api/${endpoint}`, options);
        const result = await response.json();
        
        if (!result.success) {
            throw new Error(result.error || 'API call failed');
        }
        
        return result;
    } catch (error) {
        addMessage(`Error: ${error.message}`, 'error');
        throw error;
    }
}

async function loadSerialDevices() {
    try {
        const result = await apiCall('devices/serial');
        elements.serialPort.innerHTML = '<option value="">Select serial port...</option>';
        result.devices.forEach(port => {
            const option = document.createElement('option');
            option.value = port;
            option.textContent = port;
            if (port === state.selectedSerialPort) {
                option.selected = true;
            }
            elements.serialPort.appendChild(option);
        });
    } catch (error) {
        addMessage('Failed to load serial devices', 'error');
    }
}

async function loadAudioDevices() {
    try {
        const result = await apiCall('devices/audio');
        
        // Populate microphone devices (outputs - goes to SIM808)
        elements.micDevice.innerHTML = '<option value="">Select microphone device...</option>';
        result.devices.outputs.forEach(device => {
            const option = document.createElement('option');
            option.value = device.index;
            option.textContent = `${device.name} (${device.host_api})`;
            if (device.index === state.selectedMicDevice) {
                option.selected = true;
            }
            elements.micDevice.appendChild(option);
        });
        
        // Populate speaker devices (inputs - from SIM808)
        elements.speakerDevice.innerHTML = '<option value="">Select speaker device...</option>';
        result.devices.inputs.forEach(device => {
            const option = document.createElement('option');
            option.value = device.index;
            option.textContent = `${device.name} (${device.host_api})`;
            if (device.index === state.selectedSpeakerDevice) {
                option.selected = true;
            }
            elements.speakerDevice.appendChild(option);
        });
    } catch (error) {
        addMessage('Failed to load audio devices', 'error');
    }
}

async function connectSerial() {
    const port = elements.serialPort.value;
    if (!port) {
        addMessage('Please select a serial port', 'error');
        return;
    }
    
    try {
        addMessage(`Connecting to ${port}...`, 'info');
        const result = await apiCall('connect', 'POST', { port: port, baudrate: 115200 });
        state.selectedSerialPort = port;
        addMessage(result.message, 'success');
        await refreshStatus();
    } catch (error) {
        addMessage(`Failed to connect: ${error.message}`, 'error');
    }
}

async function disconnectSerial() {
    try {
        const result = await apiCall('disconnect', 'POST');
        addMessage(result.message, 'success');
        updateConnectionStatus(false);
        updateCallStatus(null);
    } catch (error) {
        addMessage(`Failed to disconnect: ${error.message}`, 'error');
    }
}

async function refreshStatus() {
    try {
        const result = await apiCall('status');
        const status = result.status;
        updateConnectionStatus(status.connected, status.port);
        updateCallStatus(status.call_status, status.incoming_number);
    } catch (error) {
        addMessage(`Failed to refresh status: ${error.message}`, 'error');
    }
}

async function dial() {
    const number = elements.phoneNumber.value.trim();
    if (!number) {
        addMessage('Please enter a phone number', 'error');
        return;
    }
    
    try {
        addMessage(`Dialing ${number}...`, 'info');
        const result = await apiCall('call/dial', 'POST', { number: number });
        addMessage(result.message, 'success');
        updateCallStatus('dialing');
    } catch (error) {
        addMessage(`Failed to dial: ${error.message}`, 'error');
    }
}

async function answer() {
    try {
        const result = await apiCall('call/answer', 'POST');
        addMessage(result.message, 'success');
        updateCallStatus('active');
    } catch (error) {
        addMessage(`Failed to answer: ${error.message}`, 'error');
    }
}

async function hangup() {
    try {
        const result = await apiCall('call/hangup', 'POST');
        addMessage(result.message, 'success');
        updateCallStatus(null);
    } catch (error) {
        addMessage(`Failed to hang up: ${error.message}`, 'error');
    }
}

async function sendDTMF(digit) {
    try {
        const result = await apiCall('call/dtmf', 'POST', { digit: digit });
        addMessage(result.message, 'success');
    } catch (error) {
        addMessage(`Failed to send DTMF: ${error.message}`, 'error');
    }
}

async function saveAudioDevices() {
    const micDevice = elements.micDevice.value ? parseInt(elements.micDevice.value) : null;
    const speakerDevice = elements.speakerDevice.value ? parseInt(elements.speakerDevice.value) : null;
    
    if (micDevice === null && speakerDevice === null) {
        addMessage('Please select at least one audio device', 'error');
        return;
    }
    
    try {
        const result = await apiCall('audio/select', 'POST', {
            mic_device: micDevice,
            speaker_device: speakerDevice
        });
        
        if (result.success) {
            state.selectedMicDevice = micDevice;
            state.selectedSpeakerDevice = speakerDevice;
            result.messages.forEach(msg => addMessage(msg, 'success'));
        } else {
            result.messages.forEach(msg => addMessage(msg, 'error'));
        }
    } catch (error) {
        addMessage(`Failed to save audio devices: ${error.message}`, 'error');
    }
}

// Event listeners
elements.refreshSerial.addEventListener('click', loadSerialDevices);
elements.connectBtn.addEventListener('click', connectSerial);
elements.disconnectBtn.addEventListener('click', disconnectSerial);
elements.dialBtn.addEventListener('click', dial);
elements.answerBtn.addEventListener('click', answer);
elements.hangupBtn.addEventListener('click', hangup);
elements.saveAudioDevices.addEventListener('click', saveAudioDevices);
elements.answerIncomingBtn.addEventListener('click', answer);
elements.rejectIncomingBtn.addEventListener('click', hangup);

// DTMF keypad
elements.dtmfKeypad.addEventListener('click', (e) => {
    if (e.target.classList.contains('dtmf-key')) {
        const digit = e.target.getAttribute('data-digit');
        sendDTMF(digit);
    }
});

// Allow Enter key to dial
elements.phoneNumber.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        dial();
    }
});

// Socket.IO event handlers
socket.on('connect', () => {
    addMessage('Connected to server', 'success');
    refreshStatus();
});

socket.on('disconnect', () => {
    addMessage('Disconnected from server', 'error');
    updateConnectionStatus(false);
});

socket.on('connected', (data) => {
    addMessage(data.message, 'success');
});

socket.on('status_update', (data) => {
    const { event, data: eventData } = data;
    
    switch (event) {
        case 'incoming_call':
            updateCallStatus('incoming', eventData.number);
            addMessage(`Incoming call from ${eventData.number || 'unknown'}`, 'info');
            break;
            
        case 'call_ended':
            updateCallStatus(null);
            addMessage('Call ended', 'info');
            break;
            
        case 'call_busy':
            updateCallStatus(null);
            addMessage('Call busy', 'error');
            break;
            
        case 'call_status':
            updateCallStatus(eventData.status, eventData.number);
            break;
            
        case 'initial_status':
            updateConnectionStatus(eventData.connected, eventData.port);
            updateCallStatus(eventData.call_status);
            break;
    }
});

// Browser audio device functions - detect and display default devices
async function loadBrowserAudioDevices() {
    try {
        // Check if browser supports media devices API
        if (!navigator.mediaDevices) {
            elements.browserMicInfo.textContent = 'Not supported - browser will use default';
            elements.browserSpeakerInfo.textContent = 'Not supported - browser will use default';
            addMessage('Browser does not support MediaDevices API. Using default devices.', 'info');
            return;
        }
        
        // Request permission to access audio devices first (required for device labels)
        let permissionGranted = false;
        if (navigator.mediaDevices.getUserMedia) {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                // Get the actual device being used
                const audioTrack = stream.getAudioTracks()[0];
                if (audioTrack) {
                    const settings = audioTrack.getSettings();
                    state.browserMicDevice = settings.deviceId || 'default';
                    state.currentBrowserMicName = audioTrack.label || 'Default Microphone';
                    elements.browserMicInfo.textContent = state.currentBrowserMicName;
                }
                stream.getTracks().forEach(track => track.stop());
                permissionGranted = true;
            } catch (e) {
                if (e.name === 'NotAllowedError' || e.name === 'PermissionDeniedError') {
                    elements.browserMicInfo.textContent = 'Permission denied - click to grant access';
                    addMessage('Microphone permission needed to detect device name.', 'info');
                } else if (e.name === 'NotFoundError') {
                    elements.browserMicInfo.textContent = 'No microphone found';
                    addMessage('No microphone found on this device.', 'error');
                } else {
                    elements.browserMicInfo.textContent = 'Error detecting device';
                    addMessage(`Microphone access error: ${e.message}`, 'error');
                }
            }
        }
        
        // Try to enumerate devices to get speaker info (if supported)
        if (navigator.mediaDevices.enumerateDevices && permissionGranted) {
            try {
                const devices = await navigator.mediaDevices.enumerateDevices();
                
                // Find default input device (usually the first one with a label)
                const inputDevices = devices.filter(device => device.kind === 'audioinput');
                if (inputDevices.length > 0 && !state.currentBrowserMicName) {
                    const defaultInput = inputDevices.find(d => d.label) || inputDevices[0];
                    if (defaultInput && defaultInput.label) {
                        state.currentBrowserMicName = defaultInput.label;
                        elements.browserMicInfo.textContent = defaultInput.label;
                    }
                }
                
                // Try to find speaker devices (audiooutput enumeration is limited)
                const outputDevices = devices.filter(device => device.kind === 'audiooutput');
                if (outputDevices.length > 0) {
                    const defaultOutput = outputDevices.find(d => d.label) || outputDevices[0];
                    if (defaultOutput && defaultOutput.label) {
                        state.currentBrowserSpeakerName = defaultOutput.label;
                        elements.browserSpeakerInfo.textContent = defaultOutput.label;
                    }
                } else {
                    // Most browsers don't support audiooutput enumeration
                    elements.browserSpeakerInfo.textContent = 'Default system speaker';
                    state.currentBrowserSpeakerName = 'Default Speaker';
                }
                
            } catch (error) {
                // If enumeration fails, just show default
                if (!state.currentBrowserMicName) {
                    elements.browserMicInfo.textContent = 'Default microphone';
                }
                elements.browserSpeakerInfo.textContent = 'Default system speaker';
            }
        } else {
            // Fallback to default messages
            if (!state.currentBrowserMicName) {
                elements.browserMicInfo.textContent = 'Default microphone (permission needed to see name)';
            }
            elements.browserSpeakerInfo.textContent = 'Default system speaker';
        }
        
    } catch (error) {
        elements.browserMicInfo.textContent = 'Error detecting device';
        elements.browserSpeakerInfo.textContent = 'Error detecting device';
        addMessage(`Failed to detect browser audio devices: ${error.message}`, 'error');
    }
}

// Browser devices use defaults - no selection needed

async function testBrowserAudio() {
    try {
        addMessage('Testing browser audio...', 'info');
        
        // Check if getUserMedia is available
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            addMessage('Browser does not support audio capture', 'error');
            return;
        }
        
        // Get user media with default device
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        
        // Get the actual device being used for display
        const audioTrack = stream.getAudioTracks()[0];
        if (audioTrack) {
            const deviceName = audioTrack.label || 'Default Microphone';
            addMessage(`Using microphone: ${deviceName}`, 'info');
        }
        
        // Create audio context and connect to speakers
        if (!state.audioContext) {
            state.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        }
        
        // Create a simple feedback loop for testing
        const source = state.audioContext.createMediaStreamSource(stream);
        const destination = state.audioContext.createMediaStreamDestination();
        source.connect(destination);
        
        // Play through default speaker
        const audio = new Audio();
        audio.srcObject = destination.stream;
        await audio.play();
        
        addMessage('Audio test started. You should hear your microphone. Test will stop automatically.', 'success');
        
        // Stop after 5 seconds
        setTimeout(() => {
            stream.getTracks().forEach(track => track.stop());
            audio.pause();
            audio.srcObject = null;
            if (state.audioContext && state.audioContext.state !== 'closed') {
                state.audioContext.close();
                state.audioContext = null;
            }
            addMessage('Audio test stopped', 'info');
        }, 5000);
        
    } catch (error) {
        addMessage(`Audio test failed: ${error.message}`, 'error');
        if (error.name === 'NotAllowedError') {
            addMessage('Please allow microphone access and try again', 'error');
        }
    }
}

// Event listeners for browser audio devices
elements.refreshBrowserDevices.addEventListener('click', loadBrowserAudioDevices);
elements.testBrowserAudio.addEventListener('click', testBrowserAudio);

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    addMessage('SIM808 Softphone initialized', 'info');
    loadSerialDevices();
    loadAudioDevices();
    loadBrowserAudioDevices();
    refreshStatus();
    
    // Refresh status periodically
    setInterval(refreshStatus, 5000);
});
