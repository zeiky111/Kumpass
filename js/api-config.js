// Resolves the backend API base URL, and carries the bearer auth token.
//
// The frontend (kumpass-frontend.onrender.com) and backend
// (kumpass.onrender.com) are different subdomains, which browsers
// increasingly treat as cross-site for cookies -- third-party-cookie
// blocking (Safari, Firefox strict mode, Brave, and a growing share of
// Chrome) silently dropped the session cookie the backend used to rely on,
// so login would succeed, redirect to the dashboard, then immediately look
// logged-out on the very next request with no error shown. A token sent
// explicitly in the Authorization header isn't subject to any cookie
// policy, so it works the same regardless of how the two domains relate.
window.KUMPAS_API_BASE = localStorage.getItem('kumpasApiBase') || 'https://kumpass.onrender.com/api';

const KUMPAS_TOKEN_KEY = 'kumpasAuthToken';

window.getKumpasToken = function () {
    try {
        return localStorage.getItem(KUMPAS_TOKEN_KEY) || '';
    } catch (_) {
        return '';
    }
};

window.setKumpasToken = function (token) {
    try {
        if (token) {
            localStorage.setItem(KUMPAS_TOKEN_KEY, token);
        } else {
            localStorage.removeItem(KUMPAS_TOKEN_KEY);
        }
    } catch (_) {
        // Ignore storage failures (private browsing, quota, etc.)
    }
};

// Every authenticated call across the app already marks itself with
// `credentials: 'include'` -- a holdover from the cookie-based session flow.
// Reuse that exact marker to transparently attach the bearer token instead,
// so none of those call sites (spread across many pages and shared scripts)
// need to be rewritten individually.
//
// Public auth endpoints (login, Google sign-in, signup, verification,
// password reset) never get the token: they don't need one, and a stale
// token left in localStorage must never be able to block signing back in.
// Any 401 that says the caller isn't authenticated also clears the stored
// token, so a dead token can't linger and break later requests.
(function () {
    const nativeFetch = window.fetch.bind(window);
    const PUBLIC_AUTH_PATH = /\/auth\/(login|google|signup|csrf|verify-email|resend-verification|request-password-reset|resend-password-reset-code|reset-password)\/?(\?|$)/;

    window.fetch = function (input, init) {
        const token = window.getKumpasToken();
        const url = typeof input === 'string' ? input : (input && input.url) || '';
        const attachToken = Boolean(token && init && init.credentials === 'include' && !PUBLIC_AUTH_PATH.test(url));
        if (attachToken) {
            init = Object.assign({}, init, {
                headers: Object.assign({}, init.headers || {}, { Authorization: `Token ${token}` }),
            });
        }
        const request = nativeFetch(input, init);
        if (!attachToken) return request;

        return request.then((response) => {
            if (response.status === 401) {
                response.clone().json().then((data) => {
                    if (data && data.authenticated === false && window.getKumpasToken() === token) {
                        window.setKumpasToken(null);
                    }
                }).catch(() => {});
            }
            return response;
        });
    };
})();

