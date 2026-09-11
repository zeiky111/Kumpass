// Google Identity Services configuration.
//
// This client ID is public (it's meant to ship in frontend JS -- Google
// verifies sign-ins by checking the token signature, not by keeping this
// value secret), but it must match the GOOGLE_CLIENT_ID configured on the
// backend or /auth/google/ will reject every sign-in.
//
// To get one: https://console.cloud.google.com/apis/credentials
//   1. Create an OAuth 2.0 Client ID of type "Web application".
//   2. Under "Authorized JavaScript origins" add every origin this app is
//      served from (e.g. http://127.0.0.1:5500, https://kumpass-frontend.onrender.com).
//   3. Paste the resulting "....apps.googleusercontent.com" client ID below.
const GOOGLE_CLIENT_ID = '';
