document.addEventListener('DOMContentLoaded', () => {
    // --- UI ELEMENTS ---
    const loginTab = document.getElementById('login-tab');
    const signupTab = document.getElementById('signup-tab');
    const loginSection = document.getElementById('login-section');
    const signupSection = document.getElementById('signup-section');
    const signUpForm = document.getElementById('form-signup');
    const logInForm = document.getElementById('form-login');

    // --- SUPABASE CLIENT SETUP ---
    const { createClient } = supabase;
    const SUPABASE_URL = window.supabase_url;
    const SUPABASE_ANON_KEY = window.supabase_anon_key;

    if (!SUPABASE_URL || !SUPABASE_ANON_KEY) {
        showMessage('Error: Supabase credentials not found. Check .env file and server.', 'error', signupSection);
        showMessage('Error: Supabase credentials not found. Check .env file and server.', 'error', loginSection);
        return;
    }
    const supabaseClient = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

    // --- TAB SWITCHING LOGIC ---
    function showLogin() {
        loginTab.classList.add('active');
        signupTab.classList.remove('active');

        signupSection.style.opacity = '0';
        signupSection.style.pointerEvents = 'none';
        signupSection.style.transform = 'scale(0.98)';
        
        loginSection.style.opacity = '1';
        loginSection.style.pointerEvents = 'auto';
        loginSection.style.transform = 'scale(1)';
        clearMessages();
    }

    function showSignup() {
        loginTab.classList.remove('active');
        signupTab.classList.add('active');

        loginSection.style.opacity = '0';
        loginSection.style.pointerEvents = 'none';
        loginSection.style.transform = 'scale(0.98)';

        signupSection.style.opacity = '1';
        signupSection.style.pointerEvents = 'auto';
        signupSection.style.transform = 'scale(1)';
        clearMessages();
    }

    loginTab.addEventListener('click', showLogin);
    signupTab.addEventListener('click', showSignup);

    // --- SIGN UP LOGIC ---
    signUpForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const firstName = e.target.elements.firstName.value;
        const lastName = e.target.elements.lastName.value;
        const email = e.target.elements.email.value;
        const password = e.target.elements.password.value;
        const confirmPassword = e.target.elements.confirmPassword.value;
        const dob = e.target.elements.dob.value;

        if (password !== confirmPassword) {
            showMessage("Passwords do not match.", 'error', signupSection);
            return;
        }

        showMessage("Creating account...", 'loading', signupSection);

        const { data, error } = await supabaseClient.auth.signUp({
            email: email,
            password: password,
            options: {
                data: {
                    first_name: firstName,
                    last_name: lastName,
                    date_of_birth: dob
                }
            }
        });

        if (error) {
            showMessage(`Sign up error: ${error.message}`, 'error', signupSection);
        } else {
            showMessage("Success! Please check your email to confirm your account.", 'success', signupSection);
        }
    });

    // --- LOG IN LOGIC ---
    logInForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const email = e.target.elements.email.value;
        const password = e.target.elements.password.value;

        showMessage("Logging in...", 'loading', loginSection);

        const { data, error } = await supabaseClient.auth.signInWithPassword({
            email: email,
            password: password,
        });

        if (error) {
            showMessage(`Login error: ${error.message}`, 'error', loginSection);
        } else {
            showMessage("Login successful! Redirecting...", 'success', loginSection);
            setTimeout(() => {
                window.location.href = "/"; // Redirect to main app
            }, 1500);
        }
    });

    // --- HELPER FUNCTIONS ---
    function showMessage(text, type, parentElement) {
        const messageElement = parentElement.querySelector('.message');
        messageElement.textContent = text;
        if (type === 'error') {
            messageElement.style.color = '#f87171'; // Red
        } else if (type === 'success') {
            messageElement.style.color = '#4ade80'; // Green
        } else {
            messageElement.style.color = '#555'; // Dark text for loading
        }
    }

    function clearMessages() {
        document.querySelectorAll('.message').forEach(el => el.textContent = '');
    }

    // Initialize the view to show the Login form first
    showLogin();
});