// ---- No dead loading ----------------------------------------------------
// The backend runs on a free Render instance that sleeps when idle; the
// first request after that can take 30-60 seconds. Without feedback the
// app just looks frozen ("dead loading"). So, for every call to the API:
//   * GET requests time out after 45 s instead of hanging forever, so the
//     page's own error handling can run;
//   * if a request is still running after 3 s, a small notice explains the
//     server is waking up; it disappears when the requests finish;
//   * if the server can't be reached, the notice offers "Try again".
// Public pages (landing, login, register, ...) also wake the server up
// right away, so it is ready by the time the student has logged in.
(function () {
    const API = String(window.KUMPAS_API_BASE || '').replace(/\/$/, '');
    if (!API || typeof window.fetch !== 'function') return;

    const GET_TIMEOUT_MS = 45000;
    const SLOW_AFTER_MS = 3000;
    const baseFetch = window.fetch;
    let slowCount = 0;
    let toast = null;
    let toastKind = '';
    let hideTimer = null;

    function ensureToast() {
        if (toast && document.body && document.body.contains(toast)) return toast;
        if (!document.body) return null;
        toast = document.createElement('div');
        toast.id = 'kumpasNetNotice';
        toast.setAttribute('role', 'status');
        toast.setAttribute('aria-live', 'polite');
        // position/z-index are !important because css/bg-orbs.css forces
        // position:relative on every direct child of <body>.
        toast.style.cssText = [
            'position:fixed !important', 'left:50%', 'bottom:20px', 'transform:translateX(-50%)',
            'z-index:10080 !important', 'max-width:min(560px, calc(100vw - 32px))', 'display:none',
            'align-items:center', 'gap:10px', 'padding:12px 16px', 'border-radius:14px',
            'font:600 0.92rem/1.45 system-ui, -apple-system, "Segoe UI", sans-serif',
            'box-shadow:0 12px 30px rgba(15,23,42,0.28)', 'color:#fff',
        ].join(';');
        document.body.appendChild(toast);
        return toast;
    }

    function showToast(kind, html, autoHideMs) {
        const el = ensureToast();
        if (!el) return;
        clearTimeout(hideTimer);
        toastKind = kind;
        el.style.background = kind === 'error' ? '#b91c1c' : '#1e3a8a';
        el.innerHTML = html;
        el.style.display = 'flex';
        const retry = el.querySelector('[data-net-retry]');
        if (retry) retry.addEventListener('click', () => window.location.reload());
        if (autoHideMs) hideTimer = setTimeout(hideToast, autoHideMs);
    }

    function hideToast() {
        clearTimeout(hideTimer);
        toastKind = '';
        if (toast) toast.style.display = 'none';
    }

    function isApiCall(url) {
        // File views/downloads can be large; let them take as long as they need.
        return url.indexOf(API) === 0 && url.indexOf('/files/') === -1;
    }

    window.fetch = function (input, init) {
        const url = typeof input === 'string' ? input : (input && input.url) || '';
        if (!isApiCall(url)) return baseFetch(input, init);

        const method = String((init && init.method) || (input && input.method) || 'GET').toUpperCase();
        let timeoutId = null;
        let timedOut = false;
        if (method === 'GET' && !(init && init.signal) && typeof AbortController === 'function') {
            const controller = new AbortController();
            init = Object.assign({}, init, { signal: controller.signal });
            timeoutId = setTimeout(() => { timedOut = true; controller.abort(); }, GET_TIMEOUT_MS);
        }

        let isSlow = false;
        const slowTimer = setTimeout(() => {
            isSlow = true;
            slowCount += 1;
            if (toastKind !== 'error') {
                showToast('info', '<span aria-hidden="true">⏳</span><span>Connecting to the Kumpas server… The first load can take up to a minute while the server wakes up.</span>');
            }
        }, SLOW_AFTER_MS);

        const finish = () => {
            clearTimeout(timeoutId);
            clearTimeout(slowTimer);
            if (isSlow) {
                slowCount = Math.max(0, slowCount - 1);
                if (!slowCount && toastKind === 'info') hideToast();
            }
        };

        return baseFetch(input, init).then((response) => {
            finish();
            return response;
        }, (error) => {
            finish();
            // A caller cancelling its own request isn't a connection problem.
            if (timedOut || !(error && error.name === 'AbortError')) {
                showToast('error',
                    '<span aria-hidden="true">⚠️</span><span>Can\'t reach the Kumpas server right now. Check your internet connection.</span>'
                    + '<button type="button" data-net-retry style="flex:none;border:none;border-radius:999px;padding:6px 14px;font:inherit;cursor:pointer;background:#fff;color:#b91c1c;">Try again</button>',
                    15000);
            }
            throw error;
        });
    };

    // Wake the backend early on the public pages.
    const page = (window.location.pathname.split('/').pop() || 'index.html').toLowerCase();
    if (/^(index|login|register|forgot-password|reset-password|verify-email|verify-certificate)\.html$/.test(page)) {
        setTimeout(() => {
            baseFetch(`${API}/auth/csrf/`, { credentials: 'include', cache: 'no-store' }).catch(() => {});
        }, 0);
    }
})();
