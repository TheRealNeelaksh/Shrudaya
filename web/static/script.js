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
    const muteBtn = document.getElementById('mute-btn');
    const chatLog = document.getElementById('chat-log');
    const callName = document.getElementById('call-name');
    const callTimer = document.getElementById('call-timer');
    const callVisualizer = document.getElementById('call-visualizer');
    const allGifs = {
        listening: document.getElementById('status-listening'),
        processing: document.getElementById('status-processing'),
        speaking: document.getElementById('status-speaking'),
        muted: document.getElementById('status-muted')
    };
    const callerTune = document.getElementById('caller-tune');
    const connectionChime = document.getElementById('connection-chime');

    // State variables
    let socket;
    let audioContext;
    let workletNode;
    let mediaStream;
    let timerInterval;
    let seconds = 0;
    let mediaSource, sourceBuffer, audioElement;
    let audioQueue = [], isAppending = false;
    let isAiSpeaking = false, isMuted = false;
    let currentAiMessageElement = null;
    let aiSpeakingAnimationId;

    const startCall = (contact) => {
        // --- PASSWORD PROMPT RE-ADDED ---
        const password = prompt("Please enter the password to connect:");
        if (!password) {
            return; // Stop if the user cancels or enters nothing
        }
        
        chatLog.innerHTML = '';
        isMuted = false;
        showScreen('loading-screen');
        document.getElementById('loading-text').textContent = `Connecting to ${contact}...`;
        callerTune.play().catch(e => console.error("Caller tune failed to play:", e));
        const randomDelay = Math.random() * 4000 + 1000;

        setTimeout(() => {
            callerTune.pause();
            callerTune.currentTime = 0;
            connectionChime.play().catch(e => console.error("Chime failed to play:", e));
            try {
                setupAudioPlayback();
                const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                // Add the password to the WebSocket URL
                const wsUrl = `${wsProtocol}//${window.location.host}/ws?password=${encodeURIComponent(password)}`;
                socket = new WebSocket(wsUrl);
                
                socket.onopen = () => {
                    setupAudioProcessing();
                    callName.textContent = contact;
                    showScreen('call-screen');
                    startTimer();
                    updateMuteButton();
                    updateStatusIndicator('listening');
                };

                socket.onmessage = handleSocketMessage;
                
                socket.onclose = (event) => {
                    // Check for our specific "authentication failed" code
                    if (event.code === 4001) {
                        alert("Authentication failed. Please refresh and try again.");
                    }
                    endCall(`Connection closed (code: ${event.code})`);
                };

                socket.onerror = () => endCall('A connection error occurred.');
            } catch (error) {
                endCall('Failed to initialize call.');
            }
        }, randomDelay);
    };

    // --- All other functions remain the same ---

    const updateStatusIndicator = (state) => {
        if (isMuted && state !== 'idle') { state = 'muted'; }
        Object.values(allGifs).forEach(gif => gif.classList.remove('active'));
        if (allGifs[state]) allGifs[state].classList.add('active');
    };
    const showScreen = (screenId) => {
        document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
        document.getElementById(screenId).classList.add('active');
    };
    const addMessageToChatLog = (sender, text) => {
        const messageBubble = document.createElement('div');
        messageBubble.className = `message-bubble ${sender}-message`;
        messageBubble.textContent = text;
        chatLog.appendChild(messageBubble);
        chatLog.scrollTop = chatLog.scrollHeight;
        return messageBubble;
    };
    const aiSpeakingAnimation = () => {
        const pulse = 1 + Math.sin(Date.now() / 300) * 0.1;
        callVisualizer.style.transform = `scale(${pulse})`;
        aiSpeakingAnimationId = requestAnimationFrame(aiSpeakingAnimation);
    };
    const startAiSpeakingAnimation = () => {
        if (!aiSpeakingAnimationId) aiSpeakingAnimation();
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
                let scale = 1 + avgVolume * 8;
                scale = Math.min(scale, 1.3);
                callVisualizer.style.transform = `scale(${scale})`;
            };
            const source = audioContext.createMediaStreamSource(mediaStream);
            source.connect(workletNode);
        } catch (err) {
            endCall("Could not access microphone.");
        }
    };
    function setupAudioPlayback() {
        audioElement = new Audio();
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
            }
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
            reader.onload = function() { audioQueue.push(reader.result); processAudioQueue(); };
            reader.readAsArrayBuffer(event.data);
        } else {
            const msg = JSON.parse(event.data);
            if (msg.type === 'user_transcript') {
                addMessageToChatLog('user', msg.data);
                currentAiMessageElement = null;
                updateStatusIndicator('processing');
            } else if (msg.type === 'ai_text_chunk') {
                if (!currentAiMessageElement) {
                    currentAiMessageElement = addMessageToChatLog('ai', msg.data);
                } else {
                    currentAiMessageElement.textContent += msg.data;
                }
                chatLog.scrollTop = chatLog.scrollHeight;
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
        callerTune.pause(); callerTune.currentTime = 0;
        connectionChime.pause(); connectionChime.currentTime = 0;
        clearInterval(timerInterval);
        seconds = 0;
        if (workletNode) workletNode.port.close();
        if (mediaStream) mediaStream.getTracks().forEach(track => track.stop());
        if (audioContext && audioContext.state !== 'closed') audioContext.close();
        if (socket && socket.readyState !== WebSocket.CLOSED) socket.close();
        if (audioElement && audioElement.src) URL.revokeObjectURL(audioElement.src);
        audioQueue = [], isAiSpeaking = false;
        stopAiSpeakingAnimation();
        showScreen('contact-screen');
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
    const updateMuteButton = () => {
        if (isMuted) {
            muteBtn.innerHTML = `<i class="fas fa-microphone"></i> Unmute`;
        } else {
            muteBtn.innerHTML = `<i class="fas fa-microphone-slash"></i> Mute`;
        }
    };
    const toggleMute = () => {
        isMuted = !isMuted;
        updateMuteButton();
        updateStatusIndicator(isAiSpeaking ? 'speaking' : 'listening');
    };

    callTaaraBtn.addEventListener('click', () => startCall('Taara'));
    callVeerBtn.addEventListener('click', () => showScreen('not-available-screen'));
    goBackBtn.addEventListener('click', () => showScreen('contact-screen'));
    endCallBtn.addEventListener('click', () => endCall());
    muteBtn.addEventListener('click', toggleMute);
});