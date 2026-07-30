// Lets the instructor dashboard open any game page in "preview mode" so a
// teacher can play a specific level (including unpublished drafts) exactly
// as a student would, without touching real student progress.
//
// Activated via ?previewLevelId=<id>&previewActor=<instructor email> in the
// game page URL. Each game page's own script still calls
// loadLevelPools(gameKey, mapItem) on boot; this file wraps window.fetch so
// that call transparently resolves to the single previewed level (instead of
// the public "all published levels for this game" endpoint), reusing each
// page's existing grouping/mapping logic untouched.
(function () {
  const params = new URLSearchParams(window.location.search);
  const previewLevelId = params.get('previewLevelId');
  if (!previewLevelId) return;

  const previewActor = params.get('previewActor') || '';
  const API_BASE = 'http://127.0.0.1:8000/api';

  window.KumpasGamePreview = {
    active: true,
    levelId: previewLevelId,
    level: null,
  };

  const originalFetch = window.fetch.bind(window);
  window.fetch = function (input, init) {
    const url = typeof input === 'string' ? input : (input && input.url) || '';
    if (url.includes('/api/games/')) {
      return originalFetch(
        `${API_BASE}/instructor/game-levels/${encodeURIComponent(previewLevelId)}/?actorEmail=${encodeURIComponent(previewActor)}`
      ).then(async response => {
        if (!response.ok) return new Response('[]', { status: 200 });
        const level = await response.json();
        window.KumpasGamePreview.level = level;
        // Mimic the public endpoint's shape: a list of levels for this game.
        return new Response(JSON.stringify([level]), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        });
      });
    }
    return originalFetch(input, init);
  };

  let bannerEl = null;

  function renderBanner(level) {
    if (bannerEl) {
      bannerEl.remove();
      document.body.style.paddingTop = '';
    }
    const banner = document.createElement('div');
    banner.style.cssText = [
      'position:fixed', 'top:0', 'left:0', 'right:0', 'z-index:9999',
      'background:linear-gradient(135deg,#1e3a8a 0%,#7c3aed 100%)',
      'color:#fff', 'padding:10px 16px', 'font-size:14px', 'font-weight:600',
      'display:flex', 'justify-content:center', 'align-items:center', 'gap:14px',
      'box-shadow:0 4px 14px rgba(15,23,42,0.25)',
    ].join(';');

    const statusLabel = level && level.is_published ? 'Published' : 'Draft';
    const label = document.createElement('span');
    label.textContent = level
      ? `🔍 Preview Mode — Level ${level.level_number} (${level.difficulty}) · ${statusLabel} · Progress will not be saved`
      : '🔍 Preview Mode — Progress will not be saved';
    banner.appendChild(label);

    const closeLink = document.createElement('a');
    closeLink.textContent = 'Close Preview';
    closeLink.href = 'javascript:window.close();';
    closeLink.onclick = function () {
      if (window.opener) {
        window.close();
      } else {
        window.location.href = 'instructor-dashboard.html#game-levels';
      }
      return false;
    };
    closeLink.style.cssText = 'color:#fff;text-decoration:underline;font-weight:700;';
    banner.appendChild(closeLink);

    document.body.prepend(banner);
    document.body.style.paddingTop = `${banner.offsetHeight}px`;
    bannerEl = banner;
  }

  function lockToPreviewDifficulty() {
    const level = window.KumpasGamePreview.level;
    if (!level) return;

    // Skip the "How to Play" modal in preview mode -- the teacher is already
    // familiar with the game and just wants to see the level's content.
    if (window.KumpasGames && typeof window.KumpasGames.closeModal === 'function') {
      window.KumpasGames.closeModal('howToPlayModal');
    }
    const startBtn = document.getElementById('startGameBtn');
    if (startBtn) startBtn.click();

    // Only the previewed level's difficulty is selectable; the other
    // difficulty buttons are hidden so the teacher can't wander into the
    // generic/default question pool for this game.
    document.querySelectorAll('.difficulty-btn').forEach(btn => {
      if (btn.dataset.level !== level.difficulty) {
        btn.style.display = 'none';
      }
    });

    if (typeof window.canSelectDifficulty === 'function') {
      window.canSelectDifficulty = function (lvl) { return lvl === level.difficulty; };
    }
    if (typeof window.setDifficulty === 'function') {
      const btn = document.querySelector(`.difficulty-btn[data-level="${level.difficulty}"]`);
      window.setDifficulty(level.difficulty, btn);
    } else if (typeof window.switchDifficulty === 'function') {
      window.switchDifficulty(level.difficulty, true);
    }

    // Items with missing/incomplete data (e.g. a sentence item with no
    // signs picked yet) are silently dropped by each game's own mapItem
    // filter. getActivePool() falls back to the generic default pool
    // whenever the previewed difficulty's pool is empty, so a non-empty
    // result here doesn't by itself prove the level's own content loaded —
    // we only use this to detect the "definitely nothing playable" case.
    const pool = typeof window.getActivePool === 'function' ? window.getActivePool() : [];
    if (!pool || !pool.length) {
      const warning = document.createElement('div');
      warning.style.cssText = 'position:fixed;top:52px;left:0;right:0;z-index:9998;background:#fef3c7;color:#92400e;padding:8px 16px;font-size:13px;text-align:center;font-weight:600;';
      warning.textContent = '⚠️ This level has no complete, playable content yet — showing the default question pool instead. Add valid content in "Manage Content" to preview the real level.';
      document.body.prepend(warning);
    }
  }

  function init() {
    // Banner renders immediately; difficulty lock waits for the page's own
    // boot Promise (loadLevelPools) to populate KumpasGamePreview.level.
    renderBanner(null);
    const waitForLevel = setInterval(() => {
      if (window.KumpasGamePreview.level) {
        clearInterval(waitForLevel);
        renderBanner(window.KumpasGamePreview.level);
        lockToPreviewDifficulty();
      }
    }, 150);
    setTimeout(() => clearInterval(waitForLevel), 10000);
  }

  // This script tag sits near the end of <body>, after it (and possibly the
  // whole document) has already parsed, so DOMContentLoaded may already have
  // fired by the time we'd attach a listener for it.
  if (document.readyState === 'loading') {
    window.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
