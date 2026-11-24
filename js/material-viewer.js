/*
 * Kumpas in-app lesson material viewer.
 *
 * Students study module materials inside the app instead of downloading
 * them. Every material opens in a full-screen, lesson-style viewer:
 *   - PDF       -> rendered page by page (like slides) with PDF.js, no
 *                  browser PDF toolbar, so there's no download/print button
 *   - Video     -> player with slow-motion (0.5x / 0.75x) and repeat, which
 *                  is what students need to follow a sign
 *   - Image     -> fit-to-screen picture
 *   - Audio     -> player
 *   - Text      -> readable text panel
 *   - Word/PPT/Excel -> Office web viewer (read-only, embedded)
 *
 * The viewer blocks the context menu, Ctrl/Cmd+S and Ctrl/Cmd+P while it is
 * open. That keeps casual saving out of the lesson flow; it is not DRM.
 *
 * Usage: window.KumpasMaterialViewer.open(file, { onOpened })
 *   file = { file_name, description, file_type, file_extension, view_url | file_url }
 */
(function () {
  'use strict';

  const PDFJS_VERSION = '3.11.174';
  const PDFJS_SRC = `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/${PDFJS_VERSION}/pdf.min.js`;
  const PDFJS_WORKER = `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/${PDFJS_VERSION}/pdf.worker.min.js`;

  const OFFICE_EXTS = new Set(['doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx']);
  const IMAGE_EXTS = new Set(['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp']);
  const VIDEO_EXTS = new Set(['mp4', 'mov', 'webm', 'avi', 'mkv']);
  const AUDIO_EXTS = new Set(['mp3', 'wav', 'm4a', 'aac', 'flac', 'ogg']);
  const TEXT_EXTS = new Set(['txt']);

  let pdfjsPromise = null;
  let root = null;
  let els = {};
  let session = 0;
  let cleanupFns = [];

  function esc(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function extensionOf(file) {
    if (file.file_extension) return String(file.file_extension).toLowerCase();
    const name = String(file.file_name || '').split('?')[0];
    const dot = name.lastIndexOf('.');
    return dot >= 0 ? name.slice(dot + 1).toLowerCase() : '';
  }

  function kindOf(file) {
    const ext = extensionOf(file);
    if (file.file_type === 'video' || VIDEO_EXTS.has(ext)) return 'video';
    if (ext === 'pdf') return 'pdf';
    if (file.file_type === 'image' || IMAGE_EXTS.has(ext)) return 'image';
    if (file.file_type === 'audio' || AUDIO_EXTS.has(ext)) return 'audio';
    if (TEXT_EXTS.has(ext)) return 'text';
    if (OFFICE_EXTS.has(ext)) return 'office';
    return 'unsupported';
  }

  const KIND_ICON = {
    pdf: '📄', video: '🎬', image: '🖼️', audio: '🔊', text: '📝', office: '📑', unsupported: '📦',
  };

  function iconFor(file) {
    return KIND_ICON[kindOf(file)] || '📄';
  }

  function labelFor(file) {
    const kind = kindOf(file);
    const ext = extensionOf(file).toUpperCase();
    return {
      pdf: 'Reading', video: 'Sign video', image: 'Picture', audio: 'Audio',
      text: 'Notes', office: ext === 'PPT' || ext === 'PPTX' ? 'Slides' : 'Reading',
      unsupported: 'Material',
    }[kind];
  }

  function loadPdfJs() {
    if (window.pdfjsLib) return Promise.resolve(window.pdfjsLib);
    if (pdfjsPromise) return pdfjsPromise;
    pdfjsPromise = new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = PDFJS_SRC;
      script.async = true;
      script.onload = () => {
        if (!window.pdfjsLib) { reject(new Error('PDF viewer failed to load')); return; }
        window.pdfjsLib.GlobalWorkerOptions.workerSrc = PDFJS_WORKER;
        resolve(window.pdfjsLib);
      };
      script.onerror = () => { pdfjsPromise = null; reject(new Error('PDF viewer failed to load')); };
      document.head.appendChild(script);
    });
    return pdfjsPromise;
  }

  // ---------- Styles & shell ----------

  function injectStyles() {
    if (document.getElementById('kmvStyles')) return;
    const style = document.createElement('style');
    style.id = 'kmvStyles';
    style.textContent = `
      /* !important: css/bg-orbs.css forces position:relative on every direct
         child of <body>, which would push this overlay below the footer. */
      .kmv { position: fixed !important; inset: 0; z-index: 10050 !important; display: none; flex-direction: column;
        background: #0f172a; color: #f8fafc; font-family: inherit;
        -webkit-user-select: none; user-select: none; -webkit-touch-callout: none; }
      .kmv.open { display: flex; }
      .kmv-header { display: flex; align-items: center; gap: 12px; padding: 12px 16px;
        background: #111827; border-bottom: 1px solid rgba(255,255,255,0.08); }
      .kmv-icon { font-size: 1.6rem; line-height: 1; }
      .kmv-titles { flex: 1; min-width: 0; }
      .kmv-kicker { font-size: 0.72rem; letter-spacing: .06em; text-transform: uppercase; color: #93c5fd; font-weight: 700; }
      .kmv-title { margin: 2px 0 0; font-size: 1.05rem; font-weight: 700; color: #fff;
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
      .kmv-desc { margin: 2px 0 0; font-size: 0.85rem; color: #cbd5e1;
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
      .kmv-close { flex: none; width: 42px; height: 42px; border-radius: 50%; border: none; cursor: pointer;
        background: rgba(255,255,255,0.1); color: #fff; font-size: 1.5rem; line-height: 1; }
      .kmv-close:hover, .kmv-close:focus-visible { background: rgba(255,255,255,0.2); outline: none; }
      .kmv-stage { flex: 1; min-height: 0; position: relative; display: flex; align-items: center;
        justify-content: center; overflow: auto; padding: 16px; }
      .kmv-stage canvas { max-width: 100%; height: auto; background: #fff; border-radius: 8px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.35); }
      .kmv-stage img { max-width: 100%; max-height: 100%; object-fit: contain; border-radius: 8px; }
      .kmv-stage video { width: 100%; max-width: 960px; max-height: 100%; border-radius: 12px; background: #000; }
      .kmv-stage audio { width: min(560px, 100%); }
      .kmv-stage iframe { width: 100%; height: 100%; border: 0; border-radius: 8px; background: #fff; }
      .kmv-text { width: min(820px, 100%); max-height: 100%; overflow: auto; background: #fff; color: #111827;
        border-radius: 12px; padding: 24px; line-height: 1.7; white-space: pre-wrap; font-size: 1.02rem;
        -webkit-user-select: text; user-select: text; }
      .kmv-message { max-width: 460px; text-align: center; color: #e2e8f0; line-height: 1.6; }
      .kmv-message .big { font-size: 3rem; display: block; margin-bottom: 8px; }
      .kmv-spinner { width: 44px; height: 44px; border-radius: 50%; border: 4px solid rgba(255,255,255,0.25);
        border-top-color: #fff; animation: kmvSpin .8s linear infinite; }
      @keyframes kmvSpin { to { transform: rotate(360deg); } }
      .kmv-bar { display: flex; align-items: center; justify-content: center; flex-wrap: wrap; gap: 8px;
        padding: 10px 16px calc(10px + env(safe-area-inset-bottom)); background: #111827;
        border-top: 1px solid rgba(255,255,255,0.08); }
      .kmv-bar:empty { display: none; }
      .kmv-btn { border: none; cursor: pointer; border-radius: 999px; padding: 9px 16px; font-weight: 600;
        font-size: 0.92rem; background: rgba(255,255,255,0.1); color: #fff; min-height: 40px; }
      .kmv-btn:hover:not(:disabled), .kmv-btn:focus-visible { background: rgba(255,255,255,0.2); outline: none; }
      .kmv-btn:disabled { opacity: .4; cursor: not-allowed; }
      .kmv-btn.active { background: #2563eb; }
      .kmv-btn.primary { background: #2563eb; }
      .kmv-page { min-width: 110px; text-align: center; color: #cbd5e1; font-size: 0.92rem; }
      .kmv-group-label { color: #94a3b8; font-size: 0.82rem; margin-right: 2px; }
      .kmv-sep { width: 1px; height: 24px; background: rgba(255,255,255,0.15); margin: 0 4px; }
      .kmv-progress { position: absolute; left: 0; top: 0; height: 3px; background: #3b82f6; transition: width .2s ease; }
      @media (max-width: 600px) {
        .kmv-header { padding: 10px 12px; }
        .kmv-desc { display: none; }
        .kmv-stage { padding: 8px; }
        .kmv-btn { padding: 8px 12px; }
      }
      @media print { .kmv, .kmv * { display: none !important; } }
    `;
    document.head.appendChild(style);
  }

  function buildShell() {
    if (root) return;
    injectStyles();
    root = document.createElement('div');
    root.className = 'kmv';
    root.setAttribute('role', 'dialog');
    root.setAttribute('aria-modal', 'true');
    root.setAttribute('aria-labelledby', 'kmvTitle');
    root.innerHTML = `
      <div class="kmv-header">
        <span class="kmv-icon" aria-hidden="true"></span>
        <div class="kmv-titles">
          <div class="kmv-kicker"></div>
          <h2 class="kmv-title" id="kmvTitle"></h2>
          <p class="kmv-desc"></p>
        </div>
        <button type="button" class="kmv-close" aria-label="Close material">&times;</button>
      </div>
      <div class="kmv-stage"><div class="kmv-progress" style="width:0"></div><div class="kmv-content"></div></div>
      <div class="kmv-bar"></div>
    `;
    document.body.appendChild(root);
    els = {
      icon: root.querySelector('.kmv-icon'),
      kicker: root.querySelector('.kmv-kicker'),
      title: root.querySelector('.kmv-title'),
      desc: root.querySelector('.kmv-desc'),
      close: root.querySelector('.kmv-close'),
      stage: root.querySelector('.kmv-stage'),
      content: root.querySelector('.kmv-content'),
      progress: root.querySelector('.kmv-progress'),
      bar: root.querySelector('.kmv-bar'),
    };
    els.content.style.cssText = 'display:flex;align-items:center;justify-content:center;width:100%;height:100%;';
    els.close.addEventListener('click', close);
    root.addEventListener('contextmenu', e => e.preventDefault());
    root.addEventListener('dragstart', e => e.preventDefault());
  }

  function onKeyDown(e) {
    if (!root || !root.classList.contains('open')) return;
    const key = String(e.key || '').toLowerCase();
    if ((e.ctrlKey || e.metaKey) && (key === 's' || key === 'p')) {
      e.preventDefault();
      return;
    }
    if (key === 'escape') {
      e.preventDefault();
      close();
    }
  }

  function setLoading() {
    els.content.innerHTML = '<div class="kmv-spinner" role="status" aria-label="Loading material"></div>';
  }

  function setMessage(icon, html) {
    els.content.innerHTML = `<div class="kmv-message"><span class="big">${icon}</span>${html}</div>`;
  }

  function addCleanup(fn) { cleanupFns.push(fn); }

  function runCleanup() {
    cleanupFns.forEach(fn => { try { fn(); } catch (_) {} });
    cleanupFns = [];
  }

  // ---------- Renderers ----------

  async function renderPdf(url, token) {
    setLoading();
    let pdf;
    try {
      const pdfjsLib = await loadPdfJs();
      if (token !== session) return;
      pdf = await pdfjsLib.getDocument({ url, withCredentials: false }).promise;
    } catch (err) {
      if (token !== session) return;
      setMessage('⚠️', '<p>This reading could not be loaded right now.</p><p>Check your connection and try again.</p>');
      return;
    }
    if (token !== session) { pdf.destroy(); return; }
    addCleanup(() => pdf.destroy());

    const total = pdf.numPages;
    let page = 1;
    let zoom = 1;
    let renderTask = null;
    const canvas = document.createElement('canvas');
    canvas.setAttribute('aria-label', 'Lesson page');
    els.content.innerHTML = '';
    els.content.style.alignItems = 'flex-start';
    els.content.appendChild(canvas);

    els.bar.innerHTML = `
      <button type="button" class="kmv-btn" data-act="prev" aria-label="Previous page">‹ Prev</button>
      <span class="kmv-page" aria-live="polite"></span>
      <button type="button" class="kmv-btn primary" data-act="next" aria-label="Next page">Next ›</button>
      <span class="kmv-sep" aria-hidden="true"></span>
      <button type="button" class="kmv-btn" data-act="zoomout" aria-label="Zoom out">−</button>
      <button type="button" class="kmv-btn" data-act="fit" aria-label="Fit to screen">Fit</button>
      <button type="button" class="kmv-btn" data-act="zoomin" aria-label="Zoom in">+</button>
    `;
    const pageLabel = els.bar.querySelector('.kmv-page');
    const prevBtn = els.bar.querySelector('[data-act="prev"]');
    const nextBtn = els.bar.querySelector('[data-act="next"]');

    async function draw() {
      if (token !== session) return;
      pageLabel.textContent = `Page ${page} of ${total}`;
      prevBtn.disabled = page <= 1;
      nextBtn.disabled = page >= total;
      els.progress.style.width = `${(page / total) * 100}%`;
      if (renderTask) { try { renderTask.cancel(); } catch (_) {} }
      const pdfPage = await pdf.getPage(page);
      if (token !== session) return;
      const base = pdfPage.getViewport({ scale: 1 });
      const stageW = Math.max(200, els.stage.clientWidth - 32);
      const stageH = Math.max(200, els.stage.clientHeight - 32);
      // "Fit" shows the whole page; zoom scales from there.
      const fitScale = Math.min(stageW / base.width, stageH / base.height);
      const cssScale = fitScale * zoom;
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const viewport = pdfPage.getViewport({ scale: cssScale * dpr });
      canvas.width = Math.floor(viewport.width);
      canvas.height = Math.floor(viewport.height);
      canvas.style.width = `${Math.floor(viewport.width / dpr)}px`;
      canvas.style.maxWidth = zoom > 1 ? 'none' : '100%';
      els.content.style.justifyContent = zoom > 1 ? 'flex-start' : 'center';
      renderTask = pdfPage.render({ canvasContext: canvas.getContext('2d'), viewport });
      try { await renderTask.promise; } catch (_) { /* cancelled */ }
      els.stage.scrollTop = 0;
    }

    function go(delta) {
      const next = Math.min(total, Math.max(1, page + delta));
      if (next !== page) { page = next; draw(); }
    }

    els.bar.addEventListener('click', e => {
      const act = e.target.closest('[data-act]');
      if (!act) return;
      const a = act.dataset.act;
      if (a === 'prev') go(-1);
      else if (a === 'next') go(1);
      else if (a === 'zoomin') { zoom = Math.min(3, zoom + 0.25); draw(); }
      else if (a === 'zoomout') { zoom = Math.max(0.5, zoom - 0.25); draw(); }
      else if (a === 'fit') { zoom = 1; draw(); }
    });

    const keyNav = e => {
      if (e.key === 'ArrowRight' || e.key === 'PageDown') { e.preventDefault(); go(1); }
      else if (e.key === 'ArrowLeft' || e.key === 'PageUp') { e.preventDefault(); go(-1); }
    };
    document.addEventListener('keydown', keyNav);
    addCleanup(() => document.removeEventListener('keydown', keyNav));

    // Swipe left/right on phones to turn pages (only when not zoomed in).
    let touchX = null;
    const onTouchStart = e => { touchX = e.touches.length === 1 ? e.touches[0].clientX : null; };
    const onTouchEnd = e => {
      if (touchX == null || zoom > 1) return;
      const dx = e.changedTouches[0].clientX - touchX;
      if (Math.abs(dx) > 60) go(dx < 0 ? 1 : -1);
      touchX = null;
    };
    els.stage.addEventListener('touchstart', onTouchStart, { passive: true });
    els.stage.addEventListener('touchend', onTouchEnd);
    addCleanup(() => {
      els.stage.removeEventListener('touchstart', onTouchStart);
      els.stage.removeEventListener('touchend', onTouchEnd);
    });

    let resizeTimer = null;
    const onResize = () => { clearTimeout(resizeTimer); resizeTimer = setTimeout(draw, 150); };
    window.addEventListener('resize', onResize);
    addCleanup(() => { window.removeEventListener('resize', onResize); clearTimeout(resizeTimer); });

    draw();
  }

  function renderVideo(url, token, onPlay) {
    const video = document.createElement('video');
    video.controls = true;
    video.playsInline = true;
    video.setAttribute('playsinline', '');
    video.setAttribute('controlsList', 'nodownload noremoteplayback');
    video.disablePictureInPicture = true;
    video.preload = 'auto';
    video.src = url;
    els.content.innerHTML = '';
    els.content.appendChild(video);
    if (onPlay) video.addEventListener('play', onPlay, { once: true });
    video.addEventListener('error', () => {
      if (token !== session) return;
      setMessage('⚠️', '<p>This video could not be loaded right now.</p><p>Check your connection and try again.</p>');
    });
    addCleanup(() => { try { video.pause(); } catch (_) {} video.removeAttribute('src'); try { video.load(); } catch (_) {} });

    // Slow motion + repeat: the two things that help most when copying a sign.
    els.bar.innerHTML = `
      <span class="kmv-group-label">Speed</span>
      <button type="button" class="kmv-btn" data-rate="0.5">0.5×</button>
      <button type="button" class="kmv-btn" data-rate="0.75">0.75×</button>
      <button type="button" class="kmv-btn active" data-rate="1">1×</button>
      <span class="kmv-sep" aria-hidden="true"></span>
      <button type="button" class="kmv-btn" data-act="replay">↺ Replay</button>
      <button type="button" class="kmv-btn" data-act="loop" aria-pressed="false">🔁 Repeat</button>
    `;
    els.bar.addEventListener('click', e => {
      const btn = e.target.closest('button');
      if (!btn) return;
      if (btn.dataset.rate) {
        video.playbackRate = Number(btn.dataset.rate);
        els.bar.querySelectorAll('[data-rate]').forEach(b => b.classList.toggle('active', b === btn));
      } else if (btn.dataset.act === 'replay') {
        video.currentTime = 0;
        video.play().catch(() => {});
      } else if (btn.dataset.act === 'loop') {
        video.loop = !video.loop;
        btn.classList.toggle('active', video.loop);
        btn.setAttribute('aria-pressed', String(video.loop));
      }
    });
  }

  function renderImage(url, token) {
    setLoading();
    const img = new Image();
    img.alt = '';
    img.draggable = false;
    img.onload = () => {
      if (token !== session) return;
      els.content.innerHTML = '';
      els.content.appendChild(img);
    };
    img.onerror = () => {
      if (token !== session) return;
      setMessage('⚠️', '<p>This picture could not be loaded right now.</p>');
    };
    img.src = url;
  }

  function renderAudio(url) {
    els.content.innerHTML = '';
    const audio = document.createElement('audio');
    audio.controls = true;
    audio.setAttribute('controlsList', 'nodownload');
    audio.src = url;
    els.content.appendChild(audio);
    addCleanup(() => { try { audio.pause(); } catch (_) {} audio.removeAttribute('src'); });
  }

  async function renderText(url, token) {
    setLoading();
    try {
      const response = await fetch(url);
      if (!response.ok) throw new Error(String(response.status));
      const text = await response.text();
      if (token !== session) return;
      els.content.innerHTML = `<div class="kmv-text">${esc(text)}</div>`;
    } catch (_) {
      if (token !== session) return;
      setMessage('⚠️', '<p>These notes could not be loaded right now.</p>');
    }
  }

  function renderOffice(url) {
    const isLocal = /^(https?:\/\/)?(localhost|127\.|0\.0\.0\.0|10\.|192\.168\.)/i.test(url);
    if (isLocal) {
      setMessage('📑', '<p>Word, PowerPoint and Excel materials can only be previewed on the online (deployed) site.</p><p>Ask your instructor for a PDF version to view it here.</p>');
      return;
    }
    const frame = document.createElement('iframe');
    frame.title = 'Lesson material';
    frame.src = `https://view.officeapps.live.com/op/embed.aspx?src=${encodeURIComponent(url)}`;
    frame.setAttribute('referrerpolicy', 'no-referrer');
    els.content.innerHTML = '';
    els.content.appendChild(frame);
  }

  // ---------- Public API ----------

  function open(file, options) {
    if (!file) return;
    const opts = options || {};
    buildShell();
    runCleanup();
    const token = ++session;
    const url = file.view_url || file.file_url || '';
    const kind = kindOf(file);

    els.icon.textContent = iconFor(file);
    els.kicker.textContent = labelFor(file);
    els.title.textContent = file.file_name || 'Material';
    // Skip the description when it only repeats the file name.
    const desc = String(file.description || '').trim();
    const showDesc = desc && desc.toLowerCase() !== String(file.file_name || '').trim().toLowerCase();
    els.desc.textContent = showDesc ? desc : '';
    els.desc.style.display = showDesc ? '' : 'none';
    els.bar.innerHTML = '';
    const freshBar = els.bar.cloneNode(false); // drop old listeners
    els.bar.replaceWith(freshBar);
    els.bar = freshBar;
    els.progress.style.width = '0';
    els.content.style.alignItems = 'center';
    els.content.style.justifyContent = 'center';

    root.classList.add('open');
    document.documentElement.style.overflow = 'hidden';
    document.addEventListener('keydown', onKeyDown, true);
    els.close.focus();

    const markOpened = () => { if (typeof opts.onOpened === 'function') opts.onOpened(); };

    if (!url) {
      setMessage('⚠️', '<p>This material is not available yet.</p>');
      return;
    }

    if (kind === 'video') {
      // Watching counts as opening it.
      renderVideo(url, token, markOpened);
      return;
    }

    markOpened();
    if (kind === 'pdf') renderPdf(url, token);
    else if (kind === 'image') renderImage(url, token);
    else if (kind === 'audio') renderAudio(url);
    else if (kind === 'text') renderText(url, token);
    else if (kind === 'office') renderOffice(url);
    else setMessage('📦', '<p>This type of file can\'t be shown inside Kumpas.</p><p>Ask your instructor to upload it as a PDF, video or picture.</p>');
  }

  function close() {
    if (!root) return;
    session++;
    runCleanup();
    root.classList.remove('open');
    els.content.innerHTML = '';
    els.bar.innerHTML = '';
    document.documentElement.style.overflow = '';
    document.removeEventListener('keydown', onKeyDown, true);
  }

  window.KumpasMaterialViewer = { open, close, iconFor, labelFor, kindOf };
})();
