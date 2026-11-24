// Shared engine used by all four game pages (sign-match, typing, sentence, scenario).
// Centralizes: API base, auth check, navbar dropdown wiring, shuffle, the
// difficulty-gating/level-progression state machine, the "How to Play"
// instructions modal, and the end-of-game completion panel.
//
// js/game-preview.js relies on getActivePool/canSelectDifficulty/setDifficulty/
// switchDifficulty being globals and .difficulty-btn[data-level] existing in the
// DOM -- that contract is preserved here.
(function () {
  const API_BASE = window.KUMPAS_API_BASE;
  window.KumpasGames = window.KumpasGames || {};
  window.KumpasGames.API_BASE = API_BASE;

  // Auth is checked by js/auth.js's requireAuth() near the top of <body> on
  // every game page, before this file loads -- not repeated here.

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

      const response = await window.fetchWithAuth(`${API_BASE}/certificates/award/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
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
  //
  // Pooling: a GameLevelItem can carry extra_data.pool -- a list of raw
  // alternative items ({prompt, media_url, extra_data}) sharing the same
  // shape as a GameLevelItem. Each pool entry is mapped through mapItem() up
  // front (here) and attached to the mapped item as `_pool`, so the level
  // *slot* itself doesn't change (same level_number/title/count), but which
  // WORD fills that slot can be redrawn from the pool on each playthrough --
  // see createGameEngine's buildQuestionsForCurrentLevel/pickFromPool.
  function buildLevelsByDifficulty(levels, mapItem) {
    const byDifficulty = { easy: [], medium: [], hard: [] };
    levels.forEach(level => {
      const items = (level.items || [])
        .map(rawItem => {
          const mapped = mapItem(rawItem);
          if (mapped == null) return null;
          const rawPool = (rawItem.extra_data && Array.isArray(rawItem.extra_data.pool))
            ? rawItem.extra_data.pool
            : null;
          if (rawPool && rawPool.length) {
            const mappedPool = rawPool
              .map(mapItem)
              .filter(entry => entry != null);
            if (mappedPool.length) mapped._pool = mappedPool;
          }
          return mapped;
        })
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
  // reviewItems (optional): [{ question, correctAnswer }, ...] -- missed
  // questions to reveal now that the game has actually ended. Answers are
  // intentionally withheld during play (no per-question reveal) so a wrong
  // guess doesn't hand the player the answer for next time; this is the one
  // place they're shown, once there's no more of that difficulty left to play.
  function showCompletionModal({ title, message, onContinue, continueLabel, autoContinueAfterMs = 0, reviewItems }) {
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
            <div id="gameCompleteReview" style="display:none; text-align:left; max-height:220px; overflow-y:auto; margin-top:12px; border-top:1px solid rgba(148,163,184,0.25); padding-top:12px;"></div>
            <div class="button-group" style="margin-top:18px;">
              <button type="button" class="btn btn-primary" id="gameCompleteContinueBtn">Continue</button>
            </div>
          </div>
        </div>`);
      modal = document.getElementById('gameCompleteModal');
    }
    document.getElementById('gameCompleteTitle').textContent = title || 'Great job!';
    document.getElementById('gameCompleteMessage').textContent = message || '';
    const reviewDiv = document.getElementById('gameCompleteReview');
    if (reviewDiv) {
      if (Array.isArray(reviewItems) && reviewItems.length) {
        reviewDiv.style.display = 'block';
        reviewDiv.innerHTML = '<strong>Answers to review:</strong><ul style="margin:8px 0 0; padding-left:20px;">'
          + reviewItems.map(item => `<li style="margin-bottom:4px;">${item.question} &rarr; <strong>${item.correctAnswer}</strong></li>`).join('')
          + '</ul>';
      } else {
        reviewDiv.style.display = 'none';
        reviewDiv.innerHTML = '';
      }
    }
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

  // ---- Game Result Screen (shown once a full game -- all three
  // difficulties -- is finished, distinct from the lighter
  // showCompletionModal used for the easy->medium->hard transitions) ----

  // Persists this result into the student's progress record (UserLearningState
  // via the same /learning/state/ read-merge-write endpoint the rest of the
  // dashboard/profile already uses) so score/high score survive across
  // devices and sessions, not just this browser's localStorage. Fire-and-
  // forget: never blocks the result screen from showing, and a failed sync
  // just means the next successful one catches up (localStorage remains the
  // source of truth for the live in-page high score comparison).
  function syncGameResult(gameKey, result) {
    try {
      if (!window.KumpasPortal || typeof window.KumpasPortal.updateState !== 'function') return;
      window.KumpasPortal.updateState({
        games: {
          [gameKey]: {
            score: result.score,
            highScore: result.highScore,
            correct: result.correct,
            difficulty: result.difficulty,
            lastPlayedAt: new Date().toISOString(),
          },
        },
      });
    } catch (_) {
      // Best-effort only -- see comment above.
    }
  }

  // config: { gameKey, gameLabel, score, highScore, correct, difficultyLabel,
  //           reviewItems, onPlayAgain }
  function showGameResultScreen(config) {
    syncGameResult(config.gameKey, {
      score: config.score,
      highScore: config.highScore,
      correct: config.correct,
      difficulty: config.difficultyLabel,
    });

    let modal = document.getElementById('gameResultModal');
    if (!modal) {
      document.body.insertAdjacentHTML('beforeend', `
        <div id="gameResultModal" class="modal" role="dialog" aria-modal="true" aria-labelledby="gameResultTitle">
          <div class="modal-content game-result-content">
            <button type="button" class="modal-close" aria-label="Close" onclick="KumpasGames.closeModal('gameResultModal')">&times;</button>
            <div class="game-result-header">
              <div class="game-result-icon">🏆</div>
              <h2 id="gameResultTitle">Game Complete!</h2>
              <p class="game-result-subtitle" id="gameResultSubtitle"></p>
            </div>
            <div class="game-result-score-row">
              <div class="game-result-score-box game-result-score-primary">
                <span class="game-result-score-label">Score</span>
                <span class="game-result-score-value" id="gameResultScore">0</span>
              </div>
              <div class="game-result-score-box">
                <span class="game-result-score-label">High Score</span>
                <span class="game-result-score-value" id="gameResultHighScore">0</span>
              </div>
            </div>
            <div class="game-instructions-levels" id="gameResultStats"></div>
            <div id="gameResultReview" style="display:none; text-align:left; max-height:180px; overflow-y:auto; margin-top:4px; border-top:1px solid rgba(148,163,184,0.25); padding-top:12px;"></div>
            <div class="game-result-buttons">
              <button type="button" class="btn btn-primary" id="gameResultPlayAgain">Play Again</button>
              <button type="button" class="btn btn-outline" id="gameResultBackToGames">Back to Games</button>
            </div>
          </div>
        </div>`);
      modal = document.getElementById('gameResultModal');
    }

    document.getElementById('gameResultSubtitle').textContent = config.gameLabel || '';
    document.getElementById('gameResultScore').textContent = config.score;
    document.getElementById('gameResultHighScore').textContent = config.highScore;
    document.getElementById('gameResultStats').innerHTML = [
      { label: 'Correct', value: config.correct },
      { label: 'Difficulty', value: config.difficultyLabel },
    ].map(s => `<div class="level-pill"><span>${s.label}</span><strong>${s.value}</strong></div>`).join('');

    const reviewDiv = document.getElementById('gameResultReview');
    if (Array.isArray(config.reviewItems) && config.reviewItems.length) {
      reviewDiv.style.display = 'block';
      reviewDiv.innerHTML = '<strong>Answers to review:</strong><ul style="margin:8px 0 0; padding-left:20px;">'
        + config.reviewItems.map(item => `<li style="margin-bottom:4px;">${item.question} &rarr; <strong>${item.correctAnswer}</strong></li>`).join('')
        + '</ul>';
    } else {
      reviewDiv.style.display = 'none';
      reviewDiv.innerHTML = '';
    }

    const backBtn = document.getElementById('gameResultBackToGames');
    const newBackBtn = backBtn.cloneNode(true);
    backBtn.parentNode.replaceChild(newBackBtn, backBtn);
    newBackBtn.addEventListener('click', () => {
      window.location.href = 'games.html';
    });

    const playAgainBtn = document.getElementById('gameResultPlayAgain');
    const newPlayAgainBtn = playAgainBtn.cloneNode(true);
    playAgainBtn.parentNode.replaceChild(newPlayAgainBtn, playAgainBtn);
    newPlayAgainBtn.addEventListener('click', () => {
      closeModal('gameResultModal');
      if (typeof config.onPlayAgain === 'function') config.onPlayAgain();
    });

    openModal('gameResultModal');
  }

  window.KumpasGames.showGameResultScreen = showGameResultScreen;

  // ---- Passing, tries and module review ----
  // Each difficulty is a "round" (all of its levels). A round is passed at
  // 70% correct (e.g. 7/10). Passing unlocks the next difficulty; failing
  // allows a retry. After 3 failed tries in a row on a difficulty, the
  // student must review a learning module (open its topics or materials)
  // before playing that difficulty again. Tries are kept per game and
  // difficulty so the end screen can show "passed Easy on try 2".
  const PASS_RATIO = 0.7;
  const MAX_FAILS_BEFORE_REVIEW = 3;
  const DIFFICULTIES = ['easy', 'medium', 'hard'];
  const DIFF_LABEL = { easy: 'Easy', medium: 'Medium', hard: 'Hard' };
  const REVIEW_KEY = 'kumpasLastModuleReviewAt';

  function passMarkFor(total) {
    return Math.max(1, Math.ceil(Number(total || 0) * PASS_RATIO));
  }

  function currentUserKey() {
    try {
      const user = window.KumpasPortal && window.KumpasPortal.getCurrentUser ? window.KumpasPortal.getCurrentUser() : null;
      return String((user && (user.email || user.username)) || 'guest').toLowerCase();
    } catch (_) {
      return 'guest';
    }
  }

  function readLocal(key) {
    try { return JSON.parse(localStorage.getItem(key) || 'null'); } catch (_) { return null; }
  }

  function writeLocal(key, value) {
    try { localStorage.setItem(key, JSON.stringify(value)); } catch (_) {}
  }

  // Newest of the synced learning state copy and this browser's copy.
  function loadAllAttempts() {
    const local = readLocal(`kumpasGameAttempts:${currentUserKey()}`);
    let synced = null;
    try {
      const state = window.KumpasPortal && window.KumpasPortal.getState ? window.KumpasPortal.getState() : null;
      synced = state && state.gameAttempts && typeof state.gameAttempts === 'object' ? state.gameAttempts : null;
    } catch (_) {}
    const pick = [local, synced].filter(Boolean).sort((a, b) => Number(b.updatedAt || 0) - Number(a.updatedAt || 0))[0];
    return pick ? JSON.parse(JSON.stringify(pick)) : { updatedAt: 0, games: {} };
  }

  function saveAllAttempts(all) {
    all.updatedAt = Date.now();
    writeLocal(`kumpasGameAttempts:${currentUserKey()}`, all);
    try {
      if (window.KumpasPortal && typeof window.KumpasPortal.updateState === 'function'
          && !(window.KumpasGamePreview && window.KumpasGamePreview.active)) {
        window.KumpasPortal.updateState({ gameAttempts: all });
      }
    } catch (_) {}
  }

  function emptyRecord() {
    return { tries: 0, fails: 0, passed: false, passedOnTry: 0, bestCorrect: 0, bestTotal: 0, reviewRequiredSince: 0 };
  }

  function getGameRecord(all, gameKey) {
    all.games = all.games || {};
    const game = all.games[gameKey] = all.games[gameKey] || {};
    DIFFICULTIES.forEach(d => { game[d] = Object.assign(emptyRecord(), game[d] || {}); });
    return game;
  }

  function lastModuleReviewAt() {
    let synced = 0;
    try {
      const state = window.KumpasPortal && window.KumpasPortal.getState ? window.KumpasPortal.getState() : null;
      synced = Number((state && state.lastModuleReviewAt) || 0);
    } catch (_) {}
    return Math.max(Number(readLocal(REVIEW_KEY) || 0), synced);
  }

  // True while the student still has to review a module for this difficulty.
  // Clears the lock (and the fail count) once a review has happened.
  function isReviewRequired(gameKey, difficulty) {
    const all = loadAllAttempts();
    const rec = getGameRecord(all, gameKey)[difficulty];
    if (!rec.reviewRequiredSince) return false;
    if (lastModuleReviewAt() > rec.reviewRequiredSince) {
      rec.reviewRequiredSince = 0;
      rec.fails = 0;
      saveAllAttempts(all);
      return false;
    }
    return true;
  }

  function recordRound(gameKey, difficulty, correct, total, passed) {
    const all = loadAllAttempts();
    const game = getGameRecord(all, gameKey);
    const rec = game[difficulty];
    rec.tries += 1;
    if (correct / Math.max(1, total) >= rec.bestCorrect / Math.max(1, rec.bestTotal || 1) || !rec.bestTotal) {
      rec.bestCorrect = correct;
      rec.bestTotal = total;
    }
    if (passed) {
      if (!rec.passed) rec.passedOnTry = rec.tries;
      rec.passed = true;
      rec.fails = 0;
      rec.reviewRequiredSince = 0;
    } else {
      rec.fails += 1;
      if (rec.fails >= MAX_FAILS_BEFORE_REVIEW) rec.reviewRequiredSince = Date.now();
    }
    saveAllAttempts(all);
    return { rec: Object.assign({}, rec), game: JSON.parse(JSON.stringify(game)) };
  }

  function getPassedDifficulties(gameKey) {
    const game = getGameRecord(loadAllAttempts(), gameKey);
    return { easy: game.easy.passed, medium: game.medium.passed, hard: game.hard.passed };
  }

  window.KumpasGames.passMarkFor = passMarkFor;
  window.KumpasGames.isReviewRequired = isReviewRequired;
  window.KumpasGames.getGameAttempts = gameKey => getGameRecord(loadAllAttempts(), gameKey);

  // ---- Round result screen ----
  function ensureRoundModal() {
    let modal = document.getElementById('gameRoundModal');
    if (modal) return modal;
    document.body.insertAdjacentHTML('beforeend', `
      <div id="gameRoundModal" class="modal" role="dialog" aria-modal="true" aria-labelledby="gameRoundTitle">
        <div class="modal-content game-result-content" style="max-width:520px;">
          <div class="game-result-header">
            <div class="game-result-icon" id="gameRoundIcon">🏆</div>
            <h2 id="gameRoundTitle">Round Complete</h2>
            <p class="game-result-subtitle" id="gameRoundSubtitle"></p>
          </div>
          <div class="game-result-score-row">
            <div class="game-result-score-box game-result-score-primary">
              <span class="game-result-score-label">Your Score</span>
              <span class="game-result-score-value" id="gameRoundScore">0/0</span>
            </div>
            <div class="game-result-score-box">
              <span class="game-result-score-label">Passing Score</span>
              <span class="game-result-score-value" id="gameRoundPassMark">0/0</span>
            </div>
          </div>
          <div id="gameRoundVerdict" style="margin:6px 0 10px;padding:10px 12px;border-radius:12px;font-weight:700;text-align:center;"></div>
          <div id="gameRoundMessage" style="color:#475569;line-height:1.55;text-align:center;margin-bottom:10px;"></div>
          <div id="gameRoundTries" style="text-align:left;margin-bottom:8px;"></div>
          <div id="gameRoundReview" style="display:none; text-align:left; max-height:160px; overflow-y:auto; margin-top:4px; border-top:1px solid rgba(148,163,184,0.25); padding-top:12px;"></div>
          <div class="game-result-buttons" id="gameRoundButtons"></div>
        </div>
      </div>`);
    return document.getElementById('gameRoundModal');
  }

  function triesSummaryHtml(game, highlight) {
    const rows = DIFFICULTIES.map(d => {
      const rec = game[d] || emptyRecord();
      let text;
      if (rec.passed) text = `✅ Passed on try ${rec.passedOnTry}${rec.tries > rec.passedOnTry ? ` <span style="color:#64748b;">(${rec.tries} plays total)</span>` : ''}`;
      else if (rec.tries) text = `❌ Not passed yet — ${rec.tries} ${rec.tries === 1 ? 'try' : 'tries'}`;
      else text = '<span style="color:#94a3b8;">Not played yet</span>';
      return `<div class="level-pill" style="justify-content:space-between;${d === highlight ? 'outline:2px solid #3b82f6;' : ''}"><span>${DIFF_LABEL[d]}</span><strong style="font-weight:600;">${text}</strong></div>`;
    }).join('');
    return `<div style="font-weight:700;margin-bottom:6px;">Tries before passing</div><div class="game-instructions-levels" style="display:grid;gap:6px;">${rows}</div>`;
  }

  // Latest round's answers per game + difficulty, for the end-of-game review.
  const lastRoundAnswers = {};

  function answersListHtml(answers) {
    if (!answers || !answers.length) return '<div style="color:#64748b;">No answers recorded.</div>';
    return '<ol style="margin:6px 0 0; padding-left:22px;">' + answers.map(a => `
      <li style="margin-bottom:6px;">
        <span style="font-weight:700;color:${a.correct ? '#059669' : '#dc2626'};">${a.correct ? '✓' : '✗'}</span>
        ${escapeHtml(a.question)}<br>
        <span style="color:#475569;">Correct answer:</span> <strong>${escapeHtml(a.correctAnswer || '—')}</strong>
        ${a.correct ? '' : `<br><span style="color:#475569;">Your answer:</span> <span style="color:#dc2626;">${escapeHtml(a.yourAnswer || '(no answer)')}</span>`}
      </li>`).join('') + '</ol>';
  }

  function escapeHtml(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  // Shows the review-the-module lock (no way back into the game from here).
  function showReviewRequired(gameKey, gameLabel, difficulty) {
    const modal = ensureRoundModal();
    const game = getGameRecord(loadAllAttempts(), gameKey);
    document.getElementById('gameRoundIcon').textContent = '📖';
    document.getElementById('gameRoundTitle').textContent = 'Review the module first';
    document.getElementById('gameRoundSubtitle').textContent = `${gameLabel || ''} · ${DIFF_LABEL[difficulty]}`;
    const rec = game[difficulty];
    document.getElementById('gameRoundScore').textContent = rec.bestTotal ? `${rec.bestCorrect}/${rec.bestTotal}` : '—';
    document.getElementById('gameRoundPassMark').textContent = rec.bestTotal ? `${passMarkFor(rec.bestTotal)}/${rec.bestTotal}` : '70%';
    const verdict = document.getElementById('gameRoundVerdict');
    verdict.textContent = `${MAX_FAILS_BEFORE_REVIEW} tries without passing`;
    verdict.style.cssText += ';background:#fffbeb;color:#92400e;border:1px solid #fcd34d;';
    document.getElementById('gameRoundMessage').innerHTML =
      `Read a learning module again — open its <strong>topics</strong> or <strong>materials</strong> — then come back to play ${DIFF_LABEL[difficulty]} again.`;
    document.getElementById('gameRoundTries').innerHTML = triesSummaryHtml(game, difficulty);
    document.getElementById('gameRoundReview').style.display = 'none';
    document.getElementById('gameRoundButtons').innerHTML = `
      <a class="btn btn-primary" href="learning.html">📖 Review the Module</a>
      <a class="btn btn-outline" href="games.html">Back to Games</a>`;
    openModal('gameRoundModal');
  }

  // cfg: { engine, gameKey, gameLabel, highScore, reviewItems, onReplay(level), onProceed(level) }
  function finishRound(cfg) {
    const engine = cfg.engine;
    const difficulty = engine.state.difficulty;
    const correct = Number(engine.state.roundCorrect || 0);
    const total = Number(engine.state.roundTotal || 0);
    const passMark = passMarkFor(total);
    const passed = total > 0 && correct >= passMark;
    const { rec, game } = recordRound(cfg.gameKey, difficulty, correct, total, passed);
    const nextDifficulty = difficulty === 'easy' ? 'medium' : difficulty === 'medium' ? 'hard' : null;
    const gameComplete = passed && !nextDifficulty;

    if (passed) engine.markDifficultyCompleted(difficulty);
    if (gameComplete) {
      awardCertificateIfEarned(cfg.gameKey);
      syncGameResult(cfg.gameKey, {
        score: engine.state.score,
        highScore: cfg.highScore,
        correct: engine.state.correct,
        difficulty: DIFF_LABEL[difficulty],
      });
    }

    const modal = ensureRoundModal();
    document.getElementById('gameRoundIcon').textContent = gameComplete ? '🏆' : passed ? '🎉' : '💪';
    document.getElementById('gameRoundTitle').textContent = gameComplete
      ? 'Game Complete!'
      : passed ? `${DIFF_LABEL[difficulty]} Passed!` : 'Not passed yet';
    document.getElementById('gameRoundSubtitle').textContent = `${cfg.gameLabel || ''} · ${DIFF_LABEL[difficulty]} · Try #${rec.tries}`;
    document.getElementById('gameRoundScore').textContent = `${correct}/${total}`;
    document.getElementById('gameRoundPassMark').textContent = `${passMark}/${total}`;

    const verdict = document.getElementById('gameRoundVerdict');
    verdict.style.cssText = 'margin:6px 0 10px;padding:10px 12px;border-radius:12px;font-weight:700;text-align:center;'
      + (passed ? 'background:#ecfdf5;color:#065f46;border:1px solid #a7f3d0;' : 'background:#fef2f2;color:#991b1b;border:1px solid #fecaca;');
    verdict.textContent = passed
      ? `✓ PASSED — ${correct}/${total} (needed ${passMark}/${total})`
      : `✗ NOT PASSED — ${correct}/${total} (needed ${passMark}/${total})`;

    const reviewNeeded = !passed && rec.reviewRequiredSince;
    const triesLeft = Math.max(0, MAX_FAILS_BEFORE_REVIEW - rec.fails);
    let message;
    if (gameComplete) {
      message = `You passed every difficulty! Final score: <strong>${engine.state.score}</strong> · High score: <strong>${cfg.highScore}</strong>.`;
    } else if (passed) {
      message = `Play ${DIFF_LABEL[difficulty]} again for practice, or move on to <strong>${DIFF_LABEL[nextDifficulty]}</strong> — it's harder.`;
    } else if (reviewNeeded) {
      message = `That was your ${MAX_FAILS_BEFORE_REVIEW}${MAX_FAILS_BEFORE_REVIEW === 3 ? 'rd' : 'th'} try without passing. <strong>Read a learning module again</strong> (open its topics or materials), then come back to play.`;
    } else {
      message = `Keep practicing! You have <strong>${triesLeft}</strong> more ${triesLeft === 1 ? 'try' : 'tries'} before you need to review the module.`;
    }
    document.getElementById('gameRoundMessage').innerHTML = message;
    document.getElementById('gameRoundTries').innerHTML = triesSummaryHtml(game, difficulty);

    // Correct answers: this difficulty after every round; all three
    // difficulties (latest round of each) once the whole game is finished.
    const roundAnswers = Array.isArray(engine.state.roundAnswers) ? engine.state.roundAnswers.slice() : [];
    lastRoundAnswers[cfg.gameKey] = lastRoundAnswers[cfg.gameKey] || {};
    lastRoundAnswers[cfg.gameKey][difficulty] = roundAnswers;
    const reviewDiv = document.getElementById('gameRoundReview');
    reviewDiv.style.maxHeight = gameComplete ? '320px' : '220px';
    if (gameComplete) {
      const byDifficulty = lastRoundAnswers[cfg.gameKey];
      reviewDiv.style.display = 'block';
      reviewDiv.innerHTML = '<div style="font-weight:700;margin-bottom:4px;">Correct answers</div>'
        + DIFFICULTIES.filter(d => byDifficulty[d]).map(d => {
          const list = byDifficulty[d];
          const right = list.filter(a => a.correct).length;
          return `<details ${d === 'hard' ? 'open' : ''} style="margin-bottom:8px;">
              <summary style="cursor:pointer;font-weight:700;">${DIFF_LABEL[d]} — ${right}/${list.length} correct</summary>
              ${answersListHtml(list)}
            </details>`;
        }).join('');
    } else if (roundAnswers.length) {
      const right = roundAnswers.filter(a => a.correct).length;
      reviewDiv.style.display = 'block';
      reviewDiv.innerHTML = `<div style="font-weight:700;">Correct answers — ${DIFF_LABEL[difficulty]} (${right}/${roundAnswers.length} correct)</div>`
        + answersListHtml(roundAnswers);
    } else {
      reviewDiv.style.display = 'none';
      reviewDiv.innerHTML = '';
    }

    const buttons = document.getElementById('gameRoundButtons');
    if (gameComplete) {
      buttons.innerHTML = `
        <button type="button" class="btn btn-primary" data-act="replay-easy">Play Again</button>
        <a class="btn btn-outline" href="games.html">Back to Games</a>`;
    } else if (passed) {
      buttons.innerHTML = `
        <button type="button" class="btn btn-outline" data-act="replay">🔁 Play ${DIFF_LABEL[difficulty]} Again</button>
        <button type="button" class="btn btn-primary" data-act="proceed">Proceed to ${DIFF_LABEL[nextDifficulty]} →</button>`;
    } else if (reviewNeeded) {
      buttons.innerHTML = `
        <a class="btn btn-primary" href="learning.html">📖 Review the Module</a>
        <a class="btn btn-outline" href="games.html">Back to Games</a>`;
    } else {
      buttons.innerHTML = `
        <button type="button" class="btn btn-primary" data-act="replay">🔁 Retry ${DIFF_LABEL[difficulty]}</button>
        <a class="btn btn-outline" href="games.html">Back to Games</a>`;
    }
    buttons.querySelectorAll('[data-act]').forEach(btn => {
      btn.addEventListener('click', () => {
        closeModal('gameRoundModal');
        const act = btn.dataset.act;
        if (act === 'proceed' && typeof cfg.onProceed === 'function') cfg.onProceed(nextDifficulty);
        else if (act === 'replay' && typeof cfg.onReplay === 'function') cfg.onReplay(difficulty);
        else if (act === 'replay-easy' && typeof cfg.onReplay === 'function') cfg.onReplay('easy');
      });
    });

    // Without the close button, this screen can only be left via its buttons.
    const closeBtn = modal.querySelector('.modal-close');
    if (closeBtn) closeBtn.remove();
    openModal('gameRoundModal');
  }

  window.KumpasGames.finishRound = finishRound;
  window.KumpasGames.showReviewRequired = showReviewRequired;

  // Small "To Pass" box next to the in-game score, e.g. "3 / 7".
  function updatePassIndicator(engine) {
    const correctEl = document.getElementById('correct');
    const anchor = correctEl && correctEl.closest('.score-box');
    if (!anchor) return;
    let box = document.getElementById('kgPassBox');
    if (!box) {
      anchor.insertAdjacentHTML('afterend', `
        <div class="score-box" id="kgPassBox" title="Correct answers needed on this difficulty to pass (70%)">
          <div class="label">To Pass</div>
          <div class="value" id="kgPassValue">0/0</div>
        </div>`);
      box = document.getElementById('kgPassBox');
    }
    const total = engine.expectedRoundTotal();
    const mark = passMarkFor(total);
    const got = Number(engine.state.roundCorrect || 0);
    const value = document.getElementById('kgPassValue');
    value.textContent = total ? `${got}/${mark}` : '—';
    value.style.color = total && got >= mark ? '#10b981' : '';
  }

  // ---- Difficulty / level engine ----
  // Creates a self-contained state machine each game page instantiates once.
  // choiceCounts: { easy, medium, hard } -- number of answer choices per difficulty.
  function createGameEngine(opts) {
    const state = {
      difficulty: 'easy',
      levelIndex: 0, // index into the CURRENT SHUFFLED ORDER for this difficulty
      questionIndex: 0, // index into the current level's question/item list
      score: 0,
      correct: 0,
      total: 0,
      // Correct answers / questions played in the current difficulty
      // (all of its levels) -- this is what the 70% pass mark is checked on.
      roundCorrect: 0,
      roundTotal: 0,
      // Every answer in the current difficulty: { question, correctAnswer, yourAnswer, correct }
      roundAnswers: [],
      // Restored from saved tries: a difficulty passed before stays passed.
      completedDifficulties: opts.gameKey ? getPassedDifficulties(opts.gameKey) : { easy: false, medium: false, hard: false },
      levelsByDifficulty: { easy: [], medium: [], hard: [] },
      // Per-difficulty shuffled level order, re-rolled every time that
      // difficulty is (re)started -- so replaying assigns different
      // questions to the "Level 1", "Level 2", ... slots instead of always
      // playing the same authored level_number order every session.
      shuffledOrder: { easy: null, medium: null, hard: null },
    };

    // Re-shuffles which authored level fills each position for `difficulty`.
    // Called every time that difficulty is (re)selected, including replays.
    function reshuffleLevelOrder(difficulty) {
      const list = state.levelsByDifficulty[difficulty] || [];
      state.shuffledOrder[difficulty] = shuffle(list);
    }

    // All playable content comes from teacher-authored GameLevel rows -- no
    // default/fallback pool. A difficulty with zero published levels simply
    // has nothing to play (see hasNextLevel/totalLevelsForDifficulty below).
    function activeLevelList() {
      // Lazily shuffle on first access (e.g. the very first "Start Game" of a
      // fresh page load, before any explicit setDifficulty() call) so even a
      // brand-new session doesn't play the raw authored level_number order.
      if (!state.shuffledOrder[state.difficulty]) {
        reshuffleLevelOrder(state.difficulty);
      }
      const list = state.shuffledOrder[state.difficulty] || [];
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

    // Displayed level number is the player's slot position in this session
    // (1, 2, 3, ...) rather than the authored level_number, since the order
    // is reshuffled every time the difficulty is (re)started -- showing the
    // raw level_number would make the on-screen counter jump around
    // non-sequentially (e.g. "Level 5" then "Level 2").
    function currentLevelNumber() {
      const result = state.levelIndex + 1;
      if (window.__KUMPAS_DEBUG_LEVELS__) {
        console.log('[KumpasGames.currentLevelNumber]', { difficulty: state.difficulty, levelIndex: state.levelIndex, result });
      }
      return result;
    }

    function totalLevelsForDifficulty(difficulty) {
      const list = state.levelsByDifficulty[difficulty];
      return (list && list.length) ? list.length : null; // null = nothing published for this difficulty
    }

    // Total number of on-screen choices/options for the current difficulty.
    // Each level holds a single correct item, so this is just the configured
    // count -- distractors to fill the rest come from each game's own wider
    // word/clip pool, not from the level itself.
    function getChoiceCount() {
      return Math.max(2, opts.choiceCounts[state.difficulty] || 4);
    }

    // Flat points per correct answer for the CURRENT difficulty -- no
    // level-number bonus, so the score always matches what's stated in the
    // "How to Play" instructions (e.g. "Easy = 10 pts") regardless of which
    // level/question the player happens to be on.
    function getPointValue() {
      return opts.pointBase[state.difficulty] || 10;
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
    // Redraws each item from its pool (if any) so the SAME level slot can
    // surface a different word on each playthrough. An item without a
    // `_pool` (or an empty one) always plays its own authored content, so
    // this is a no-op for levels that were never given extra alternatives.
    function drawFromPool(item) {
      if (!item || !Array.isArray(item._pool) || !item._pool.length) return item;
      const candidates = [item, ...item._pool];
      return candidates[Math.floor(Math.random() * candidates.length)];
    }

    function buildQuestionsForCurrentLevel() {
      const pool = getActivePool().map(drawFromPool);
      const questions = shuffle(pool).slice(0, Math.max(1, pool.length));
      if (state.levelIndex === 0) {
        // First level of a difficulty = start of a new round.
        state.roundCorrect = 0;
        state.roundTotal = 0;
        state.roundAnswers = [];
      }
      state.roundTotal += pool.length ? questions.length : 0;
      updatePassIndicator(engineApi);
      // 3 failed tries -> the student must review a module before playing again.
      if (opts.gameKey && !(window.KumpasGamePreview && window.KumpasGamePreview.active)
          && isReviewRequired(opts.gameKey, state.difficulty)) {
        showReviewRequired(opts.gameKey, opts.gameLabel, state.difficulty);
      }
      return questions;
    }

    // Number of questions in the whole current difficulty (all its levels).
    function expectedRoundTotal() {
      const levels = state.levelsByDifficulty[state.difficulty] || [];
      return levels.reduce((sum, level) => sum + ((level && level.items) ? level.items.length : 0), 0);
    }

    // Call after each correct answer so the "To Pass" box updates.
    function recordCorrect() {
      state.roundCorrect += 1;
      updatePassIndicator(engineApi);
    }

    // Call after every answer (right or wrong) so the correct answers can be
    // shown after the difficulty and at the end of the game.
    function recordAnswer(entry) {
      state.roundAnswers.push({
        question: String((entry && entry.question) || `Question ${state.roundAnswers.length + 1}`),
        correctAnswer: String((entry && entry.correctAnswer) || ''),
        yourAnswer: entry && entry.yourAnswer != null && entry.yourAnswer !== '' ? String(entry.yourAnswer) : '',
        correct: Boolean(entry && entry.correct),
      });
    }

    function hasNextLevel() {
      const levels = activeLevelList();
      if (levels) return state.levelIndex + 1 < levels.length;
      return false; // nothing playable at all for this difficulty
    }

    // Called when the player finishes all questions in the current level.
    // Returns 'next-level' | 'next-difficulty' | 'game-complete'.
    function advance() {
      if (window.__KUMPAS_DEBUG_LEVELS__) {
        console.log('[KumpasGames.advance]', {
          difficulty: state.difficulty,
          levelIndexBefore: state.levelIndex,
          activeLevelListLength: (activeLevelList() || []).length,
          hasNextLevel: hasNextLevel(),
          levelsByDifficulty: JSON.parse(JSON.stringify(state.levelsByDifficulty)),
        });
      }
      if (hasNextLevel()) {
        state.levelIndex += 1;
        return 'next-level';
      }
      // End of the difficulty: the game page calls KumpasGames.finishRound(),
      // which checks the 70% pass mark before unlocking the next difficulty.
      return 'round-complete';
    }

    function setDifficulty(level, resetScore) {
      state.difficulty = level;
      state.levelIndex = 0;
      reshuffleLevelOrder(level);
      document.querySelectorAll('.difficulty-btn').forEach(btn => btn.classList.remove('selected'));
      const btn = document.querySelector(`.difficulty-btn[data-level="${level}"]`);
      if (btn) btn.classList.add('selected');
      if (resetScore) {
        state.score = 0;
        state.correct = 0;
      }
      state.roundCorrect = 0;
      state.roundTotal = 0;
      state.roundAnswers = [];
      updateDifficultyButtons();
    }

    const engineApi = {
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
      expectedRoundTotal,
      recordCorrect,
      recordAnswer,
    };
    return engineApi;
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
