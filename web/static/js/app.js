// Whisper Meeting Transcriber - Frontend JavaScript

let selectedFile = null;
let currentTaskId = null;
let websocket = null;

// DOM Elements
const dropzone = document.getElementById('dropzone');
const fileInput = document.getElementById('fileInput');
const fileInfo = document.getElementById('fileInfo');
const fileName = document.getElementById('fileName');
const fileSize = document.getElementById('fileSize');
const removeFileBtn = document.getElementById('removeFile');
const transcribeBtn = document.getElementById('transcribeBtn');
const cancelBtn = document.getElementById('cancelBtn');
const diarizeCheckbox = document.getElementById('diarize');
const speakerSettings = document.getElementById('speakerSettings');
const progressSection = document.getElementById('progressSection');
const progressBar = document.getElementById('progressBar');
const progressText = document.getElementById('progressText');
const progressPercent = document.getElementById('progressPercent');
const statusText = document.getElementById('statusText');
const resultsSection = document.getElementById('resultsSection');
const resultPreview = document.getElementById('resultPreview');
const downloadBtn = document.getElementById('downloadBtn');
const errorSection = document.getElementById('errorSection');
const errorMessage = document.getElementById('errorMessage');
const taskHistory = document.getElementById('taskHistory');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    checkConnection();
    checkModels();
    loadTaskHistory();
    setInterval(loadTaskHistory, 5000); // Refresh every 5 seconds
});

// Check Whisper service connection
async function checkConnection() {
    try {
        const response = await fetch('/health');
        const data = await response.json();
        const indicator = document.getElementById('statusIndicator');
        
        if (data.status === 'healthy') {
            indicator.innerHTML = `
                <i class="fas fa-check-circle text-green-500 mr-2"></i>
                <span class="text-green-600">Connected</span>
            `;
        } else {
            indicator.innerHTML = `
                <i class="fas fa-exclamation-circle text-red-500 mr-2"></i>
                <span class="text-red-600">Disconnected</span>
            `;
        }
    } catch (error) {
        const indicator = document.getElementById('statusIndicator');
        indicator.innerHTML = `
            <i class="fas fa-exclamation-circle text-red-500 mr-2"></i>
            <span class="text-red-600">Error</span>
        `;
    }
}

// Check available models
async function checkModels() {
    try {
        const response = await fetch('/models');
        const models = await response.json();
        const modelSelect = document.getElementById('modelSelect');
        const modelStatus = document.getElementById('modelStatus');
        
        // Update model select options with availability
        const options = modelSelect.options;
        let availableCount = 0;
        
        for (let i = 0; i < options.length; i++) {
            const modelId = options[i].value;
            const model = models[modelId];
            
            if (model && model.available) {
                options[i].text = `${model.name} ✓`;
                availableCount++;
            } else if (model) {
                options[i].text = `${model.name} ✗`;
                options[i].disabled = true;
            }
        }
        
        modelStatus.innerHTML = `
            <i class="fas fa-info-circle mr-1"></i>
            ${availableCount} model${availableCount !== 1 ? 's' : ''} available
        `;
    } catch (error) {
        console.error('Error checking models:', error);
        const modelStatus = document.getElementById('modelStatus');
        modelStatus.innerHTML = `
            <i class="fas fa-exclamation-circle mr-1 text-red-500"></i>
            <span class="text-red-600">Error checking models</span>
        `;
    }
}

// File handling
dropzone.addEventListener('click', () => fileInput.click());
fileInput.addEventListener('change', handleFileSelect);

// Drag and drop
dropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropzone.classList.add('dragover');
});

dropzone.addEventListener('dragleave', () => {
    dropzone.classList.remove('dragover');
});

dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.classList.remove('dragover');
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        handleFile(files[0]);
    }
});

function handleFileSelect(e) {
    const files = e.target.files;
    if (files.length > 0) {
        handleFile(files[0]);
    }
}

function handleFile(file) {
    // Validate file type
    const allowedTypes = ['video/', 'audio/'];
    const isAllowed = allowedTypes.some(type => file.type.startsWith(type));
    
    if (!isAllowed && !file.name.match(/\.(mp4|avi|mov|mkv|webm|mp3|wav|m4a)$/i)) {
        showError('Please select a valid video or audio file');
        return;
    }
    
    selectedFile = file;
    fileName.textContent = file.name;
    fileSize.textContent = formatFileSize(file.size);
    fileInfo.classList.remove('hidden');
    transcribeBtn.disabled = false;
    hideError();
}

removeFileBtn.addEventListener('click', () => {
    selectedFile = null;
    fileInput.value = '';
    fileInfo.classList.add('hidden');
    transcribeBtn.disabled = true;
});

// Speaker diarization toggle
diarizeCheckbox.addEventListener('change', (e) => {
    if (e.target.checked) {
        speakerSettings.classList.remove('hidden');
    } else {
        speakerSettings.classList.add('hidden');
    }
});

