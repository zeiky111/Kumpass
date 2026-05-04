// Login and Registration Form Handler
document.addEventListener('DOMContentLoaded', function() {
    const API_BASE = localStorage.getItem('kumpasApiBase') || 'http://127.0.0.1:8000/api';

    async function postJson(path, payload) {
        const response = await fetch(`${API_BASE}${path}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        let data = {};
        try {
            data = await response.json();
        } catch (_) {
            data = {};
        }

        if (!response.ok) {
            let message = data.error || 'Request failed';
            if (typeof message === 'object') {
                message = Object.values(message).flat().join(' ');
            }
            throw new Error(message);
        }

        return data;
    }

    function saveCurrentUser(user) {
        localStorage.setItem('currentUser', JSON.stringify({
            name: user.name,
            email: user.email,
            yearLevel: user.yearLevel,
            role: user.role
        }));
    }

    // Handle registration form submission
    const registerForm = document.getElementById('registerForm');
    const yearLevelSelect = document.getElementById('yearLevel');

    function sanitizeName(value) {
        return String(value || '')
            .replace(/[<>]/g, '')
            .replace(/\s+/g, ' ')
            .trim();
    }
    
    if (registerForm) {
        registerForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const fullname = sanitizeName(document.getElementById('fullname').value);
            const email = String(document.getElementById('email').value || '').trim().toLowerCase();
            const yearLevel = yearLevelSelect ? String(yearLevelSelect.value || '').trim() : '';
            const password = document.getElementById('password').value;
            const confirmPassword = document.getElementById('confirmPassword').value;
            
            // Validation
            if (!fullname || !email || !password || !confirmPassword) {
                alert('Please fill in all fields');
                return;
            }

            if (!yearLevel) {
                alert('Please select your year level');
                return;
            }
            
            if (password.length < 8) {
                alert('Password must be at least 8 characters long');
                return;
            }
            
            if (password !== confirmPassword) {
                alert('Passwords do not match');
                return;
            }
            
            try {
                const result = await postJson('/auth/signup/', {
                    fullname,
                    email,
                    yearLevel,
                    password,
                    confirmPassword
                });

                saveCurrentUser(result.user);
                alert('Registration successful! Redirecting to your dashboard...');
                window.location.href = result.redirect || 'dashboard.html';
            } catch (error) {
                alert(`Signup failed: ${error.message}`);
            }
        });
    }
    
    // Handle Google signup button
    const googleBtns = document.querySelectorAll('.google-btn');
    googleBtns.forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            alert('Google Sign-in integration coming soon! Please use email registration for now.');
        });
    });
    
    // Handle login form submission
    const loginForm = document.getElementById('loginForm');
    
    if (loginForm) {
        loginForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const email = String(document.getElementById('email').value || '').trim().toLowerCase();
            const password = document.getElementById('password').value;
            
            try {
                const result = await postJson('/auth/login/', {
                    email,
                    password
                });

                saveCurrentUser(result.user);
                window.location.href = result.redirect || 'dashboard.html';
            } catch (error) {
                alert(`Login failed: ${error.message}`);
            }
        });
    }
    
    // Handle user menu dropdown
    const userMenuBtn = document.getElementById('userMenuBtn');
    const userDropdown = document.getElementById('userDropdown');
    
    if (userMenuBtn && userDropdown) {
        userMenuBtn.addEventListener('click', function() {
            userDropdown.classList.toggle('active');
        });
        
        // Close dropdown when clicking outside
        document.addEventListener('click', function(event) {
            if (!event.target.closest('.user-menu')) {
                userDropdown.classList.remove('active');
            }
        });
    }
    
    // Hamburger menu
    const hamburger = document.getElementById('hamburger');
    const navMenu = document.getElementById('navMenu');
    
    if (hamburger && navMenu) {
        hamburger.addEventListener('click', function() {
            navMenu.classList.toggle('active');
        });
    }
});

// Navigation between dashboard sections
function switchTab(tabName) {
    console.log('Switching to tab:', tabName);
    // This function would be used to show/hide different sections
}

// Modal functions
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('active');
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('active');
    }
}

// Close modal when clicking outside of it
document.addEventListener('click', function(event) {
    if (event.target.classList && event.target.classList.contains('modal')) {
        event.target.classList.remove('active');
    }
});
