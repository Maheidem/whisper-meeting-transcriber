/**
 * Meeting Transcriber - Frontend Logic
 * Lean version: WebSocket-first, minimal polling fallback
 */

// DOM Elements
const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');
const selectedFile = document.getElementById('selectedFile');
const uploadForm = document.getElementById('uploadForm');
const submitBtn = document.getElementById('submitBtn');
const modelSelect = document.getElementById('modelSelect');
const languageSelect = document.getElementById('languageSelect');
const formatSelect = document.getElementById('formatSelect');
const diarizeCheck = document.getElementById('diarizeCheck');
const speakerOptions = document.getElementById('speakerOptions');
const progressSection = document.getElementById('progressSection');
const progressBar = document.getElementById('progressBar');
const progressText = document.getElementById('progressText');
const resultSection = document.getElementById('resultSection');
const resultStats = document.getElementById('resultStats');
const downloadBtn = document.getElementById('downloadBtn');
const errorSection = document.getElementById('errorSection');
const errorText = document.getElementById('errorText');
const taskHistory = document.getElementById('taskHistory');

// Settings elements
const settingsToggle = document.getElementById('settingsToggle');
const settingsPanel = document.getElementById('settingsPanel');
const settingsArrow = document.getElementById('settingsArrow');
const hfTokenInput = document.getElementById('hfTokenInput');
const toggleTokenVisibility = document.getElementById('toggleTokenVisibility');
const tokenStatus = document.getElementById('tokenStatus');
const saveSettingsBtn = document.getElementById('saveSettingsBtn');
const settingsFeedback = document.getElementById('settingsFeedback');

let currentFile = null;
let currentTaskId = null;
let ws = null;

// Progress tracking state
let progressState = {
    startTime: null,
    elapsedTimer: null,
    lastProgress: 0,
    lastProgressTime: null,
    audioDuration: null,
    isDiarizeEnabled: false,
    currentStep: null,
};

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
    await loadGpuStatus();
    await loadModels();
    await loadLanguages();
    await loadFormats();
    await loadHistory();
    await loadSettings();
    setupEventListeners();
    setupSettingsListeners();
});

async function loadGpuStatus() {
    try {
        const res = await fetch('/gpu');
        const data = await res.json();
        const gpuStatusEl = document.getElementById('gpuStatus');
        if (!gpuStatusEl) return;

        const isGpu = data.gpu.available;
        const icon = isGpu ? '⚡' : '💻';
        const bgColor = isGpu ? 'bg-green-100' : 'bg-gray-100';
        const textColor = isGpu ? 'text-green-700' : 'text-gray-600';
        const dotColor = isGpu ? 'bg-green-500' : 'bg-gray-400';

        gpuStatusEl.innerHTML = `
            <span class="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${bgColor} ${textColor}">
                <span class="w-2 h-2 rounded-full ${dotColor} mr-2"></span>
                ${icon} ${data.gpu.name} · ${data.speed_estimate}
            </span>
        `;
    } catch (e) {
        console.error('Failed to load GPU status:', e);
    }
}

async function loadModels() {
    try {
        const res = await fetch('/models');
        const data = await res.json();
        modelSelect.innerHTML = data.models.map(m =>
            `<option value="${m.id}" ${m.id === data.default ? 'selected' : ''}>${m.name} - ${m.description}</option>`
        ).join('');
    } catch (e) {
        console.error('Failed to load models:', e);
    }
}

async function loadLanguages() {
    try {
        const res = await fetch('/languages');
        const data = await res.json();
        languageSelect.innerHTML = data.languages.map(l =>
            `<option value="${l.code}" ${l.code === data.default ? 'selected' : ''}>${l.name}</option>`
        ).join('');
    } catch (e) {
        console.error('Failed to load languages:', e);
    }
}

async function loadFormats() {
    try {
        const res = await fetch('/formats');
        const data = await res.json();
        formatSelect.innerHTML = data.formats.map(f =>
            `<option value="${f}" ${f === data.default ? 'selected' : ''}>${f.toUpperCase()}</option>`
        ).join('');
    } catch (e) {
        console.error('Failed to load formats:', e);
    }
}