// Transcription
transcribeBtn.addEventListener('click', startTranscription);
cancelBtn.addEventListener('click', cancelTranscription);

async function startTranscription() {
    if (!selectedFile) return;
    
    // Validate speaker settings
    const minSpeakers = document.getElementById('minSpeakers').value;
    const maxSpeakers = document.getElementById('maxSpeakers').value;
    
    if (diarizeCheckbox.checked) {
        if (minSpeakers && parseInt(minSpeakers) < 1) {
            showError('Minimum speakers must be at least 1');
            return;
        }
        if (maxSpeakers && parseInt(maxSpeakers) < 1) {
            showError('Maximum speakers must be at least 1');
            return;
        }
        if (minSpeakers && maxSpeakers && parseInt(minSpeakers) > parseInt(maxSpeakers)) {
            showError('Minimum speakers cannot exceed maximum speakers');
            return;
        }
    }
    
    // Prepare form data
    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('output_format', document.querySelector('input[name="format"]:checked').value);
    formData.append('model', document.getElementById('modelSelect').value);
    formData.append('diarize', diarizeCheckbox.checked);
    
    if (diarizeCheckbox.checked) {
        if (minSpeakers) formData.append('min_speakers', minSpeakers);
        if (maxSpeakers) formData.append('max_speakers', maxSpeakers);
    }
    
    // Reset UI
    hideError();
    resultsSection.classList.add('hidden');
    progressSection.classList.remove('hidden');
    transcribeBtn.classList.add('hidden');
    cancelBtn.classList.remove('hidden');
    updateProgress(0, 'Uploading file...');
    
    try {
        // Start transcription
        const response = await fetch('/transcribe', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to start transcription');
        }
        
        const data = await response.json();
        currentTaskId = data.task_id;
        
        // Connect WebSocket for progress updates
        connectWebSocket(currentTaskId);
        
    } catch (error) {
        showError(error.message);
        resetUI();
    }
}

function connectWebSocket(taskId) {
    const wsUrl = `ws://${window.location.host}/ws/${taskId}`;
    websocket = new WebSocket(wsUrl);
    
    websocket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        updateTaskStatus(data);
    };
    
    websocket.onerror = () => {
        showError('WebSocket connection error');
    };
    
    websocket.onclose = () => {
        if (currentTaskId === taskId) {
            // Fallback to polling if WebSocket closes
            pollStatus(taskId);
        }
    };
}

async function pollStatus(taskId) {
    if (currentTaskId !== taskId) return;
    
    try {
        const response = await fetch(`/status/${taskId}`);
        const data = await response.json();
        updateTaskStatus(data);
        
        if (data.status === 'processing' || data.status === 'pending') {
            setTimeout(() => pollStatus(taskId), 1000);
        }
    } catch (error) {
        console.error('Polling error:', error);
    }
}

function updateTaskStatus(task) {
    if (task.task_id !== currentTaskId) return;
    
    updateProgress(task.progress, task.message);
    
    // Show additional info during processing
    if (task.status === 'processing' && statusMessage) {
        let infoText = task.message;
        if (task.file_duration_seconds) {
            infoText += ` • Duration: ${formatTime(task.file_duration_seconds)}`;
        }
        if (task.file_size_mb) {
            infoText += ` • Size: ${task.file_size_mb.toFixed(1)} MB`;
        }
        if (task.model_used) {
            infoText += ` • Model: ${task.model_used}`;
        }
        statusText.textContent = infoText;
    }
    
    if (task.status === 'completed') {
        // Show completion metrics
        if (task.execution_time_seconds && task.transcription_speed_ratio) {
            const metricsText = `Completed in ${formatTime(task.execution_time_seconds)} (${task.transcription_speed_ratio.toFixed(1)}x speed)`;
            updateProgress(100, metricsText);
            setTimeout(() => {
                showResults(task);
                resetUI();
                loadTaskHistory();
            }, 2000); // Show metrics for 2 seconds
        } else {
            showResults(task);
            resetUI();
            loadTaskHistory();
        }
    } else if (task.status === 'failed') {
        showError(task.error || 'Transcription failed');
        resetUI();
        loadTaskHistory();
    } else if (task.status === 'cancelled') {
        showError('Transcription cancelled');
        resetUI();
        loadTaskHistory();
    }
}

async function cancelTranscription() {
    if (!currentTaskId) return;
    
    try {
        await fetch(`/cancel/${currentTaskId}`, { method: 'POST' });
        if (websocket) {
            websocket.close();
        }
    } catch (error) {
        console.error('Cancel error:', error);
    }
}

async function showResults(task) {
    resultsSection.classList.remove('hidden');
    progressSection.classList.add('hidden');
    
    // Load and show preview
    try {
        const response = await fetch(`/result/${task.task_id}`);
        const text = await response.text();
        
        // Show preview (first 500 characters)
        resultPreview.textContent = text.substring(0, 500) + (text.length > 500 ? '...' : '');
        
        // Set up download
        downloadBtn.onclick = () => {
            const a = document.createElement('a');
            a.href = `/result/${task.task_id}`;
            a.download = `transcription_${task.task_id}.${task.settings.output_format}`;
            a.click();
        };
    } catch (error) {
        console.error('Error loading result:', error);
    }
}

