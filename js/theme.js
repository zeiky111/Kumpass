/* KUMPAS - Shared theme engine (Light / Dark / Auto) */
(function () {
  var STORAGE_KEY = 'kumpasTheme';
  var media = window.matchMedia ? window.matchMedia('(prefers-color-scheme: dark)') : null;

  function getStoredPreference() {
    try {
      return localStorage.getItem(STORAGE_KEY) || 'auto';
    } catch (_) {
      return 'auto';
    }
  }

  function resolveTheme(preference) {
    if (preference === 'dark' || preference === 'light') return preference;
    return media && media.matches ? 'dark' : 'light';
  }

  function applyTheme(preference) {
    var resolved = resolveTheme(preference);
    document.documentElement.setAttribute('data-theme', resolved);
    document.documentElement.setAttribute('data-theme-pref', preference);
  }

  function setThemePreference(preference) {
    var next = ['light', 'dark', 'auto'].indexOf(preference) === -1 ? 'auto' : preference;
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch (_) { /* ignore storage errors */ }
    applyTheme(next);
  }

  // Apply immediately (before paint) to avoid a flash of the wrong theme.
  applyTheme(getStoredPreference());

  if (media) {
    var handleSystemChange = function () {
      if (getStoredPreference() === 'auto') applyTheme('auto');
    };
    if (typeof media.addEventListener === 'function') {
      media.addEventListener('change', handleSystemChange);
    } else if (typeof media.addListener === 'function') {
      media.addListener(handleSystemChange);
    }
  }

  window.addEventListener('storage', function (event) {
    if (event.key === STORAGE_KEY) applyTheme(getStoredPreference());
  });

  window.KumpasTheme = {
    get: getStoredPreference,
    set: setThemePreference,
    resolved: function () { return resolveTheme(getStoredPreference()); }
  };
})();
