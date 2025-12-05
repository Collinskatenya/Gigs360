document.addEventListener('DOMContentLoaded', () => {
    
    // 1. Get Stored Theme
    const getPreferredTheme = () => {
        const storedTheme = localStorage.getItem('theme');
        if (storedTheme) {
            return storedTheme;
        }
        return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    };

    // 2. Update Active State in Menu
    const updateActiveButton = (theme) => {
        document.querySelectorAll('[data-theme-value]').forEach(btn => {
            btn.classList.remove('active');
            if (btn.getAttribute('data-theme-value') === theme) {
                btn.classList.add('active');
            }
        });
        
        // Update Top Bar Icon text
        const btnIcon = document.querySelector('#themeSwitchBtn i');
        const btnText = document.querySelector('#themeSwitchBtn span');
        
        if (theme === 'dark') {
            btnIcon.className = 'bi bi-moon-stars-fill';
            if(btnText) btnText.textContent = 'Dark';
        } else if (theme === 'light') {
            btnIcon.className = 'bi bi-sun-fill';
            if(btnText) btnText.textContent = 'Light';
        } else {
            btnIcon.className = 'bi bi-circle-half';
            if(btnText) btnText.textContent = 'System';
        }
    };

    // 3. Apply Theme
    const setTheme = function (theme) {
        if (theme === 'auto' && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            document.documentElement.setAttribute('data-theme', 'dark');
        } else if (theme === 'auto') {
            document.documentElement.setAttribute('data-theme', 'light');
        } else {
            document.documentElement.setAttribute('data-theme', theme);
        }
        updateActiveButton(theme);
    };

    // Init
    const savedTheme = localStorage.getItem('theme') || 'auto';
    setTheme(savedTheme);
    updateActiveButton(savedTheme);

    // 4. Handle Click Events
    document.querySelectorAll('[data-theme-value]').forEach(btn => {
        btn.addEventListener('click', () => {
            const theme = btn.getAttribute('data-theme-value');
            localStorage.setItem('theme', theme);
            setTheme(theme);
        });
    });

    // 5. Listen for System Changes
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
        if (localStorage.getItem('theme') === 'auto' || !localStorage.getItem('theme')) {
            setTheme('auto');
        }
    });
});