async function loadHistory() {
    try {
        const res = await fetch('/tasks');
        const data = await res.json();
        if (data.tasks.length === 0) {
            taskHistory.innerHTML = '<p class="text-gray-400 text-sm">No transcriptions yet</p>';
            return;
        }
        taskHistory.innerHTML = data.tasks.slice(-5).reverse().map(task => `
            <div class="flex items-center justify-between p-2 bg-gray-50 rounded">
                <div>
                    <span class="text-sm font-medium">${task.filename || 'Unknown'}</span>
                    <span class="text-xs text-gray-400 ml-2">${task.status}</span>
                </div>
                ${task.status === 'completed' ?
                    `<a href="/result/${task.task_id}" class="text-blue-600 text-sm hover:underline">Download</a>` :
                    ''}
            </div>
        `).join('');
    } catch (e) {
        console.error('Failed to load history:', e);
    }
}

function setupEventListeners() {
    // Drag and drop
    dropZone.addEventListener('click', () => fileInput.click());
    dropZone.addEventListener('dragover', e => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });
    dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
    dropZone.addEventListener('drop', e => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        if (e.dataTransfer.files.length) {
            handleFile(e.dataTransfer.files[0]);
        }
    });

    // File input
    fileInput.addEventListener('change', () => {
        if (fileInput.files.length) {
            handleFile(fileInput.files[0]);
        }
    });

    // Diarization toggle
    diarizeCheck.addEventListener('change', () => {
        speakerOptions.classList.toggle('hidden', !diarizeCheck.checked);
    });

    // Form submit
    uploadForm.addEventListener('submit', handleSubmit);
}

function handleFile(file) {
    currentFile = file;
    selectedFile.textContent = `Selected: ${file.name} (${(file.size / 1024 / 1024).toFixed(1)} MB)`;
    selectedFile.classList.remove('hidden');
    submitBtn.disabled = false;
}

async function handleSubmit(e) {
    e.preventDefault();
    if (!currentFile) return;

    // Reset UI
    hideAll();
    progressSection.classList.remove('hidden');
    submitBtn.disabled = true;

    // Initialize enhanced progress UI
    initProgressUI(currentFile, diarizeCheck.checked);

    // Build form data
    const formData = new FormData();
    formData.append('file', currentFile);
    formData.append('model', modelSelect.value);
    formData.append('language', languageSelect.value);
    formData.append('output_format', formatSelect.value);
    formData.append('diarize', diarizeCheck.checked);

    const minSpeakers = document.getElementById('minSpeakers').value;
    const maxSpeakers = document.getElementById('maxSpeakers').value;
    if (minSpeakers) formData.append('min_speakers', minSpeakers);
    if (maxSpeakers) formData.append('max_speakers', maxSpeakers);

    try {
        // Start transcription
        const res = await fetch('/transcribe', { method: 'POST', body: formData });
        const data = await res.json();

        if (!res.ok) {
            throw new Error(data.detail || 'Upload failed');
        }

        currentTaskId = data.task_id;
        connectWebSocket(data.task_id);

    } catch (err) {
        stopProgressTimer();
        showError(err.message);
    }
}

function connectWebSocket(taskId) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${protocol}//${window.location.host}/ws/${taskId}`);

    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            if (data.ping) return; // Keep-alive

            console.log('[WS] Progress update:', data.progress, data.step, data.message);
            updateEnhancedProgress(data);

            if (data.status === 'completed') {
                stopProgressTimer();
                showResult(data);
                ws.close();
            } else if (data.status === 'failed') {
                stopProgressTimer();
                showError(data.error || 'Transcription failed');
                ws.close();
            }
        } catch (err) {
            console.error('[WS] Error processing message:', err);
        }
    };

    ws.onerror = (err) => {
        console.error('[WS] WebSocket error:', err);
        // Fallback to polling if WebSocket fails
        pollStatus(taskId);
    };

    ws.onclose = () => {
        loadHistory();
    };
}

async function pollStatus(taskId) {
    try {
        const res = await fetch(`/status/${taskId}`);
        const data = await res.json();

        updateEnhancedProgress(data);

        if (data.status === 'completed') {
            stopProgressTimer();
            showResult(data);
        } else if (data.status === 'failed') {
            stopProgressTimer();
            showError(data.error);
        } else {
            setTimeout(() => pollStatus(taskId), 2000);
        }
    } catch (e) {
        stopProgressTimer();
        showError('Lost connection to server');
    }
}

