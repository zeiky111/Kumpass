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
(function () {
    const nativeFetch = window.fetch.bind(window);
    window.fetch = function (input, init) {
        const token = window.getKumpasToken();
        if (token && init && init.credentials === 'include') {
            init = Object.assign({}, init, {
                headers: Object.assign({}, init.headers || {}, { Authorization: `Token ${token}` }),
            });
        }
        return nativeFetch(input, init);
    };
})();
