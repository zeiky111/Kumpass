// Resolves the backend API base URL for the whole frontend.
//
// The deployed frontend (kumpass-frontend.onrender.com) and backend
// (kumpass.onrender.com) are different subdomains, so a session cookie set
// by the backend is a *third-party* cookie from the frontend's point of
// view (onrender.com subdomains are each their own "site" on the public
// suffix list). Many browsers block third-party cookies by default, which
// made login silently fail: the cookie never actually got stored, so the
// very next request looked logged-out and bounced back to the login page.
//
// Fix: on the deployed frontend, call the same-origin "/api" path instead
// of the backend's own domain. Render's _redirects file (repo root)
// transparently proxies "/api/*" to the real backend, so the browser only
// ever talks to kumpass-frontend.onrender.com and the session cookie is
// set as first-party. Local/dev origins keep talking to the backend
// directly, since there's no proxy configured for them.
window.KUMPAS_API_BASE = (function () {
    const stored = localStorage.getItem('kumpasApiBase');
    if (stored) return stored;
    if (window.location.hostname === 'kumpass-frontend.onrender.com') {
        return '/api';
    }
    return 'https://kumpass.onrender.com/api';
})();
