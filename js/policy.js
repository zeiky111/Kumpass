/*
 * Kumpas policies for Learning Modules and Games.
 *
 * Renders a "📜 Policy" button into any element with
 * [data-kumpas-policy="modules"|"games"] and opens the policy in a modal.
 * Each policy is also shown automatically the first time a student visits
 * the page (remembered per account in this browser).
 *
 * The rules listed here describe how the system actually behaves -- keep
 * them in sync with:
 *   - backend QUIZ_PASSING_PERCENT (75) and the level lock (views.py)
 *   - PASS_RATIO (0.7) / MAX_FAILS_BEFORE_REVIEW (3) in js/games-common.js
 */
(function () {
  'use strict';

  const POLICIES = {
    modules: {
      icon: '📘',
      title: 'Learning Modules Policy',
      intro: 'These rules apply to every learning module in Kumpas.',
      sections: [
        {
          heading: '1. Levels',
          items: [
            'Modules are grouped into <strong>Beginner</strong>, <strong>Elementary</strong>, <strong>Intermediate</strong> and <strong>Advanced</strong>.',
            'Elementary modules unlock only after you <strong>pass every Beginner module</strong>.',
            'Intermediate modules unlock only after you <strong>pass every Elementary module</strong>.',
            'Advanced modules unlock only after you <strong>pass every Intermediate module</strong>.',
          ],
        },
        {
          heading: '2. Order inside a module',
          items: [
            '<strong>Pre-test</strong> first. It measures what you already know, is taken <strong>once</strong>, and does not affect passing.',
            '<strong>Topics</strong> next, in order. A topic opens only after the one before it is marked done.',
            '<strong>Lesson materials</strong>: open every material in the module.',
            '<strong>Post-test</strong> last. It unlocks only after all topics are done and all materials are opened.',
          ],
        },
        {
          heading: '3. Passing the post-test',
          items: [
            'The passing score is <strong>75%</strong> (for example, 8 out of 10, or 15 out of 20).',
            'If you do not pass, you may <strong>retake</strong> the post-test. Review the topics and materials first.',
            'Your <strong>best score</strong> is kept. Once you pass, the post-test is closed.',
            'The correct answers are shown only after you pass.',
          ],
        },
        {
          heading: '4. Achievements and certificate',
          items: [
            'Passing a module\'s post-test earns an <strong>achievement</strong> for that module (e.g. "Passed: Alphabets").',
            'The <strong>certificate</strong> is given only when you have <strong>completed and passed every learning module</strong>.',
            'Achievements and the certificate appear in your <strong>Profile</strong>; the certificate is also sent to your registered email.',
          ],
        },
        {
          heading: '5. Progress',
          items: [
            'A module is <strong>completed</strong> when all of its topics and materials have been opened and its post-test is passed.',
            'Module progress grows with each step you finish: the pre-test, each topic, and each material.',
            'A module reaches <strong>100%</strong> only when its post-test is passed.',
          ],
        },
        {
          heading: '6. Use of materials',
          items: [
            'Lesson materials are for viewing inside Kumpas only and <strong>cannot be downloaded</strong>.',
            'Do not record, copy or share the materials outside the system.',
          ],
        },
        {
          heading: '7. Honesty',
          items: [
            'Answer the pre-test and post-test on your own, without help from others or outside sources.',
          ],
        },
      ],
    },
    games: {
      icon: '🎮',
      title: 'Games Policy',
      intro: 'These rules apply to all four games: Sign Match, Sign-to-Word Typing, Sentence Builder and Scenario-Based.',
      sections: [
        {
          heading: '1. Difficulty order',
          items: [
            'Every game is played <strong>Easy → Medium → Hard</strong>, and each difficulty is harder than the last.',
            'The next difficulty unlocks only after you <strong>pass</strong> the current one.',
          ],
        },
        {
          heading: '2. Passing score',
          items: [
            'You pass a difficulty with <strong>70% correct</strong> (for example, <strong>7 out of 10</strong>).',
            'The <strong>To Pass</strong> box beside your score shows how many correct answers you still need.',
          ],
        },
        {
          heading: '3. After you pass',
          items: [
            'You may <strong>play the same difficulty again</strong> for practice, or <strong>proceed</strong> to the next one.',
            'Passing <strong>Hard</strong> completes the game and earns the game\'s <strong>achievement</strong> (e.g. "Sign Match Game Champion").',
          ],
        },
        {
          heading: '4. If you do not pass',
          items: [
            'You may <strong>retry</strong> the difficulty.',
            'After <strong>3 tries without passing</strong> on a difficulty, you must <strong>review a learning module</strong> (open one of its topics or materials) before you can play that difficulty again.',
          ],
        },
        {
          heading: '5. Tries and answers',
          items: [
            'Every try is counted. At the end you will see how many tries it took to pass each difficulty.',
            'The <strong>correct answers</strong> are shown after each difficulty and again at the end of the game.',
          ],
        },
        {
          heading: '6. Fair play',
          items: [
            'Play on your own account and answer by yourself.',
            'On Hard, some games give you a time limit for each question.',
          ],
        },
      ],
    },
  };

  function seenKey(kind) {
    let user = '';
    try {
      const current = window.KumpasPortal && window.KumpasPortal.getCurrentUser ? window.KumpasPortal.getCurrentUser() : null;
      user = String((current && (current.email || current.username)) || '').toLowerCase();
    } catch (_) {}
    return `kumpasPolicySeen:${kind}:${user || 'guest'}`;
  }

  function injectStyles() {
    if (document.getElementById('kumpasPolicyStyles')) return;
    const style = document.createElement('style');
    style.id = 'kumpasPolicyStyles';
    style.textContent = `
      .kp-overlay { position: fixed !important; inset: 0; z-index: 10060 !important; display: none; align-items: center;
        justify-content: center; padding: 16px; background: rgba(15, 23, 42, 0.6); }
      .kp-overlay.open { display: flex; }
      .kp-dialog { width: min(680px, 100%); max-height: calc(100vh - 32px); display: flex; flex-direction: column;
        background: #fff; color: #0f172a; border-radius: 18px; box-shadow: 0 24px 60px rgba(15, 23, 42, 0.35); overflow: hidden; }
      .kp-head { display: flex; align-items: center; gap: 12px; padding: 16px 20px;
        background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 60%, #3b82f6 100%); color: #fff; }
      .kp-head h2 { margin: 0; font-size: 1.2rem; flex: 1; color: #fff; }
      .kp-head .kp-icon { font-size: 1.5rem; }
      .kp-close { width: 38px; height: 38px; border-radius: 50%; border: none; cursor: pointer; font-size: 1.4rem;
        line-height: 1; background: rgba(255,255,255,0.18); color: #fff; }
      .kp-close:hover, .kp-close:focus-visible { background: rgba(255,255,255,0.3); outline: none; }
      .kp-body { padding: 18px 20px; overflow-y: auto; line-height: 1.6; }
      .kp-intro { margin: 0 0 14px; color: #475569; }
      .kp-section { margin-bottom: 14px; }
      .kp-section h3 { margin: 0 0 6px; font-size: 1rem; color: #1e3a8a; }
      .kp-section ul { margin: 0; padding-left: 20px; }
      .kp-section li { margin-bottom: 4px; }
      .kp-foot { display: flex; justify-content: flex-end; padding: 12px 20px; border-top: 1px solid #e2e8f0; }
      .kp-ok { border: none; cursor: pointer; border-radius: 999px; padding: 10px 22px; font-weight: 700; font-family: inherit;
        color: #fff; background: linear-gradient(135deg, #2563eb 0%, #7c3aed 100%); }
      .kp-button { display: inline-flex; align-items: center; gap: 6px; border: 1px solid rgba(255,255,255,0.55);
        background: rgba(255,255,255,0.16); color: #fff; cursor: pointer; border-radius: 999px; padding: 8px 16px;
        font-weight: 700; font-size: 0.92rem; font-family: inherit; margin-top: 12px; }
      .kp-button:hover, .kp-button:focus-visible { background: rgba(255,255,255,0.28); outline: none; }
      :root[data-theme="dark"] .kp-dialog { background: #111827; color: #e5e7eb; }
      :root[data-theme="dark"] .kp-intro { color: #9ca3af; }
      :root[data-theme="dark"] .kp-section h3 { color: #93c5fd; }
      :root[data-theme="dark"] .kp-foot { border-color: #1f2937; }
      @media print { .kp-overlay { display: none !important; } }
    `;
    document.head.appendChild(style);
  }

  let overlay = null;

  function close() {
    if (!overlay) return;
    overlay.classList.remove('open');
    document.removeEventListener('keydown', onKey, true);
  }

  function onKey(e) {
    if (e.key === 'Escape') { e.preventDefault(); close(); }
  }

  function open(kind) {
    const policy = POLICIES[kind];
    if (!policy) return;
    injectStyles();
    if (!overlay) {
      overlay = document.createElement('div');
      overlay.className = 'kp-overlay';
      overlay.setAttribute('role', 'dialog');
      overlay.setAttribute('aria-modal', 'true');
      overlay.setAttribute('aria-labelledby', 'kpTitle');
      overlay.addEventListener('click', e => { if (e.target === overlay) close(); });
      document.body.appendChild(overlay);
    }
    overlay.innerHTML = `
      <div class="kp-dialog">
        <div class="kp-head">
          <span class="kp-icon" aria-hidden="true">${policy.icon}</span>
          <h2 id="kpTitle">${policy.title}</h2>
          <button type="button" class="kp-close" aria-label="Close policy">&times;</button>
        </div>
        <div class="kp-body">
          <p class="kp-intro">${policy.intro}</p>
          ${policy.sections.map(section => `
            <div class="kp-section">
              <h3>${section.heading}</h3>
              <ul>${section.items.map(item => `<li>${item}</li>`).join('')}</ul>
            </div>`).join('')}
        </div>
        <div class="kp-foot"><button type="button" class="kp-ok">I understand</button></div>
      </div>`;
    overlay.querySelector('.kp-close').addEventListener('click', close);
    overlay.querySelector('.kp-ok').addEventListener('click', () => {
      try { localStorage.setItem(seenKey(kind), '1'); } catch (_) {}
      close();
    });
    overlay.classList.add('open');
    document.addEventListener('keydown', onKey, true);
    overlay.querySelector('.kp-ok').focus();
  }

  function hasSeen(kind) {
    try { return localStorage.getItem(seenKey(kind)) === '1'; } catch (_) { return true; }
  }

  function init() {
    document.querySelectorAll('[data-kumpas-policy]').forEach(slot => {
      const kind = slot.getAttribute('data-kumpas-policy');
      if (!POLICIES[kind] || slot.querySelector('.kp-button')) return;
      injectStyles();
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'kp-button';
      button.innerHTML = `📜 ${POLICIES[kind].title}`;
      button.addEventListener('click', () => open(kind));
      slot.appendChild(button);

      // First visit: show it once, after the page (and the logged-in user)
      // has had a moment to load so it's remembered per account.
      setTimeout(() => {
        if (!hasSeen(kind) && !(overlay && overlay.classList.contains('open'))) open(kind);
      }, 1200);
    });
  }

  window.KumpasPolicy = { open, close, POLICIES };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
