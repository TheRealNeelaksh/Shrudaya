document.addEventListener('DOMContentLoaded', () => {
    // Screen elements
    const contactScreen = document.getElementById('contact-screen');
    const loadingScreen = document.getElementById('loading-screen');
    const callScreen = document.getElementById('call-screen');
    const screens = [contactScreen, loadingScreen, callScreen];

    // Button elements
    const calltaaraBtn = document.getElementById('call-taara');
    const callveerBtn = document.getElementById('call-veer');
    const endCallBtn = document.getElementById('end-call-btn');
    const unmuteBtn = document.getElementById('unmute-btn');

    // Dynamic text elements
    const loadingText = document.getElementById('loading-text');
    const callName = document.getElementById('call-name');
    const callTimer = document.getElementById('call-timer');

    // State variables
    let timerInterval;
    let seconds = 0;
    let isMuted = true;

    // --- Functions ---

    function showScreen(screenToShow) {
        // Hide all screens by removing the 'active' class
        screens.forEach(screen => {
            screen.classList.remove('active');
        });

        // Show the target screen by adding the 'active' class
        screenToShow.classList.add('active');
    }

    function startCall(contact) {
        // 1. Show loading screen
        loadingText.textContent = `Connecting to ${contact}...`;
        showScreen(loadingScreen);

        // 2. Simulate connection delay (2.5 seconds)
        setTimeout(() => {
            // 3. Switch to call screen
            callName.textContent = contact;
            showScreen(callScreen);
            
            // 4. Start the call timer
            startTimer();
        }, 2500);
    }

    function endCall() {
        // 1. Stop the timer
        clearInterval(timerInterval);
        
        // 2. Reset timer and state
        seconds = 0;
        callTimer.textContent = '00:00';
        isMuted = true; // Reset mute state
        updateMuteButton();
        
        // 3. Show contact screen
        showScreen(contactScreen);
    }

    function startTimer() {
        timerInterval = setInterval(() => {
            seconds++;
            const mins = Math.floor(seconds / 60).toString().padStart(2, '0');
            const secs = (seconds % 60).toString().padStart(2, '0');
            callTimer.textContent = `${mins}:${secs}`;
        }, 1000);
    }

    function toggleMute() {
        isMuted = !isMuted;
        updateMuteButton();
    }

    function updateMuteButton() {
        if (isMuted) {
            unmuteBtn.innerHTML = `<i class="fas fa-microphone-slash"></i> Unmute`;
        } else {
            unmuteBtn.innerHTML = `<i class="fas fa-microphone"></i> Mute`;
        }
    }


    // --- Event Listeners ---
    
    calltaaraBtn.addEventListener('click', () => startCall('taara'));
    callveerBtn.addEventListener('click', () => startCall('veer'));
    endCallBtn.addEventListener('click', endCall);
    unmuteBtn.addEventListener('click', toggleMute);

    // --- Initial State ---

    // Initially show the contact screen when the page loads
    showScreen(contactScreen);
});