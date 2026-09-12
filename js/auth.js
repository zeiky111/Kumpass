// Session-based authentication using HTTP-only cookies
const DEFAULT_API_BASE = localStorage.getItem('kumpasApiBase') || 'https://kumpass.onrender.com/api';

function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) {
        return parts.pop().split(';').shift();
    }
    return '';
}

// Render's free tier spins the backend down after ~15 minutes idle, so the
// first request after a while can hit a cold start and fail to connect
// before the dyno finishes waking up. Retrying a couple times with a short
// delay covers that window instead of surfacing a hard failure immediately.
async function fetchWithRetry(url, options, attempts = 3, delayMs = 4000) {
    let lastError;
    for (let i = 0; i < attempts; i++) {
        try {
            return await fetch(url, options);
        } catch (error) {
            lastError = error;
            if (i < attempts - 1) {
                await new Promise(resolve => setTimeout(resolve, delayMs));
            }
        }
    }
    throw lastError;
}

async function ensureCsrfToken(base = DEFAULT_API_BASE) {
    const existingToken = getCookie('csrftoken');
    if (existingToken) {
        return existingToken;
    }

    try {
        const response = await fetchWithRetry(`${base}/auth/csrf/`, {
            method: 'GET',
            credentials: 'include'
        });
        // Some browsers (Safari ITP, cross-site cookie blocking) drop the
        // csrftoken cookie even though the request succeeds, so fall back to
        // the token in the JSON body -- the backend returns both for this reason.
        const cookieToken = getCookie('csrftoken');
        if (cookieToken) {
            return cookieToken;
        }
        const data = await response.json().catch(() => ({}));
        return data.csrfToken || '';
    } catch (_) {
        return '';
    }
}

// Check if user is authenticated with the backend
async function isUserAuthenticated() {
    try {
        const response = await fetchWithRetry(`${DEFAULT_API_BASE}/auth/me/`, {
            method: 'GET',
            credentials: 'include' // Important: send cookies
        });
        return response.ok;
    } catch (_) {
        return false;
    }
}

// Get current user from backend session
async function getCurrentUser() {
    try {
        const response = await fetchWithRetry(`${DEFAULT_API_BASE}/auth/me/`, {
            method: 'GET',
            credentials: 'include'
        });
        if (!response.ok) return null;
        const data = await response.json();
        return data.user || null;
    } catch (_) {
        return null;
    }
}

// Require authentication on protected pages
async function requireAuth() {
    const isAuth = await isUserAuthenticated();
    if (!isAuth) {
        window.location.replace('login.html');
        return false;
    }
    return true;
}

// Logout user
async function logoutUser() {
    try {
        await fetch(`${DEFAULT_API_BASE}/auth/logout/`, {
            method: 'POST',
            credentials: 'include'
        });
    } catch (_) {
        // Continue logout even if request fails
    }
    window.location.replace('index.html');
}

// Every dashboard/portal page links "Logout" as a plain <a class="logout"
// href="index.html">, which only navigates and never actually ends the
// Django session server-side. Intercept those clicks everywhere so logout
// really terminates the session instead of just leaving the page.
document.addEventListener('click', function(event) {
    const logoutLink = event.target.closest('a.logout');
    if (!logoutLink) return;
    event.preventDefault();
    logoutUser();
});

