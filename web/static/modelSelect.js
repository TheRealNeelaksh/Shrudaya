document.addEventListener('DOMContentLoaded', () => {
    // --- THEME SWITCHER LOGIC ---
    const themeToggle = document.getElementById('theme-toggle');
    const body = document.body;

    // Function to apply the saved theme on page load
    const applySavedTheme = () => {
        const savedTheme = localStorage.getItem('theme');
        if (savedTheme === 'dark') {
            body.dataset.theme = 'dark';
            themeToggle.checked = true;
        } else {
            body.dataset.theme = 'light';
            themeToggle.checked = false;
        }
    };

    // Event listener for the toggle switch
    themeToggle.addEventListener('change', () => {
        if (themeToggle.checked) {
            body.dataset.theme = 'dark';
            localStorage.setItem('theme', 'dark');
        } else {
            body.dataset.theme = 'light';
            localStorage.setItem('theme', 'light');
        }
    });

    // Apply the theme when the page loads
    applySavedTheme();


    // --- MODEL SELECTION LOGIC ---
    const accessButtons = document.querySelectorAll('.access-button');

    accessButtons.forEach(button => {
        button.addEventListener('click', (event) => {
            const modelName = event.target.dataset.model;
            alert(`Accessing the ${modelName} model...`);
            // Example for next step:
            // window.location.href = `/chat?model=${modelName.toLowerCase()}`;
        });
    });
});