// === ENHANCED PROGRESS FUNCTIONS ===

function initProgressUI(file, isDiarize) {
    // Reset progress state
    progressState = {
        startTime: Date.now(),
        elapsedTimer: null,
        lastProgress: 0,
        lastProgressTime: Date.now(),
        audioDuration: null,
        isDiarizeEnabled: isDiarize,
        currentStep: 'upload',
    };

    // Set file info
    const filenameEl = document.getElementById('progressFilename');
    const fileSizeEl = document.getElementById('progressFileSize');
    if (filenameEl) filenameEl.textContent = file.name;
    if (fileSizeEl) fileSizeEl.textContent = `${(file.size / 1024 / 1024).toFixed(1)} MB`;

    // Show/hide diarization step
    const diarizeContainer = document.getElementById('step-diarize-container');
    const line3 = document.getElementById('line-3');
    if (diarizeContainer) {
        diarizeContainer.classList.toggle('hidden', !isDiarize);
    }
    if (line3) {
        line3.classList.toggle('hidden', !isDiarize);
    }

    // Reset step indicators
    resetStepIndicators();

    // Reset progress bar
    progressBar.style.width = '0%';
    progressBar.classList.add('progress-bar-animated');

    // Reset text elements
    const stepNameEl = document.getElementById('progressStepName');
    const percentEl = document.getElementById('progressPercent');
    const substepEl = document.getElementById('progressSubstep');
    const etaEl = document.getElementById('progressETA');
    const speedEl = document.getElementById('progressSpeed');
    const audioInfoEl = document.getElementById('progressAudioInfo');

    if (stepNameEl) stepNameEl.textContent = 'Uploading...';
    if (percentEl) percentEl.textContent = '0%';
    if (substepEl) substepEl.classList.add('hidden');
    if (etaEl) etaEl.classList.add('hidden');
    if (speedEl) speedEl.classList.add('hidden');
    if (audioInfoEl) audioInfoEl.classList.add('hidden');

    progressText.textContent = 'Starting transcription...';

    // Start elapsed timer
    startProgressTimer();
}

function resetStepIndicators() {
    const steps = ['upload', 'extract', 'transcribe', 'diarize', 'complete'];
    const lines = [1, 2, 3, 4];

    steps.forEach(step => {
        const el = document.getElementById(`step-${step}`);
        if (el) {
            el.classList.remove('completed', 'active');
            el.classList.add('text-gray-400');
        }
    });

    lines.forEach(num => {
        const el = document.getElementById(`line-${num}`);
        if (el) {
            el.classList.remove('completed');
        }
    });

    // Mark upload as completed (file was selected)
    const uploadStep = document.getElementById('step-upload');
    if (uploadStep) {
        uploadStep.classList.add('completed');
        uploadStep.classList.remove('text-gray-400');
    }
}

function startProgressTimer() {
    const elapsedEl = document.getElementById('elapsedTime');
    if (!elapsedEl) return;

    progressState.elapsedTimer = setInterval(() => {
        const elapsed = Math.floor((Date.now() - progressState.startTime) / 1000);
        elapsedEl.textContent = formatTime(elapsed);
    }, 1000);
}

function stopProgressTimer() {
    if (progressState.elapsedTimer) {
        clearInterval(progressState.elapsedTimer);
        progressState.elapsedTimer = null;
    }
}

function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