// Login and Registration Form Handler
document.addEventListener('DOMContentLoaded', function() {
    const API_BASE = DEFAULT_API_BASE;

    function getUrl(path, base = API_BASE) {
        return `${base.replace(/\/$/, '')}${path}`;
    }

    async function postJson(path, payload, base = API_BASE) {
        let response;
        try {
            const csrfToken = await ensureCsrfToken(base);
            response = await fetchWithRetry(getUrl(path, base), {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...(csrfToken ? { 'X-CSRFToken': csrfToken } : {})
                },
                credentials: 'include', // Important: send and receive cookies
                body: JSON.stringify(payload)
            });
        } catch (error) {
            throw new Error('We could not reach the server. It may still be waking up -- please wait a few seconds and try again.');
        }

        let data = {};
        let responseText = '';
        try {
            responseText = await response.text();
            if (responseText) {
                try {
                    data = JSON.parse(responseText);
                } catch (_) {
                    data = {};
                }
            }
        } catch (_) {
            data = {};
        }

        if (!response.ok) {
            let message = data.error || data.detail || responseText || `Request failed (${response.status})`;
            if (typeof message === 'object') {
                message = Object.values(message).flat().join(' ');
            }
            const error = new Error(message);
            error.status = response.status;
            error.data = data;
            throw error;
        }

        return data;
    }

    // Handle registration form submission
    const registerForm = document.getElementById('registerForm');
    const yearLevelSelect = document.getElementById('yearLevel');

    function sanitizeNamePart(value) {
        return String(value || '')
            .replace(/[<>]/g, '')
            .replace(/\s+/g, ' ')
            .trim()
            .split(' ')
            .filter(Boolean)
            .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
            .join(' ');
    }
    
    function setButtonLoading(form, loadingText) {
        const button = form.querySelector('button[type="submit"]');
        if (!button) return () => {};
        const originalHtml = button.innerHTML;
        button.disabled = true;
        button.innerHTML = `<i class="fas fa-spinner fa-spin"></i> ${loadingText}`;
        return () => {
            button.disabled = false;
            button.innerHTML = originalHtml;
        };
    }

    if (registerForm) {
        registerForm.addEventListener('submit', async function(e) {
            e.preventDefault();

            const firstName = sanitizeNamePart(document.getElementById('firstName').value);
            const middleName = sanitizeNamePart(document.getElementById('middleName').value);
            const lastName = sanitizeNamePart(document.getElementById('lastName').value);
            const suffix = sanitizeNamePart(document.getElementById('suffix').value);
            const email = String(document.getElementById('email').value || '').trim().toLowerCase();
            const yearLevel = yearLevelSelect ? String(yearLevelSelect.value || '').trim() : '';
            const password = document.getElementById('password').value;
            const confirmPassword = document.getElementById('confirmPassword').value;
            
            // Validation
            if (!firstName || !lastName || !email || !password || !confirmPassword) {
                alert('Please fill in all required fields');
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
            
            const restoreButton = setButtonLoading(registerForm, 'Creating account...');
            try {
                const result = await postJson('/auth/signup/', {
                    firstName,
                    middleName,
                    lastName,
                    suffix,
                    email,
                    yearLevel,
                    password,
                    confirmPassword
                });

                if (result.error && result.error !== 'email_delivery_failed') {
                    throw new Error(result.message || result.error || 'Registration failed');
                }

                const redirectTarget = new URL(result.redirect || 'verify-email.html', window.location.href).href;
                let message = result.message || 'Registration successful! A verification code was sent to your email.';
                if (result.warning === 'email_delivery_failed' || result.error === 'email_delivery_failed') {
                    message = 'Your account was created, but we could not send the verification email automatically. Please use the verification page to resend the code.';
                }
                alert(`${message}\nYou will be redirected to the verification page.`);
                window.location.replace(redirectTarget);
            } catch (error) {
                restoreButton();
                const errorMsg = error.message || 'Registration failed';
                alert(`Registration Error: ${errorMsg}\n\nPlease check your information and try again.`);
            }
        });
    }
    
    // Google Sign-In (Google Identity Services). Works for both login and
    // register pages: the backend finds-or-creates the account by email, so
    // the same button covers "sign up" and "sign in" with one flow.
    const googleSignInContainer = document.getElementById('googleSignInContainer');
    const configuredClientId = typeof GOOGLE_CLIENT_ID === 'string' ? GOOGLE_CLIENT_ID.trim() : '';

    async function handleGoogleCredentialResponse(googleResponse) {
        const credential = googleResponse && googleResponse.credential;
        if (!credential) return;
        try {
            const result = await postJson('/auth/google/', { credential });
            const redirectTarget = new URL(result.redirect || 'dashboard.html', window.location.href).href;
            window.location.replace(redirectTarget);
        } catch (error) {
            alert(`Google sign-in failed: ${error.message}`);
        }
    }

    if (googleSignInContainer) {
        if (!configuredClientId) {
            googleSignInContainer.style.display = 'none';
        } else {
            let initialized = false;

            // Google's button is a fixed-pixel-width iframe, not a responsive
            // element -- measure the form so it matches the width of the
            // inputs/submit button above/below it instead of floating as a
            // narrower, centered box. 400 is the widest size Google supports.
            const getButtonWidth = () => {
                // googleSignInContainer is a sibling of the form, not inside
                // it, so measure the form itself -- its parent (auth-form-container)
                // has its own padding and would overstate the available width.
                const authFormContainer = googleSignInContainer.closest('.auth-form-container');
                const reference = (authFormContainer && authFormContainer.querySelector('.auth-form')) || googleSignInContainer.parentElement;
                const measured = reference ? reference.getBoundingClientRect().width : 0;
                return Math.max(200, Math.min(400, Math.round(measured) || 320));
            };

            const renderGoogleButton = () => {
                if (!window.google || !window.google.accounts || !window.google.accounts.id) return false;
                if (!initialized) {
                    google.accounts.id.initialize({
                        client_id: configuredClientId,
                        callback: handleGoogleCredentialResponse,
                        auto_select: false
                    });
                    initialized = true;
                }
                googleSignInContainer.innerHTML = '';
                google.accounts.id.renderButton(googleSignInContainer, {
                    theme: 'outline',
                    size: 'large',
                    shape: 'rectangular',
                    text: 'continue_with',
                    width: getButtonWidth()
                });
                return true;
            };

            // The GIS script tag loads with async/defer, so it may not have
            // run yet when this handler fires -- poll briefly instead of
            // assuming it's ready.
            if (!renderGoogleButton()) {
                let attempts = 0;
                const poll = setInterval(() => {
                    attempts += 1;
                    if (renderGoogleButton() || attempts > 25) {
                        clearInterval(poll);
                    }
                }, 200);
            }

            // Re-render at the new width when the layout changes (e.g. the
            // window is resized across the mobile/desktop breakpoint).
            let resizeTimer;
            window.addEventListener('resize', () => {
                clearTimeout(resizeTimer);
                resizeTimer = setTimeout(renderGoogleButton, 200);
            });
        }
    }

    function setupPasswordToggles() {
        document.querySelectorAll('.password-toggle').forEach(toggle => {
            toggle.addEventListener('click', function() {
                const fieldContainer = this.closest('.password-field');
                if (!fieldContainer) return;
                const input = fieldContainer.querySelector('.form-input');
                if (!input) return;

                const isPassword = input.type === 'password';
                input.type = isPassword ? 'text' : 'password';
                const icon = this.querySelector('i');
                if (icon) {
                    icon.classList.toggle('fa-eye');
                    icon.classList.toggle('fa-eye-slash');
                }
                this.setAttribute('aria-label', isPassword ? 'Hide password' : 'Show password');
            });
        });
    }

    setupPasswordToggles();

    // Handle login form submission
    const loginForm = document.getElementById('loginForm');
    
    if (loginForm) {
        loginForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const loginId = String(document.getElementById('email').value || '').trim();
            const password = document.getElementById('password').value;

            if (!loginId || !password) {
                alert('Please enter your email/username and password.');
                return;
            }
            
            const restoreButton = setButtonLoading(loginForm, 'Signing in...');
            try {
                let result;
                try {
                    result = await postJson('/auth/login/', {
                        email: loginId,
                        password
                    });
                } catch (firstError) {
                    // If the stored API base is different from the default, retry
                    // using the default backend when the error indicates the stored
                    // API is unreachable or returned a 401 (account may exist on
                    // the default backend).
                    const msg = String(firstError && firstError.message || '');
                    const status = firstError && firstError.status;
                    const networkFailed = msg.includes('could not reach the server') || msg.includes('Failed to fetch') || msg.includes('NetworkError');
                    const shouldRetryWithDefault = API_BASE !== DEFAULT_API_BASE && (networkFailed || status === 401);
                    if (shouldRetryWithDefault) {
                        console.warn('Retrying login using default backend API base because stored API base failed:', msg || status);
                        result = await postJson('/auth/login/', {
                            email: loginId,
                            password
                        }, DEFAULT_API_BASE);
                    } else {
                        throw firstError;
                    }
                }

                const redirectTarget = new URL(result.redirect || 'dashboard.html', window.location.href).href;
                window.location.replace(redirectTarget);
            } catch (error) {
                restoreButton();
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
