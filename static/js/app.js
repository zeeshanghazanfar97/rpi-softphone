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
    selectedSpeakerDevice: null
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
    messages: document.getElementById('messages')
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
        const result = await apiCall('connect', 'POST', { port: port, baudrate: 9600 });
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

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    addMessage('SIM808 Softphone initialized', 'info');
    loadSerialDevices();
    loadAudioDevices();
    refreshStatus();
    
    // Refresh status periodically
    setInterval(refreshStatus, 5000);
});
