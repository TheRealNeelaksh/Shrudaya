document.addEventListener('DOMContentLoaded', () => {
    // UI Elements
    const contactScreen = document.getElementById('contact-screen');
    const loadingScreen = document.getElementById('loading-screen');
    const callScreen = document.getElementById('call-screen');
    const notAvailableScreen = document.getElementById('not-available-screen');
    const callTaaraBtn = document.getElementById('call-taara');
    const callVeerBtn = document.getElementById('call-veer');
    const endCallBtn = document.getElementById('end-call-btn');
    const goBackBtn = document.getElementById('go-back-btn');
    const transcriptDisplay = document.getElementById('transcript-display');
    const aiResponseText = document.getElementById('ai-response-text');
    const statusListening = document.getElementById('status-listening');
    const statusProcessing = document.getElementById('status-processing');
    const statusSpeaking = document.getElementById('status-speaking');
    const callName = document.getElementById('call-name');
    const callTimer = document.getElementById('call-timer');
    const loadingText = document.getElementById('loading-text');
    const callVisualizer = document.querySelector('.call-visualizer');

    // State variables
    let socket;
    let audioContext;
    let workletNode;
    let mediaStream;
    let timerInterval;
    let seconds = 0;
    
    // MSE Audio Player State
    let mediaSource;
    let sourceBuffer;
    let audioQueue = [];
    let isAppending = false;
    let audioElement;

    // Turn-taking state
    let isAiSpeaking = false;
    const allStatusGifs = [statusListening, statusProcessing, statusSpeaking];

    const updateStatusIndicator = (state) => {
        allStatusGifs.forEach(gif => gif.classList.remove('active'));
        if (state === 'listening') statusListening.classList.add('active');
        else if (state === 'processing') statusProcessing.classList.add('active');
        else if (state === 'speaking') statusSpeaking.classList.add('active');
    };

    const showScreen = (screenToShow) => {
        document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
        screenToShow.classList.add('active');
    };

    const startCall = async (contact) => {
        transcriptDisplay.textContent = '';
        aiResponseText.textContent = '';
        showScreen(loadingScreen);
        loadingText.textContent = `Connecting to ${contact}...`;
        try {
            setupAudioPlayback();
            const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            socket = new WebSocket(`${wsProtocol}//${window.location.host}/ws`);
            socket.onopen = () => {
                setupAudioProcessing();
                callName.textContent = contact;
                showScreen(callScreen);
                startTimer();
                updateStatusIndicator('listening');
            };
            socket.onmessage = handleSocketMessage;
            socket.onclose = () => endCall('Connection closed.');
            socket.onerror = () => endCall('A connection error occurred.');
        } catch (error) {
            endCall('Failed to initialize call.');
        }
    };

    const setupAudioProcessing = async () => {
        try {
            mediaStream = await navigator.mediaDevices.getUserMedia({ audio: { sampleRate: 16000, channelCount: 1, echoCancellation: true, noiseSuppression: true } });
            audioContext = new AudioContext({ sampleRate: 16000 });
            await audioContext.audioWorklet.addModule('/static/audio-processor.js');
            workletNode = new AudioWorkletNode(audioContext, 'audio-processor');
            workletNode.port.onmessage = (event) => {
                if (isAiSpeaking || socket?.readyState !== WebSocket.OPEN) return;
                const audioBuffer = event.data;
                const base64Data = btoa(String.fromCharCode.apply(null, new Uint8Array(audioBuffer)));
                socket.send(base64Data);
                const floatArray = new Float32Array(audioBuffer);
                let sum = floatArray.reduce((a, b) => a + Math.abs(b), 0);
                callVisualizer.style.transform = `scale(${1 + (sum / floatArray.length) * 10})`;
            };
            const source = audioContext.createMediaStreamSource(mediaStream);
            source.connect(workletNode);
        } catch (err) {
            alert("Could not access microphone. Please grant permission and refresh.");
            endCall("Could not access microphone.");
        }
    };

    function setupAudioPlayback() {
        audioElement = new Audio();
        // Don't set autoplay here, we will control it manually
        mediaSource = new MediaSource();
        audioElement.src = URL.createObjectURL(mediaSource);
        mediaSource.addEventListener('sourceopen', () => {
            console.log("MediaSource opened.");
            const mimeCodec = 'audio/mpeg'; // Use a simpler MIME type for broader compatibility
            if (MediaSource.isTypeSupported(mimeCodec)) {
                sourceBuffer = mediaSource.addSourceBuffer(mimeCodec);
                sourceBuffer.addEventListener('updateend', () => {
                    isAppending = false;
                    processAudioQueue();
                });
            } else {
                console.error("MIME type not supported:", mimeCodec);
            }
        });
    }

    function processAudioQueue() {
        if (isAppending || audioQueue.length === 0 || !sourceBuffer || sourceBuffer.updating) {
            return;
        }
        isAppending = true;
        const audioChunk = audioQueue.shift();
        sourceBuffer.appendBuffer(audioChunk);
    }

    function handleSocketMessage(event) {
        if (event.data instanceof Blob) {
            // THE FINAL FIX: Give the audio player a "nudge" to start playing.
            if (audioElement.paused) {
                audioElement.play().catch(e => console.error("Audio play failed:", e));
            }
            const reader = new FileReader();
            reader.onload = function() {
                audioQueue.push(reader.result);
                processAudioQueue();
            };
            reader.readAsArrayBuffer(event.data);
        } else {
            const msg = JSON.parse(event.data);
            if (msg.type === 'user_transcript') {
                if (transcriptDisplay) transcriptDisplay.textContent = `You: "${msg.data}"`;
                if (aiResponseText) aiResponseText.textContent = 'Taara: ';
                updateStatusIndicator('processing');
            } else if (msg.type === 'ai_text_chunk') {
                if (aiResponseText) aiResponseText.textContent += msg.data;
            } else if (msg.type === 'tts_start') {
                isAiSpeaking = true;
                updateStatusIndicator('speaking');
            } else if (msg.type === 'tts_end') {
                isAiSpeaking = false;
                updateStatusIndicator('listening');
            }
        }
    }
    
    const endCall = (reason = 'Call ended.') => {
        console.log(reason);
        clearInterval(timerInterval);
        seconds = 0;
        if (workletNode) workletNode.port.close();
        if (mediaStream) mediaStream.getTracks().forEach(track => track.stop());
        if (audioContext && audioContext.state !== 'closed') audioContext.close();
        if (socket && socket.readyState !== WebSocket.CLOSED) socket.close();
        if (audioElement && audioElement.src) URL.revokeObjectURL(audioElement.src);
        audioQueue = [];
        isAiSpeaking = false;
        showScreen(contactScreen);
        updateStatusIndicator('idle');
    };

    const startTimer = () => {
        callTimer.textContent = '00:00';
        timerInterval = setInterval(() => {
            seconds++;
            const mins = String(Math.floor(seconds / 60)).padStart(2, '0');
            const secs = String(seconds % 60).padStart(2, '0');
            callTimer.textContent = `${mins}:${secs}`;
        }, 1000);
    };

    callTaaraBtn.addEventListener('click', () => startCall('Taara'));
    callVeerBtn.addEventListener('click', () => showScreen(notAvailableScreen));
    goBackBtn.addEventListener('click', () => showScreen(contactScreen));
    endCallBtn.addEventListener('click', () => endCall());
});