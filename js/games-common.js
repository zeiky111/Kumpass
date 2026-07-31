// Shared engine used by all four game pages (sign-match, typing, sentence, scenario).
// Centralizes: API base, auth check, navbar dropdown wiring, shuffle, the
// difficulty-gating/level-progression state machine, the "How to Play"
// instructions modal, and the end-of-game completion panel.
//
// js/game-preview.js relies on getActivePool/canSelectDifficulty/setDifficulty/
// switchDifficulty being globals and .difficulty-btn[data-level] existing in the
// DOM -- that contract is preserved here.
(function () {
  const API_BASE = localStorage.getItem('kumpasApiBase') || 'https://kumpass.onrender.com/api';
  window.KumpasGames = window.KumpasGames || {};
  window.KumpasGames.API_BASE = API_BASE;

  // ---- Auth check (session cookie) ----
  (async function () {
    try {
      const response = await fetch(`${API_BASE}/auth/me/`, { method: 'GET', credentials: 'include' });
      if (!response.ok) window.location.replace('login.html');
    } catch (_) {
      window.location.replace('login.html');
    }
  })();

  // ---- Certificates ----
  // Called once a game's engine.advance() returns 'game-complete' (i.e. Hard
  // difficulty's last level was just finished). The backend is idempotent
  // (one UserCertificate per user+game), so this is safe to call every time
  // a player finishes Hard, even on replays -- it only issues once and the
  // rest are silent no-ops. Fire-and-forget: never blocks the completion UI.
  async function awardCertificateIfEarned(gameKey) {
    try {
      const currentUser = window.KumpasPortal && typeof window.KumpasPortal.ensureCurrentUser === 'function'
        ? await window.KumpasPortal.ensureCurrentUser()
        : null;
      const email = currentUser && currentUser.email;
      if (!email) return null;

      const response = await fetch(`${API_BASE}/certificates/award/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ email, game_key: gameKey }),
      });
      if (!response.ok) return null;
      return await response.json();
    } catch (_) {
      return null;
    }
  }
  window.KumpasGames.awardCertificateIfEarned = awardCertificateIfEarned;

  // ---- Navbar dropdown ----
  function wireNavbar() {
    const toggle = document.getElementById('navUserToggle');
    const dropdown = document.getElementById('navUserDropdown');
    if (toggle && dropdown) {
      toggle.addEventListener('click', function (e) { e.stopPropagation(); dropdown.classList.toggle('open'); });
      document.addEventListener('click', function () { dropdown.classList.remove('open'); });
    }
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', wireNavbar);
  } else {
    wireNavbar();
  }

  // ---- Small utilities ----
  function shuffle(array) {
    return array
      .map(value => ({ value, sort: Math.random() }))
      .sort((a, b) => a.sort - b.sort)
      .map(item => item.value);
  }

  function normalizeText(value) {
    return String(value == null ? '' : value)
      .toLowerCase()
      .replace(/[^a-z0-9\s]/g, '')
      .replace(/\s+/g, ' ')
      .trim();
  }

  function videoMimeType(url) {
    const clean = String(url || '').split('?')[0].toLowerCase();
    if (clean.endsWith('.mov')) return 'video/quicktime';
    if (clean.endsWith('.webm')) return 'video/webm';
    return 'video/mp4';
  }

  function buildVideoElement(src, className = 'sign-video') {
    const video = document.createElement('video');
    video.className = className;
    video.controls = true;
    video.playsInline = true;
    video.preload = 'metadata';
    video.muted = true;

    const source = document.createElement('source');
    source.src = src;
    source.type = videoMimeType(src);
    video.appendChild(source);
    return video;
  }

  function clearMediaContainer(container) {
    if (!container) return;
    container.querySelectorAll('video').forEach(video => {
      try { video.pause(); } catch (_) {}
      video.querySelectorAll('source').forEach(source => source.removeAttribute('src'));
      video.removeAttribute('src');
      try { video.load(); } catch (_) {}
    });
    container.replaceChildren();
  }

  function replaceVideoContent(container, src, className = 'sign-video') {
    if (!container) return null;
    clearMediaContainer(container);
    if (!src) return null;
    const video = buildVideoElement(src, className);
    container.appendChild(video);
    return video;
  }

  // Per-question countdown used by the "Hard" difficulty of games that carry
  // a time-pressure mechanic. onTick(secondsLeft) and onExpire() are called
  // from a 1s interval; call .stop() to cancel (e.g. once the player answers).
  function createCountdown(seconds, onTick, onExpire) {
    let remaining = seconds;
    let handle = null;
    function stop() {
      if (handle) {
        clearInterval(handle);
        handle = null;
      }
    }
    function start() {
      stop();
      remaining = seconds;
      if (typeof onTick === 'function') onTick(remaining);
      handle = setInterval(() => {
        remaining -= 1;
        if (typeof onTick === 'function') onTick(Math.max(0, remaining));
        if (remaining <= 0) {
          stop();
          if (typeof onExpire === 'function') onExpire();
        }
      }, 1000);
    }
    return { start, stop };
  }

  window.KumpasGames.createCountdown = createCountdown;

  async function loadGameLevels(gameKey) {
    try {
      const response = await fetch(`${API_BASE}/games/${gameKey}/levels/`);
      if (!response.ok) return [];
      const levels = await response.json();
      return levels
        .slice()
        .sort((a, b) => a.level_number - b.level_number);
    } catch (error) {
      console.error('Failed to load teacher-configured levels:', error);
      return [];
    }
  }

  // Groups raw GameLevel records (with .items) into { easy: [GameLevel...], ... }
  // ordered by level_number, mapping each item through mapItem(item) and
  // dropping levels that end up with no usable content.
  function buildLevelsByDifficulty(levels, mapItem) {
    const byDifficulty = { easy: [], medium: [], hard: [] };
    levels.forEach(level => {
      const items = (level.items || [])
        .map(mapItem)
        .filter(item => item != null);
      if (!items.length) return;
      if (!byDifficulty[level.difficulty]) byDifficulty[level.difficulty] = [];
      byDifficulty[level.difficulty].push({
        levelNumber: level.level_number,
        title: level.title || '',
        items,
      });
    });
    return byDifficulty;
  }

  // ---- Modal helpers (site-wide .modal / .modal-content pattern) ----
  function openModal(modalId) {
    const el = document.getElementById(modalId);
    if (el) el.classList.add('active');
  }

  function closeModal(modalId) {
    const el = document.getElementById(modalId);
    if (el) el.classList.remove('active');
  }

  window.KumpasGames.openModal = openModal;
  window.KumpasGames.closeModal = closeModal;

  // Builds and injects the "How to Play" modal + a hidden completion modal.
  // config: { gameKey, title, icon, objective, howToPlay: [..], scoring: [..],
  //           levelsByDifficulty: {easy,medium,hard} counts, onStart: fn }
  function initInstructionsModal(config) {
    const levelCounts = config.levelCounts || { easy: '-', medium: '-', hard: '-' };
    const howToPlayItems = (config.howToPlay || []).map(line => `<li>${line}</li>`).join('');
    const scoringItems = (config.scoring || []).map(line => `<li>${line}</li>`).join('');

    const modalHtml = `
      <div id="howToPlayModal" class="modal active" role="dialog" aria-modal="true" aria-labelledby="howToPlayTitle">
        <div class="modal-content game-instructions-content">
          <div class="modal-header">
            <h2 id="howToPlayTitle">${config.icon || ''} ${config.title}</h2>
            <button type="button" class="modal-close" aria-label="Close" onclick="KumpasGames.closeModal('howToPlayModal')">&times;</button>
          </div>
          <div class="game-instructions-body">
            <h3>Objective</h3>
            <p>${config.objective || ''}</p>
            <h3>How to Play</h3>
            <ul>${howToPlayItems}</ul>
            <h3>Scoring</h3>
            <ul>${scoringItems}</ul>
            <h3>Levels per Difficulty</h3>
            <div class="game-instructions-levels">
              <div class="level-pill"><span>Easy</span><strong>${levelCounts.easy}</strong></div>
              <div class="level-pill"><span>Medium</span><strong>${levelCounts.medium}</strong></div>
              <div class="level-pill"><span>Hard</span><strong>${levelCounts.hard}</strong></div>
            </div>
          </div>
          <div class="button-group" style="margin-top:22px;">
            <button type="button" class="btn btn-primary" id="startGameBtn">Start Game</button>
          </div>
        </div>
      </div>`;

    document.body.insertAdjacentHTML('beforeend', modalHtml);

    let started = false;
    function start() {
      if (started) return;
      started = true;
      closeModal('howToPlayModal');
      if (typeof config.onStart === 'function') config.onStart();
    }

    document.getElementById('startGameBtn').addEventListener('click', start);
    // Closing via the X or backdrop also starts the game -- the instructions
    // are informational, not a hard gate.
    document.getElementById('howToPlayModal').addEventListener('click', function (e) {
      if (e.target.id === 'howToPlayModal') start();
    });
  }

  // Shows an in-page "Difficulty/Game Complete" panel instead of a jarring alert().
  function showCompletionModal({ title, message, onContinue, continueLabel, autoContinueAfterMs = 0 }) {
    let modal = document.getElementById('gameCompleteModal');
    if (!modal) {
      document.body.insertAdjacentHTML('beforeend', `
        <div id="gameCompleteModal" class="modal" role="dialog" aria-modal="true">
          <div class="modal-content">
            <div class="modal-header">
              <h2 id="gameCompleteTitle">Great job!</h2>
              <button type="button" class="modal-close" aria-label="Close" onclick="KumpasGames.closeModal('gameCompleteModal')">&times;</button>
            </div>
            <p id="gameCompleteMessage"></p>
            <div class="button-group" style="margin-top:18px;">
              <button type="button" class="btn btn-primary" id="gameCompleteContinueBtn">Continue</button>
            </div>
          </div>
        </div>`);
      modal = document.getElementById('gameCompleteModal');
    }
    document.getElementById('gameCompleteTitle').textContent = title || 'Great job!';
    document.getElementById('gameCompleteMessage').textContent = message || '';
    const btn = document.getElementById('gameCompleteContinueBtn');
    btn.textContent = continueLabel || 'Continue';
    const newBtn = btn.cloneNode(true);
    btn.parentNode.replaceChild(newBtn, btn);
    let completed = false;
    const completeNow = () => {
      if (completed) return;
      completed = true;
      if (window.KumpasGames._completionTimer) {
        clearTimeout(window.KumpasGames._completionTimer);
        window.KumpasGames._completionTimer = null;
      }
      closeModal('gameCompleteModal');
      if (typeof onContinue === 'function') onContinue();
    };
    newBtn.addEventListener('click', completeNow);

    if (window.KumpasGames._completionTimer) {
      clearTimeout(window.KumpasGames._completionTimer);
      window.KumpasGames._completionTimer = null;
    }
    if (autoContinueAfterMs > 0) {
      window.KumpasGames._completionTimer = setTimeout(() => {
        window.KumpasGames._completionTimer = null;
        completeNow();
      }, autoContinueAfterMs);
    }
    openModal('gameCompleteModal');
  }

  window.KumpasGames.showCompletionModal = showCompletionModal;

  // ---- Difficulty / level engine ----
  // Creates a self-contained state machine each game page instantiates once.
  // choiceCounts: { easy, medium, hard } -- number of answer choices per difficulty.
  function createGameEngine(opts) {
    const state = {
      difficulty: 'easy',
      levelIndex: 0, // index into levelsByDifficulty[difficulty] (a teacher level)
      questionIndex: 0, // index into the current level's question/item list
      score: 0,
      correct: 0,
      total: 0,
      completedDifficulties: { easy: false, medium: false, hard: false },
      levelsByDifficulty: { easy: [], medium: [], hard: [] },
    };

    // All playable content comes from teacher-authored GameLevel rows -- no
    // default/fallback pool. A difficulty with zero published levels simply
    // has nothing to play (see hasNextLevel/totalLevelsForDifficulty below).
    function activeLevelList() {
      const list = state.levelsByDifficulty[state.difficulty] || [];
      return list.length ? list : null;
    }

    // Returns the flat list of playable items for "right now": the current
    // teacher level's items within this difficulty.
    function getActivePool() {
      const levels = activeLevelList();
      if (!levels) return [];
      const level = levels[Math.min(state.levelIndex, levels.length - 1)];
      return level ? level.items : [];
    }

    function currentLevelNumber() {
      const levels = activeLevelList();
      if (levels) {
        const level = levels[Math.min(state.levelIndex, levels.length - 1)];
        return level ? level.levelNumber : state.levelIndex + 1;
      }
      return state.levelIndex + 1;
    }

    function totalLevelsForDifficulty(difficulty) {
      const list = state.levelsByDifficulty[difficulty];
      return (list && list.length) ? list.length : null; // null = nothing published for this difficulty
    }

    function getChoiceCount() {
      const base = opts.choiceCounts[state.difficulty] || 4;
      const pool = getActivePool();
      return Math.max(2, Math.min(pool.length, base));
    }

    function getPointValue() {
      const base = opts.pointBase[state.difficulty] || 10;
      return base + currentLevelNumber();
    }

    function canSelectDifficulty(level) {
      if (level === 'easy') return true;
      if (level === 'medium') return state.completedDifficulties.easy;
      if (level === 'hard') return state.completedDifficulties.medium;
      return false;
    }

    function updateDifficultyButtons() {
      document.querySelectorAll('.difficulty-btn').forEach(btn => {
        const level = btn.dataset.level;
        const allowed = canSelectDifficulty(level);
        btn.disabled = !allowed;
        btn.classList.toggle('locked', !allowed);
      });
    }

    function markDifficultyCompleted(level) {
      if (!state.completedDifficulties[level]) {
        state.completedDifficulties[level] = true;
        updateDifficultyButtons();
      }
    }

    // Builds the question set for the CURRENT level within the active
    // difficulty (teacher-level content used in full, in the order authored;
    // shuffled only if the level has more items than the difficulty needs).
    function buildQuestionsForCurrentLevel() {
      const pool = getActivePool().slice();
      return shuffle(pool).slice(0, Math.max(1, pool.length));
    }

    function hasNextLevel() {
      const levels = activeLevelList();
      if (levels) return state.levelIndex + 1 < levels.length;
      return false; // nothing playable at all for this difficulty
    }

    // Called when the player finishes all questions in the current level.
    // Returns 'next-level' | 'next-difficulty' | 'game-complete'.
    function advance() {
      if (hasNextLevel()) {
        state.levelIndex += 1;
        return 'next-level';
      }
      if (state.difficulty === 'easy' || state.difficulty === 'medium') {
        markDifficultyCompleted(state.difficulty);
        return 'next-difficulty';
      }
      state.completedDifficulties = { easy: true, medium: true, hard: true };
      return 'game-complete';
    }

    function setDifficulty(level, resetScore) {
      state.difficulty = level;
      state.levelIndex = 0;
      document.querySelectorAll('.difficulty-btn').forEach(btn => btn.classList.remove('selected'));
      const btn = document.querySelector(`.difficulty-btn[data-level="${level}"]`);
      if (btn) btn.classList.add('selected');
      if (resetScore) {
        state.score = 0;
        state.correct = 0;
      }
      updateDifficultyButtons();
    }

    return {
      state,
      shuffle,
      normalizeText,
      videoMimeType,
      getActivePool,
      currentLevelNumber,
      totalLevelsForDifficulty,
      getChoiceCount,
      getPointValue,
      canSelectDifficulty,
      updateDifficultyButtons,
      markDifficultyCompleted,
      buildQuestionsForCurrentLevel,
      hasNextLevel,
      advance,
      setDifficulty,
    };
  }

  window.KumpasGames.shuffle = shuffle;
  window.KumpasGames.normalizeText = normalizeText;
  window.KumpasGames.videoMimeType = videoMimeType;
  window.KumpasGames.loadGameLevels = loadGameLevels;
  window.KumpasGames.buildLevelsByDifficulty = buildLevelsByDifficulty;
  window.KumpasGames.initInstructionsModal = initInstructionsModal;
  window.KumpasGames.buildVideoElement = buildVideoElement;
  window.KumpasGames.clearMediaContainer = clearMediaContainer;
  window.KumpasGames.replaceVideoContent = replaceVideoContent;
  window.KumpasGames.createGameEngine = createGameEngine;
})();