function formatDuration(seconds) {
    if (seconds >= 3600) {
        const hours = Math.floor(seconds / 3600);
        const mins = Math.floor((seconds % 3600) / 60);
        return `${hours}h ${mins}m`;
    } else if (seconds >= 60) {
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}m ${secs}s`;
    }
    return `${Math.floor(seconds)}s`;
}

function updateEnhancedProgress(data) {
    try {
        const progress = data.progress || 0;
        const message = data.message || '';
        const step = data.step || '';
        const stepName = data.step_name || '';
        const substep = data.substep || '';
        const audioDuration = data.audio_duration;
        const currentTime = data.current_time;

        // Update progress bar
        if (progressBar) {
            progressBar.style.width = `${progress}%`;
        }

        // Update percentage
        const percentEl = document.getElementById('progressPercent');
        if (percentEl) percentEl.textContent = `${progress}%`;

        // Update step name
        const stepNameEl = document.getElementById('progressStepName');
        if (stepNameEl) stepNameEl.textContent = stepName || 'Processing...';

        // Update message
        if (progressText) {
            progressText.textContent = message;
        }

        // Update substep
        const substepEl = document.getElementById('progressSubstep');
        if (substepEl) {
            if (substep) {
                substepEl.textContent = substep;
                substepEl.classList.remove('hidden');
            } else {
                substepEl.classList.add('hidden');
            }
        }

        // Update audio duration info
        if (audioDuration && audioDuration > 0) {
            progressState.audioDuration = audioDuration;
            const audioInfoEl = document.getElementById('progressAudioInfo');
            const audioDurationEl = document.getElementById('audioDuration');
            if (audioInfoEl && audioDurationEl) {
                audioDurationEl.textContent = formatDuration(audioDuration);
                audioInfoEl.classList.remove('hidden');
            }
        }

        // Calculate and show ETA during transcription
        if (step === 'transcribing' && audioDuration && currentTime) {
            calculateAndShowETA(progress, audioDuration, currentTime);
        }

        // Update step indicators (with error protection)
        if (step) {
            updateStepIndicators(step);
        }

        // Store progress for ETA calculation
        progressState.lastProgress = progress;
        progressState.lastProgressTime = Date.now();

        // Remove animation when complete
        if (progress >= 100 && progressBar) {
            progressBar.classList.remove('progress-bar-animated');
        }
    } catch (err) {
        console.error('[Progress] Error updating progress:', err);
    }
}

function calculateAndShowETA(progress, audioDuration, currentTime) {
    const elapsed = (Date.now() - progressState.startTime) / 1000;
    const etaEl = document.getElementById('progressETA');
    const etaTimeEl = document.getElementById('etaTime');
    const speedEl = document.getElementById('progressSpeed');
    const speedValueEl = document.getElementById('speedValue');

    if (!etaEl || !etaTimeEl) return;

    // Calculate processing speed (realtime multiplier)
    if (currentTime > 0 && elapsed > 0) {
        const speed = currentTime / elapsed;

        // Show speed
        if (speedEl && speedValueEl) {
            speedValueEl.textContent = speed.toFixed(1);
            speedEl.classList.remove('hidden');
        }

        // Estimate remaining time
        const remainingAudio = audioDuration - currentTime;
        if (remainingAudio > 0 && speed > 0) {
            const etaSeconds = remainingAudio / speed;
            // Add buffer for formatting step (roughly 10% of transcription time)
            const totalEta = etaSeconds * (progressState.isDiarizeEnabled ? 1.4 : 1.1);

            etaTimeEl.textContent = formatTime(Math.ceil(totalEta));
            etaEl.classList.remove('hidden');
        }
    }
}

function updateStepIndicators(currentStep) {
    try {
        if (!currentStep) return;

        const stepToIndicator = {
            'upload': 'upload',
            'extracting': 'extract',
            'preparing': 'extract',
            'loading_model': 'extract',
            'transcribing': 'transcribe',
            'diarizing': 'diarize',
            'formatting': 'complete',
            'complete': 'complete',
        };

        const indicatorOrder = ['upload', 'extract', 'transcribe', 'diarize', 'complete'];
        const lineMap = { 'extract': 1, 'transcribe': 2, 'diarize': 3, 'complete': 4 };

        // Determine which indicator this step maps to
        const targetIndicator = stepToIndicator[currentStep] || 'extract';
        const targetIndex = indicatorOrder.indexOf(targetIndicator);
        if (targetIndex === -1) return;

        const checkSvg = '<svg class="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" /></svg>';

        indicatorOrder.forEach((indicator, index) => {
            const el = document.getElementById(`step-${indicator}`);
            if (!el) return;

            // Skip diarize if not enabled
            if (indicator === 'diarize' && !progressState.isDiarizeEnabled) return;

            if (index < targetIndex) {
                // Completed steps
                el.classList.add('completed');
                el.classList.remove('active', 'text-gray-400');
                el.innerHTML = checkSvg;
            } else if (index === targetIndex) {
                // Current step
                el.classList.add('active');
                el.classList.remove('completed', 'text-gray-400');
                if (indicator === 'complete') {
                    el.innerHTML = checkSvg;
                }
            } else {
                // Future steps
                el.classList.remove('completed', 'active');
                el.classList.add('text-gray-400');
            }
        });

        // Update lines
        for (let i = 1; i <= 4; i++) {
            const lineEl = document.getElementById(`line-${i}`);
            if (!lineEl) continue;
            const correspondingIndicator = Object.keys(lineMap).find(k => lineMap[k] === i);
            const correspondingIndex = indicatorOrder.indexOf(correspondingIndicator);
            if (correspondingIndex <= targetIndex) {
                lineEl.classList.add('completed');
            } else {
                lineEl.classList.remove('completed');
            }
        }

        progressState.currentStep = currentStep;
    } catch (err) {
        console.error('[StepIndicators] Error:', err);
    }
}

function updateProgress(progress, message) {
    // Legacy function - redirect to enhanced
    updateEnhancedProgress({ progress, message });
}

function showResult(data) {
    hideAll();
    resultSection.classList.remove('hidden');

    const stats = [];
    if (data.word_count) stats.push(`${data.word_count} words`);
    if (data.speakers_detected) stats.push(`${data.speakers_detected} speakers`);
    resultStats.textContent = stats.join(' | ') || 'Transcription complete';

    downloadBtn.onclick = () => {
        window.location.href = `/result/${currentTaskId}`;
    };

    submitBtn.disabled = false;
    currentFile = null;
    selectedFile.classList.add('hidden');
}

function showError(message) {
    hideAll();
    errorSection.classList.remove('hidden');
    errorText.textContent = message;
    submitBtn.disabled = false;
}

function hideAll() {
    progressSection.classList.add('hidden');
    resultSection.classList.add('hidden');
    errorSection.classList.add('hidden');
    stopProgressTimer();
}

// === SETTINGS ===

async function loadSettings() {
    try {
        const res = await fetch('/settings');
        const data = await res.json();
        updateTokenStatus(data.hf_token_set);
    } catch (e) {
        console.error('Failed to load settings:', e);
    }
}

function updateTokenStatus(isSet) {
    if (isSet) {
        tokenStatus.innerHTML = '<span class="text-green-600">Token configured</span>';
        hfTokenInput.placeholder = '****';
    } else {
        tokenStatus.innerHTML = '<span class="text-gray-500">No token set</span>';
        hfTokenInput.placeholder = 'hf_xxxxxxxxxxxx';
    }
}

function setupSettingsListeners() {
    // Toggle settings panel
    settingsToggle.addEventListener('click', () => {
        settingsPanel.classList.toggle('hidden');
        settingsArrow.classList.toggle('rotate-180');
    });

    // Toggle token visibility
    toggleTokenVisibility.addEventListener('click', () => {
        if (hfTokenInput.type === 'password') {
            hfTokenInput.type = 'text';
        } else {
            hfTokenInput.type = 'password';
        }
    });

    // Save settings
    saveSettingsBtn.addEventListener('click', saveSettings);
}

async function saveSettings() {
    const token = hfTokenInput.value.trim();

    if (!token) {
        settingsFeedback.innerHTML = '<span class="text-red-600">Please enter a token</span>';
        return;
    }

    saveSettingsBtn.disabled = true;
    settingsFeedback.innerHTML = '<span class="text-gray-500">Saving...</span>';

    try {
        const res = await fetch('/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ hf_token: token })
        });

        const data = await res.json();

        if (res.ok && data.success) {
            settingsFeedback.innerHTML = '<span class="text-green-600">Saved!</span>';
            updateTokenStatus(data.hf_token_set);
            hfTokenInput.value = '';
            setTimeout(() => { settingsFeedback.innerHTML = ''; }, 3000);
        } else {
            throw new Error(data.detail || 'Failed to save');
        }
    } catch (e) {
        settingsFeedback.innerHTML = `<span class="text-red-600">Error: ${e.message}</span>`;
    } finally {
        saveSettingsBtn.disabled = false;
    }
}