async function loadTaskHistory() {
    try {
        const response = await fetch('/tasks');
        const tasks = await response.json();
        
        if (tasks.length === 0) {
            taskHistory.innerHTML = '<p class="text-gray-500 text-sm">No transcriptions yet</p>';
            return;
        }
        
        // Sort by creation time (newest first)
        tasks.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
        
        // Display recent tasks with metrics
        taskHistory.innerHTML = tasks.slice(0, 5).map(task => {
            const icon = task.status === 'completed' ? 'check-circle' : 
                        task.status === 'failed' ? 'times-circle' :
                        task.status === 'processing' ? 'spinner fa-spin' : 'clock';
            
            const color = task.status === 'completed' ? 'green' :
                         task.status === 'failed' ? 'red' :
                         task.status === 'processing' ? 'blue' : 'gray';
            
            // Format metrics
            const metrics = [];
            if (task.execution_time_seconds) {
                metrics.push(`<span class="text-xs text-gray-600"><i class="fas fa-clock text-xs mr-1"></i>${formatTime(task.execution_time_seconds)}</span>`);
            }
            if (task.transcription_speed_ratio) {
                metrics.push(`<span class="text-xs text-indigo-600 font-medium"><i class="fas fa-tachometer-alt text-xs mr-1"></i>${task.transcription_speed_ratio.toFixed(1)}x speed</span>`);
            }
            if (task.word_count) {
                metrics.push(`<span class="text-xs text-gray-600"><i class="fas fa-file-word text-xs mr-1"></i>${task.word_count.toLocaleString()} words</span>`);
            }
            if (task.speakers_detected) {
                metrics.push(`<span class="text-xs text-purple-600"><i class="fas fa-users text-xs mr-1"></i>${task.speakers_detected} speakers</span>`);
            }
            
            return `
                <div class="p-4 bg-gray-50 rounded-lg mb-3 hover:bg-gray-100 transition">
                    <div class="flex items-start justify-between">
                        <div class="flex items-start">
                            <i class="fas fa-${icon} text-${color}-600 mr-3 mt-1"></i>
                            <div>
                                <p class="font-medium text-sm">${task.filename}</p>
                                <p class="text-xs text-gray-500 mb-1">${formatDate(task.created_at)}</p>
                                <div class="flex items-center gap-2 flex-wrap">
                                    ${task.model_used ? `<span class="text-xs text-gray-700 bg-gray-200 px-2 py-1 rounded">${task.model_used}</span>` : ''}
                                    ${task.file_size_mb ? `<span class="text-xs text-gray-600">${task.file_size_mb.toFixed(1)} MB</span>` : ''}
                                    ${task.file_duration_seconds ? `<span class="text-xs text-gray-600">${formatTime(task.file_duration_seconds)} duration</span>` : ''}
                                </div>
                                ${metrics.length > 0 ? `<div class="flex items-center gap-3 mt-2">${metrics.join('')}</div>` : ''}
                            </div>
                        </div>
                        ${task.status === 'completed' ? `
                            <button onclick="downloadResult('${task.task_id}')" class="text-indigo-600 hover:text-indigo-800 ml-4">
                                <i class="fas fa-download"></i>
                            </button>
                        ` : ''}
                    </div>
                </div>
            `;
        }).join('');
    } catch (error) {
        console.error('Error loading task history:', error);
    }
}

function downloadResult(taskId) {
    const a = document.createElement('a');
    a.href = `/result/${taskId}`;
    a.download = true;
    a.click();
}

// Utility functions
function updateProgress(percent, message) {
    progressBar.style.width = `${percent}%`;
    progressPercent.textContent = `${percent}%`;
    progressText.textContent = message;
    statusText.textContent = message;
}

function showError(message) {
    errorMessage.textContent = message;
    errorSection.classList.remove('hidden');
}

function hideError() {
    errorSection.classList.add('hidden');
}

function resetUI() {
    transcribeBtn.classList.remove('hidden');
    cancelBtn.classList.add('hidden');
    currentTaskId = null;
    if (websocket) {
        websocket.close();
        websocket = null;
    }
}

function formatFileSize(bytes) {
    const sizes = ['B', 'KB', 'MB', 'GB'];
    if (bytes === 0) return '0 B';
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
}

function formatDate(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now - date;
    
    if (diff < 60000) return 'Just now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)} minutes ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)} hours ago`;
    
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
}

function formatTime(seconds) {
    if (seconds < 60) {
        return `${seconds.toFixed(1)}s`;
    } else if (seconds < 3600) {
        const minutes = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${minutes}m ${secs}s`;
    } else {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        return `${hours}h ${minutes}m`;
    }
}