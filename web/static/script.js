document.addEventListener('DOMContentLoaded', () => {
    // UI Elements
    const allGifs = {
        listening: document.getElementById('status-listening'),
        processing: document.getElementById('status-processing'),
        speaking: document.getElementById('status-speaking'),
        muted: document.getElementById('status-muted')
    };
    const callTaaraBtn = document.getElementById('call-taara');
    const callVeerBtn = document.getElementById('call-veer');
    const endCallBtn = document.getElementById('end-call-btn');
    const goBackBtn = document.getElementById('go-back-btn');
    const muteBtn = document.getElementById('mute-btn');
    const callVisualizer = document.getElementById('call-visualizer');
    const rippleContainer = document.getElementById('ripple-container');

    // State variables
    let socket;
    let audioContext;
    let workletNode;
    let mediaStream;
    let timerInterval;
    let seconds = 0;
    let mediaSource;
    let sourceBuffer;
    let audioQueue = [];
    let isAppending = false;
    let audioElement;
    let isAiSpeaking = false;
    let isMuted = false;
    let lastRippleTime = 0;
    let aiSpeakingAnimationId;

    const updateStatusIndicator = (state) => {
        if (isMuted && state !== 'idle') { state = 'muted'; }
        Object.values(allGifs).forEach(gif => gif.classList.remove('active'));
        if (allGifs[state]) allGifs[state].classList.add('active');
    };

    const updateMuteButton = () => {
        if (isMuted) {
            muteBtn.innerHTML = `<i class="fas fa-microphone"></i> Unmute`;
            updateStatusIndicator('muted');
        } else {
            muteBtn.innerHTML = `<i class="fas fa-microphone-slash"></i> Mute`;
            updateStatusIndicator(isAiSpeaking ? 'speaking' : 'listening');
        }
    };

    const toggleMute = () => {
        isMuted = !isMuted;
        updateMuteButton();
    };

    const showScreen = (screenId) => {
        document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
        document.getElementById(screenId).classList.add('active');
    };

    const startCall = async (contact) => {
        document.getElementById('transcript-display').textContent = '';
        document.getElementById('ai-response-text').textContent = '';
        isMuted = false;
        showScreen('loading-screen');
        try {
            setupAudioPlayback();
            const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            socket = new WebSocket(`${wsProtocol}//${window.location.host}/ws`);
            socket.onopen = () => {
                setupAudioProcessing();
                document.getElementById('call-name').textContent = contact;
                showScreen('call-screen');
                startTimer();
                updateMuteButton();
                updateStatusIndicator('listening');
            };
            socket.onmessage = handleSocketMessage;
            socket.onclose = () => endCall('Connection closed.');
            socket.onerror = () => endCall('A connection error occurred.');
        } catch (error) {
            endCall('Failed to initialize call.');
        }
    };

    const createRipple = () => {
        const ripple = document.createElement('div');
        ripple.className = 'ripple';
        rippleContainer.appendChild(ripple);
        ripple.addEventListener('animationend', () => ripple.remove());
    };

    const aiSpeakingAnimation = () => {
        const now = Date.now();
        const pulse = 1 + Math.sin(now / 300) * 0.1; // Gentle 10% pulse
        callVisualizer.style.transform = `scale(${pulse})`;
        if (now - lastRippleTime > 400) {
            createRipple();
            lastRippleTime = now;
        }
        aiSpeakingAnimationId = requestAnimationFrame(aiSpeakingAnimation);
    };

    const startAiSpeakingAnimation = () => {
        if (!aiSpeakingAnimationId) { aiSpeakingAnimation(); }
    };

    const stopAiSpeakingAnimation = () => {
        if (aiSpeakingAnimationId) {
            cancelAnimationFrame(aiSpeakingAnimationId);
            aiSpeakingAnimationId = null;
            callVisualizer.style.transform = 'scale(1)';
        }
    };

    const setupAudioProcessing = async () => {
        try {
            mediaStream = await navigator.mediaDevices.getUserMedia({ audio: { sampleRate: 16000, channelCount: 1, echoCancellation: true, noiseSuppression: true } });
            audioContext = new AudioContext({ sampleRate: 16000 });
            await audioContext.audioWorklet.addModule('/static/audio-processor.js');
            workletNode = new AudioWorkletNode(audioContext, 'audio-processor');
            workletNode.port.onmessage = (event) => {
                if (isMuted || isAiSpeaking || socket?.readyState !== WebSocket.OPEN) return;

                const audioBuffer = event.data;
                const base64Data = btoa(String.fromCharCode.apply(null, new Uint8Array(audioBuffer)));
                socket.send(base64Data);

                const floatArray = new Float32Array(audioBuffer);
                const avgVolume = floatArray.reduce((a, b) => a + Math.abs(b), 0) / floatArray.length;

                // CAPPED SCALING: Calculate scale but ensure it doesn't exceed 1.3
                let scale = 1 + avgVolume * 8;
                scale = Math.min(scale, 1.3); // Cap the scale at 1.3 (30% growth)
                callVisualizer.style.transform = `scale(${scale})`;

                // Throttled ripple effect
                const now = Date.now();
                if (avgVolume > 0.01 && now - lastRippleTime > 200) {
                    createRipple();
                    lastRippleTime = now;
                }
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
        audioElement.autoplay = true;
        mediaSource = new MediaSource();
        audioElement.src = URL.createObjectURL(mediaSource);
        mediaSource.addEventListener('sourceopen', () => {
            const mimeCodec = 'audio/mpeg';
            if (MediaSource.isTypeSupported(mimeCodec)) {
                sourceBuffer = mediaSource.addSourceBuffer(mimeCodec);
                sourceBuffer.addEventListener('updateend', () => {
                    isAppending = false;
                    processAudioQueue();
                });
            } else { console.error("MIME type not supported:", mimeCodec); }
        });
    }

    function processAudioQueue() {
        if (isAppending || audioQueue.length === 0 || !sourceBuffer || sourceBuffer.updating) return;
        isAppending = true;
        const audioChunk = audioQueue.shift();
        sourceBuffer.appendBuffer(audioChunk);
    }

    function handleSocketMessage(event) {
        if (event.data instanceof Blob) {
            if (audioElement.paused) { audioElement.play().catch(e => console.error("Audio play failed:", e)); }
            const reader = new FileReader();
            reader.onload = function () { audioQueue.push(reader.result); processAudioQueue(); };
            reader.readAsArrayBuffer(event.data);
        } else {
            const msg = JSON.parse(event.data);
            if (msg.type === 'user_transcript') {
                document.getElementById('transcript-display').textContent = `You: "${msg.data}"`;
                document.getElementById('ai-response-text').textContent = 'Taara: ';
                updateStatusIndicator('processing');
            } else if (msg.type === 'ai_text_chunk') {
                document.getElementById('ai-response-text').textContent += msg.data;
            } else if (msg.type === 'tts_start') {
                isAiSpeaking = true;
                updateStatusIndicator('speaking');
                startAiSpeakingAnimation();
            } else if (msg.type === 'tts_end') {
                isAiSpeaking = false;
                updateStatusIndicator('listening');
                stopAiSpeakingAnimation();
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
        stopAiSpeakingAnimation();
        showScreen('contact-screen');
        updateStatusIndicator('idle');
    };

    const startTimer = () => {
        document.getElementById('call-timer').textContent = '00:00';
        timerInterval = setInterval(() => {
            seconds++;
            const mins = String(Math.floor(seconds / 60)).padStart(2, '0');
            const secs = String(seconds % 60).padStart(2, '0');
            document.getElementById('call-timer').textContent = `${mins}:${secs}`;
        }, 1000);
    };

    // Event Listeners
    callTaaraBtn.addEventListener('click', () => startCall('Taara'));
    callVeerBtn.addEventListener('click', () => showScreen('not-available-screen'));
    goBackBtn.addEventListener('click', () => showScreen('contact-screen'));
    endCallBtn.addEventListener('click', () => endCall());
    muteBtn.addEventListener('click', toggleMute);
});