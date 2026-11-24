/*
 * Kumpas topic viewer: a full-screen, step-by-step lesson for one topic of a
 * learning module.
 *
 * Each topic shows:
 *   - the lesson text the instructor wrote
 *   - the signs to learn, played from the shared sign video library, with
 *     slow motion (0.5x / 0.75x), repeat, and previous/next sign
 *   - "Mark as done & next" to finish the topic and move on
 *
 * Topics are done in order: a topic opens only after the ones before it are
 * finished.
 *
 * Usage:
 *   KumpasTopicViewer.open({
 *     moduleTitle, topics, index,
 *     onComplete: async (topic) => true|false,   // record completion
 *     onClose: () => {},                         // refresh the caller's UI
 *   })
 */
(function () {
  'use strict';

  let root = null;
  let els = {};
  let state = null;

  function esc(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  // Plain text -> paragraphs and bullet lists (lines starting with "-" or "*").
  function formatContent(text) {
    const blocks = String(text || '').replace(/\r\n/g, '\n').split(/\n{2,}/);
    return blocks.map(block => {
      const lines = block.split('\n').filter(line => line.trim());
      if (!lines.length) return '';
      if (lines.every(line => /^\s*[-*•]\s+/.test(line))) {
        return `<ul>${lines.map(line => `<li>${esc(line.replace(/^\s*[-*•]\s+/, ''))}</li>`).join('')}</ul>`;
      }
      return `<p>${lines.map(esc).join('<br>')}</p>`;
    }).join('');
  }

  function injectStyles() {
    if (document.getElementById('ktvStyles')) return;
    const style = document.createElement('style');
    style.id = 'ktvStyles';
    style.textContent = `
      /* !important: css/bg-orbs.css forces position:relative on every direct
         child of <body>, which would push this overlay below the footer. */
      .ktv { position: fixed !important; inset: 0; z-index: 10040 !important; display: none; flex-direction: column;
        background: #f1f5f9; color: #0f172a; font-family: inherit; }
      .ktv.open { display: flex; }
      .ktv-header { display: flex; align-items: center; gap: 12px; padding: 12px 16px;
        background: linear-gradient(135deg, #2563eb 0%, #7c3aed 100%); color: #fff; }
      .ktv-titles { flex: 1; min-width: 0; }
      .ktv-kicker { font-size: 0.74rem; letter-spacing: .06em; text-transform: uppercase; opacity: .85; font-weight: 700; }
      .ktv-title { margin: 2px 0 0; font-size: 1.15rem; font-weight: 800; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
      .ktv-close { flex: none; width: 42px; height: 42px; border-radius: 50%; border: none; cursor: pointer;
        background: rgba(255,255,255,0.18); color: #fff; font-size: 1.5rem; line-height: 1; }
      .ktv-close:hover, .ktv-close:focus-visible { background: rgba(255,255,255,0.3); outline: none; }
      .ktv-steps { display: flex; gap: 6px; padding: 10px 16px 0; overflow-x: auto; }
      .ktv-step { flex: 1 0 28px; max-width: 120px; height: 6px; border-radius: 999px; background: #cbd5e1; }
      .ktv-step.done { background: #10b981; }
      .ktv-step.current { background: #2563eb; }
      .ktv-body { flex: 1; min-height: 0; overflow: auto; padding: 16px; }
      .ktv-grid { max-width: 1180px; margin: 0 auto; display: grid; grid-template-columns: minmax(0, 1.2fr) minmax(0, 1fr); gap: 18px; }
      .ktv-grid.no-signs { grid-template-columns: minmax(0, 1fr); max-width: 820px; }
      .ktv-card { background: #fff; border-radius: 18px; box-shadow: 0 10px 28px rgba(15,23,42,0.08); padding: 18px; }
      .ktv-card h3 { margin: 0 0 10px; font-size: 1rem; color: #1e293b; }
      .ktv-player { position: relative; aspect-ratio: 4 / 3; background: #0f172a; border-radius: 14px; overflow: hidden;
        display: flex; align-items: center; justify-content: center; color: #e2e8f0; }
      .ktv-player video { width: 100%; height: 100%; object-fit: contain; background: #000; }
      .ktv-player .ktv-empty { text-align: center; padding: 16px; line-height: 1.6; }
      .ktv-player .ktv-empty .big { font-size: 2.6rem; display: block; }
      .ktv-sign-word { margin: 12px 0 4px; font-size: 1.5rem; font-weight: 800; text-align: center; color: #1e3a8a; }
      .ktv-sign-count { text-align: center; color: #64748b; font-size: 0.85rem; margin-bottom: 10px; }
      .ktv-controls { display: flex; flex-wrap: wrap; gap: 6px; justify-content: center; }
      .ktv-btn { border: 1px solid #cbd5e1; background: #fff; color: #1e293b; cursor: pointer; border-radius: 999px;
        padding: 8px 14px; font-weight: 600; font-size: 0.9rem; min-height: 40px; font-family: inherit; }
      .ktv-btn:hover:not(:disabled), .ktv-btn:focus-visible { border-color: #2563eb; color: #2563eb; outline: none; }
      .ktv-btn:disabled { opacity: .45; cursor: not-allowed; }
      .ktv-btn.active { background: #2563eb; border-color: #2563eb; color: #fff; }
      .ktv-btn.primary { background: linear-gradient(135deg, #2563eb 0%, #7c3aed 100%); border: none; color: #fff; padding: 10px 20px; }
      .ktv-btn.primary:hover:not(:disabled) { color: #fff; filter: brightness(1.08); }
      .ktv-btn.success { background: #10b981; border-color: #10b981; color: #fff; }
      .ktv-chips { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 14px; }
      .ktv-chip { border: 1px solid #c7d2fe; background: #eef2ff; color: #3730a3; border-radius: 999px; padding: 6px 12px;
        font-weight: 600; font-size: 0.88rem; cursor: pointer; font-family: inherit; }
      .ktv-chip.active { background: #4f46e5; border-color: #4f46e5; color: #fff; }
      .ktv-chip.missing { opacity: .6; }
      .ktv-content { line-height: 1.75; font-size: 1.02rem; color: #1e293b; }
      .ktv-content p { margin: 0 0 12px; }
      .ktv-content ul { margin: 0 0 12px 1.2rem; padding: 0; }
      .ktv-content li { margin-bottom: 4px; }
      .ktv-tip { margin-top: 14px; padding: 12px 14px; border-radius: 12px; background: #ecfdf5; color: #065f46; font-size: 0.92rem; line-height: 1.5; }
      .ktv-footer { display: flex; align-items: center; justify-content: space-between; gap: 10px; flex-wrap: wrap;
        padding: 12px 16px calc(12px + env(safe-area-inset-bottom)); background: #fff; border-top: 1px solid #e2e8f0; }
      .ktv-status { color: #475569; font-size: 0.9rem; }
      .ktv-status.done { color: #059669; font-weight: 700; }
      .ktv-footer-actions { display: flex; gap: 8px; flex-wrap: wrap; margin-left: auto; }
      .ktv-error { color: #b91c1c; font-size: 0.88rem; width: 100%; text-align: right; }
      :root[data-theme="dark"] .ktv { background: #0b1220; color: #e2e8f0; }
      :root[data-theme="dark"] .ktv-card, :root[data-theme="dark"] .ktv-footer { background: #111827; border-color: #1f2937; }
      :root[data-theme="dark"] .ktv-card h3, :root[data-theme="dark"] .ktv-content { color: #e2e8f0; }
      :root[data-theme="dark"] .ktv-sign-word { color: #93c5fd; }
      :root[data-theme="dark"] .ktv-btn { background: #1f2937; border-color: #374151; color: #e2e8f0; }
      :root[data-theme="dark"] .ktv-btn.active { background: #2563eb; border-color: #2563eb; color: #fff; }
      :root[data-theme="dark"] .ktv-chip { background: #1e1b4b; border-color: #3730a3; color: #c7d2fe; }
      :root[data-theme="dark"] .ktv-chip.active { background: #4f46e5; color: #fff; }
      :root[data-theme="dark"] .ktv-tip { background: #052e2b; color: #a7f3d0; }
      @media (max-width: 860px) {
        .ktv-grid { grid-template-columns: minmax(0, 1fr); }
        .ktv-body { padding: 10px; }
        .ktv-card { padding: 14px; }
        .ktv-footer-actions { width: 100%; }
        .ktv-footer-actions .ktv-btn { flex: 1; }
      }
    `;
    document.head.appendChild(style);
  }

  function buildShell() {
    if (root) return;
    injectStyles();
    root = document.createElement('div');
    root.className = 'ktv';
    root.setAttribute('role', 'dialog');
    root.setAttribute('aria-modal', 'true');
    root.setAttribute('aria-labelledby', 'ktvTitle');
    root.innerHTML = `
      <div class="ktv-header">
        <div class="ktv-titles">
          <div class="ktv-kicker"></div>
          <h2 class="ktv-title" id="ktvTitle"></h2>
        </div>
        <button type="button" class="ktv-close" aria-label="Close topic">&times;</button>
      </div>
      <div class="ktv-steps" aria-hidden="true"></div>
      <div class="ktv-body"></div>
      <div class="ktv-footer"></div>
    `;
    document.body.appendChild(root);
    els = {
      kicker: root.querySelector('.ktv-kicker'),
      title: root.querySelector('.ktv-title'),
      close: root.querySelector('.ktv-close'),
      steps: root.querySelector('.ktv-steps'),
      body: root.querySelector('.ktv-body'),
      footer: root.querySelector('.ktv-footer'),
    };
    els.close.addEventListener('click', close);
    root.addEventListener('contextmenu', e => { if (e.target.tagName === 'VIDEO') e.preventDefault(); });
  }

  function onKeyDown(e) {
    if (!root || !root.classList.contains('open')) return;
    if (e.key === 'Escape') { e.preventDefault(); close(); }
  }

  function isUnlocked(index) {
    return state.topics.slice(0, index).every(topic => topic.completed);
  }

  function stopVideo() {
    const video = els.body && els.body.querySelector('video');
    if (video) {
      try { video.pause(); } catch (_) {}
      video.removeAttribute('src');
      try { video.load(); } catch (_) {}
    }
  }

  function render() {
    stopVideo();
    const { topics, index, moduleTitle } = state;
    const topic = topics[index];
    const signs = Array.isArray(topic.signs) ? topic.signs : [];
    state.signIndex = 0;
    state.rate = state.rate || 1;

    els.kicker.textContent = `${moduleTitle ? moduleTitle + ' · ' : ''}Topic ${index + 1} of ${topics.length}`;
    els.title.textContent = topic.title || `Topic ${index + 1}`;
    els.steps.innerHTML = topics.map((t, i) =>
      `<span class="ktv-step${t.completed ? ' done' : ''}${i === index ? ' current' : ''}"></span>`).join('');

    const content = String(topic.content || '').trim();
    els.body.innerHTML = `
      <div class="ktv-grid${signs.length ? '' : ' no-signs'}">
        ${signs.length ? `
          <section class="ktv-card" aria-label="Signs to learn">
            <h3>🤟 Signs to learn</h3>
            <div class="ktv-player"></div>
            <div class="ktv-sign-word"></div>
            <div class="ktv-sign-count"></div>
            <div class="ktv-controls">
              <button type="button" class="ktv-btn" data-act="prev-sign" aria-label="Previous sign">‹ Prev</button>
              <button type="button" class="ktv-btn" data-rate="0.5">0.5×</button>
              <button type="button" class="ktv-btn" data-rate="0.75">0.75×</button>
              <button type="button" class="ktv-btn" data-rate="1">1×</button>
              <button type="button" class="ktv-btn" data-act="replay">↺ Replay</button>
              <button type="button" class="ktv-btn" data-act="next-sign" aria-label="Next sign">Next ›</button>
            </div>
            <div class="ktv-chips" role="list">
              ${signs.map((sign, i) => `<button type="button" role="listitem" class="ktv-chip${sign.video_url ? '' : ' missing'}" data-sign="${i}">${esc(sign.word)}</button>`).join('')}
            </div>
          </section>` : ''}
        <section class="ktv-card" aria-label="Lesson">
          <h3>📘 Lesson</h3>
          <div class="ktv-content">${content ? formatContent(content) : '<p style="color:#64748b;">Watch each sign and copy it until you can do it smoothly.</p>'}</div>
          ${signs.length ? '<div class="ktv-tip">💡 Tip: slow the video to 0.5× first, copy the handshape and movement, then try it at normal speed.</div>' : ''}
        </section>
      </div>
    `;

    if (signs.length) {
      els.body.querySelector('.ktv-controls').addEventListener('click', e => {
        const btn = e.target.closest('button');
        if (!btn) return;
        if (btn.dataset.rate) { state.rate = Number(btn.dataset.rate); applyRate(); }
        else if (btn.dataset.act === 'prev-sign') showSign(state.signIndex - 1);
        else if (btn.dataset.act === 'next-sign') showSign(state.signIndex + 1);
        else if (btn.dataset.act === 'replay') {
          const video = els.body.querySelector('.ktv-player video');
          if (video) { video.currentTime = 0; video.play().catch(() => {}); }
        }
      });
      els.body.querySelectorAll('.ktv-chip').forEach(chip => {
        chip.addEventListener('click', () => showSign(Number(chip.dataset.sign)));
      });
      showSign(0);
    }

    renderFooter();
    els.body.scrollTop = 0;
  }

  function applyRate() {
    const video = els.body.querySelector('.ktv-player video');
    if (video) video.playbackRate = state.rate;
    els.body.querySelectorAll('[data-rate]').forEach(btn => {
      btn.classList.toggle('active', Number(btn.dataset.rate) === state.rate);
    });
  }

  function showSign(i) {
    const signs = state.topics[state.index].signs || [];
    if (!signs.length) return;
    const next = Math.max(0, Math.min(signs.length - 1, i));
    state.signIndex = next;
    const sign = signs[next];
    stopVideo();
    const player = els.body.querySelector('.ktv-player');
    if (sign.video_url) {
      player.innerHTML = '';
      const video = document.createElement('video');
      video.muted = true;
      video.playsInline = true;
      video.setAttribute('playsinline', '');
      video.loop = true;
      video.autoplay = true;
      video.controls = true;
      video.setAttribute('controlsList', 'nodownload noremoteplayback');
      video.disablePictureInPicture = true;
      video.src = sign.video_url;
      video.addEventListener('loadedmetadata', applyRate);
      video.addEventListener('error', () => {
        player.innerHTML = `<div class="ktv-empty"><span class="big">⚠️</span>The video for "${esc(sign.word)}" could not be loaded.</div>`;
      });
      player.appendChild(video);
      video.play().catch(() => {});
    } else {
      player.innerHTML = `<div class="ktv-empty"><span class="big">🤟</span>No video yet for "${esc(sign.word)}".<br>Ask your instructor to demonstrate this sign.</div>`;
    }
    els.body.querySelector('.ktv-sign-word').textContent = sign.word;
    els.body.querySelector('.ktv-sign-count').textContent = `Sign ${next + 1} of ${signs.length}`;
    els.body.querySelector('[data-act="prev-sign"]').disabled = next <= 0;
    els.body.querySelector('[data-act="next-sign"]').disabled = next >= signs.length - 1;
    els.body.querySelectorAll('.ktv-chip').forEach(chip => chip.classList.toggle('active', Number(chip.dataset.sign) === next));
    applyRate();
  }

  function renderFooter(errorText) {
    const { topics, index } = state;
    const topic = topics[index];
    const isLast = index === topics.length - 1;
    const nextUnlocked = !isLast && isUnlocked(index + 1);
    const doneLabel = isLast ? '✓ Mark as done' : '✓ Mark as done & next';

    els.footer.innerHTML = `
      <span class="ktv-status${topic.completed ? ' done' : ''}">${topic.completed ? '✓ You finished this topic' : 'Practice the signs, then mark this topic as done.'}</span>
      <div class="ktv-footer-actions">
        <button type="button" class="ktv-btn" data-act="prev" ${index <= 0 ? 'disabled' : ''}>← Previous topic</button>
        ${topic.completed
          ? (isLast
            ? '<button type="button" class="ktv-btn success" data-act="close">Finish</button>'
            : `<button type="button" class="ktv-btn primary" data-act="next" ${nextUnlocked ? '' : 'disabled'}>Next topic →</button>`)
          : `<button type="button" class="ktv-btn primary" data-act="complete">${doneLabel}</button>`}
      </div>
      ${errorText ? `<div class="ktv-error">${esc(errorText)}</div>` : ''}
    `;
    els.footer.querySelectorAll('[data-act]').forEach(btn => {
      btn.addEventListener('click', () => handleFooter(btn.dataset.act, btn));
    });
  }

  async function handleFooter(act, btn) {
    if (act === 'prev' && state.index > 0) { state.index -= 1; render(); return; }
    if (act === 'next') { goTo(state.index + 1); return; }
    if (act === 'close') { close(); return; }
    if (act === 'complete') {
      const topic = state.topics[state.index];
      btn.disabled = true;
      btn.textContent = 'Saving…';
      let ok = false;
      try {
        ok = typeof state.onComplete === 'function' ? await state.onComplete(topic) : true;
      } catch (_) {
        ok = false;
      }
      if (!root.classList.contains('open')) return;
      if (!ok) {
        renderFooter('Could not save your progress. Check your connection and try again.');
        return;
      }
      topic.completed = true;
      state.changed = true;
      if (state.index < state.topics.length - 1) {
        state.index += 1;
        render();
      } else {
        els.steps.querySelectorAll('.ktv-step').forEach(step => step.classList.add('done'));
        renderFooter();
      }
    }
  }

  function goTo(index) {
    if (index < 0 || index >= state.topics.length) return;
    if (!isUnlocked(index)) return;
    state.index = index;
    render();
  }

  function open(options) {
    const opts = options || {};
    const topics = Array.isArray(opts.topics) ? opts.topics.map(t => Object.assign({}, t)) : [];
    if (!topics.length) return;
    buildShell();
    let index = Math.max(0, Math.min(topics.length - 1, Number(opts.index || 0)));
    // Never open past the first unfinished topic.
    const firstOpen = topics.findIndex(t => !t.completed);
    if (firstOpen >= 0 && index > firstOpen) index = firstOpen;
    state = {
      topics,
      index,
      moduleTitle: opts.moduleTitle || '',
      onComplete: opts.onComplete,
      onClose: opts.onClose,
      rate: 1,
      changed: false,
    };
    root.classList.add('open');
    document.documentElement.style.overflow = 'hidden';
    document.addEventListener('keydown', onKeyDown, true);
    render();
    els.close.focus();
  }

  function close() {
    if (!root || !state) return;
    stopVideo();
    root.classList.remove('open');
    document.documentElement.style.overflow = '';
    document.removeEventListener('keydown', onKeyDown, true);
    const { onClose, changed } = state;
    state = null;
    if (typeof onClose === 'function') onClose({ changed });
  }

  window.KumpasTopicViewer = { open, close };
})();
