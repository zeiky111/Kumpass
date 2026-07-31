(function () {
  const STORAGE_KEY_PREFIX = 'kumpasLearningState';
  const API_BASE = localStorage.getItem('kumpasApiBase') || 'https://kumpass.onrender.com/api';
  const DEFAULT_USER_NAME = 'Learner';
  const DEFAULT_USER_EMAIL = '';
  let hydratedState = null;
  let studentContentCache = null;
  let currentUserCache = null;
  let currentUserPromise = null;

  const DEFAULT_STATE = {
    points: 0,
    rank: 0,
    accuracy: 0,
    streak: 0,
    completedActivities: 0,
    practiceMinutes: 0,
    weeklyActivity: [0, 0, 0, 0, 0, 0, 0],
    moduleProgress: {
      lesson1: 0,
      lesson2: 0,
      lesson3: 0,
      lesson4: 0,
      lesson5: 0,
      lesson6: 0,
      lesson7: 0,
      lesson8: 0
    },
    recentActivity: [],
    achievements: [],
    leaderboard: [],
    performance: []
  };

  function getCurrentUser() {
    if (currentUserCache && currentUserCache.email) {
      return currentUserCache;
    }

    return {
      name: DEFAULT_USER_NAME,
      email: DEFAULT_USER_EMAIL,
      yearLevel: '1',
      role: 'student'
    };
  }

  async function ensureCurrentUser() {
    if (currentUserCache && currentUserCache.email) {
      return currentUserCache;
    }

    if (!currentUserPromise) {
      currentUserPromise = (async () => {
        try {
          const response = await fetch(`${API_BASE}/auth/me/`, {
            method: 'GET',
            credentials: 'include'
          });
          if (!response.ok) {
            currentUserCache = null;
            return null;
          }

          const payload = await response.json();
          currentUserCache = payload && payload.user ? payload.user : null;
          return currentUserCache;
        } catch (_) {
          currentUserCache = null;
          return null;
        } finally {
          currentUserPromise = null;
        }
      })();
    }

    return currentUserPromise;
  }

  function getYearLabel(yearLevel) {
    const normalized = String(yearLevel || '').trim();
    const mapping = {
      '1': '1st Year',
      '2': '2nd Year',
      '3': '3rd Year',
      '4': '4th Year',
      instructor: 'Instructor',
      admin: 'Admin'
    };
    return mapping[normalized] || normalized || 'Student';
  }

  function getYearNumberFromLevel(level) {
    const value = String(level || '').toLowerCase().trim();
    if (value === '1st' || value === '1') return '1';
    if (value === '2nd' || value === '2') return '2';
    if (value === '3rd' || value === '3') return '3';
    if (value === '4th' || value === '4') return '4';
    return '1';
  }

  function getLevelTextFromYear(yearLevel) {
    const normalized = String(yearLevel || '').trim();
    const map = { '1': '1st', '2': '2nd', '3': '3rd', '4': '4th' };
    return map[normalized] || '1st';
  }

  function safeText(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function mapBackendModule(module, index) {
    const key = String((module && module.module_key) || '').trim() || `module${index + 1}`;
    const title = String((module && module.title) || `Module ${index + 1}`).trim();
    const description = String((module && module.description) || 'Structured sign language practice.').trim();
    const activities = Number((module && module.activities_count) || 4);
    const yearLevel = String((module && module.year_level) || '1').trim();
    const level = getLevelTextFromYear(yearLevel);
    const files = Array.isArray(module && module.files) ? module.files : [];
    const quizCount = Number((module && (module.quizCount || module.quiz_count)) || 0);
    const quizzes = Array.isArray(module && module.quizzes) ? module.quizzes : [];

    const numericId = Number(module && module.id);

    return {
      id: key,
      numericId: Number.isFinite(numericId) ? numericId : null,
      level,
      title,
      outcome: `Focus area for ${getYearLabel(yearLevel)} learners.`,
      description,
      activities: Number.isFinite(activities) ? activities : 4,
      minutes: Math.max(20, (Number.isFinite(activities) ? activities : 4) * 15),
      progressKey: key,
      unlocks: 'Unlocks the next guided activities and game challenges.',
      files,
      filesCount: files.length,
      quizCount: Number.isFinite(quizCount) ? quizCount : 0
      ,
      quizzes: quizzes
    };
  }

  function getVisibleModules() {
    if (studentContentCache && Array.isArray(studentContentCache.modules) && studentContentCache.modules.length) {
      return studentContentCache.modules.map(mapBackendModule);
    }

    return [];
  }

  function getState() {
    if (hydratedState) {
      return mergeState(hydratedState);
    }

    return mergeState({});
  }

  async function loadStateFromBackend() {
    const currentUser = getCurrentUser();
    const email = String(currentUser.email || '').trim();
    if (!email) {
      return null;
    }

    try {
      const response = await fetch(`${API_BASE}/learning/state/?email=${encodeURIComponent(email)}`, {
        credentials: 'include'
      });
      if (!response.ok) {
        return null;
      }

      const payload = await response.json();
      if (!payload || typeof payload.state !== 'object') {
        return null;
      }

      const merged = mergeState(payload.state);
      hydratedState = merged;
      return merged;
    } catch (_) {
      return null;
    }
  }

  async function loadStateForEmail(email) {
    const normalizedEmail = String(email || '').trim();
    if (!normalizedEmail) {
      return null;
    }

    try {
      const response = await fetch(`${API_BASE}/learning/state/?email=${encodeURIComponent(normalizedEmail)}`, {
        credentials: 'include'
      });
      if (!response.ok) {
        return null;
      }

      const payload = await response.json();
      if (!payload || typeof payload.state !== 'object') {
        return null;
      }

      return mergeState(payload.state);
    } catch (_) {
      return null;
    }
  }

  async function loadCertificatesForEmail(email) {
    const normalizedEmail = String(email || '').trim();
    if (!normalizedEmail) {
      return [];
    }

    try {
      const response = await fetch(`${API_BASE}/certificates/?email=${encodeURIComponent(normalizedEmail)}`, {
        credentials: 'include'
      });
      if (!response.ok) {
        return [];
      }

      const payload = await response.json();
      return Array.isArray(payload.certificates) ? payload.certificates : [];
    } catch (_) {
      return [];
    }
  }

  async function loadLeaderboardFromBackend(options) {
    const currentUser = getCurrentUser();
    const config = options && typeof options === 'object' ? options : {};
    const params = new URLSearchParams();

    if (currentUser.email) {
      params.set('email', currentUser.email);
    }
    if (config.yearLevel && config.yearLevel !== 'all') {
      params.set('yearLevel', config.yearLevel);
    }
    if (config.sortBy) {
      params.set('sortBy', config.sortBy);
    }
    if (config.timeRange) {
      params.set('timeRange', config.timeRange);
    }
    if (config.limit) {
      params.set('limit', String(config.limit));
    }

    try {
      const response = await fetch(`${API_BASE}/leaderboard/?${params.toString()}`);
      if (!response.ok) {
        return null;
      }

      return await response.json();
    } catch (_) {
      return null;
    }
  }

  async function loadPublicAnnouncements(limit) {
    const params = new URLSearchParams();
    const normalizedLimit = Number(limit || 3);
    if (Number.isFinite(normalizedLimit) && normalizedLimit > 0) {
      params.set('limit', String(Math.min(20, Math.round(normalizedLimit))));
    }

    try {
      const response = await fetch(`${API_BASE}/announcements/?${params.toString()}`);
      if (!response.ok) {
        return [];
      }

      const payload = await response.json();
      return Array.isArray(payload) ? payload : [];
    } catch (_) {
      return [];
    }
  }

  async function loadStudentContentFromBackend() {
    // Ensure we have the session-backed user before requesting student content
    const sessionUser = await ensureCurrentUser().catch(() => null);
    const currentUser = sessionUser || getCurrentUser();
    const email = String(currentUser.email || '').trim();
    if (!email) {
      // No authenticated email yet; skip loading content
      return null;
    }

    try {
      const response = await fetch(`${API_BASE}/student/content/?email=${encodeURIComponent(email)}&limit=50`, {
        credentials: 'include'
      });
      if (!response.ok) {
        return null;
      }

      const payload = await response.json();
      if (!payload || !Array.isArray(payload.modules)) {
        studentContentCache = null;
        return null;
      }

      studentContentCache = payload;
      return payload;
    } catch (_) {
      studentContentCache = null;
      return null;
    }
  }

  function renderRecentActivityList(target, entries) {
    if (!target) {
      return;
    }

    target.innerHTML = entries.map(activity => `
      <li>
        <span style="display:flex; align-items:center; gap:10px;">
          <span class="activity-dot"></span>
          <span>${activity.icon} ${activity.text}</span>
        </span>
        <span class="activity-meta">${activity.meta}</span>
      </li>
    `).join('');
  }

  async function syncStateToBackend(state) {
    const currentUser = getCurrentUser();
    const email = String(currentUser.email || '').trim();
    if (!email) {
      return null;
    }

    try {
      const response = await fetch(`${API_BASE}/learning/state/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ email, state }),
      });

      if (!response.ok) {
        return null;
      }

      const payload = await response.json();
      if (payload && typeof payload.state === 'object') {
        hydratedState = mergeState(payload.state);
      }
      return payload;
    } catch (_) {
      return null;
    }
  }

  function mergeState(partial) {
    const state = JSON.parse(JSON.stringify(DEFAULT_STATE));
    const source = partial && typeof partial === 'object' ? partial : {};

    Object.keys(source).forEach(key => {
      if (Array.isArray(source[key])) {
        state[key] = source[key].slice();
      } else if (source[key] && typeof source[key] === 'object' && !Array.isArray(source[key])) {
        state[key] = Object.assign({}, state[key] || {}, source[key]);
      } else {
        state[key] = source[key];
      }
    });

    state.moduleProgress = Object.assign({}, DEFAULT_STATE.moduleProgress, source.moduleProgress || {});
    state.performance = Array.isArray(source.performance) && source.performance.length ? source.performance : DEFAULT_STATE.performance.slice();
    state.achievements = Array.isArray(source.achievements) && source.achievements.length ? source.achievements : DEFAULT_STATE.achievements.slice();
    state.recentActivity = Array.isArray(source.recentActivity) && source.recentActivity.length ? source.recentActivity : DEFAULT_STATE.recentActivity.slice();
    state.leaderboard = Array.isArray(source.leaderboard) && source.leaderboard.length ? source.leaderboard : DEFAULT_STATE.leaderboard.slice();

    return state;
  }

  function saveState(state) {
    const merged = mergeState(state);
    hydratedState = merged;
    void syncStateToBackend(merged);
  }

  function updateState(patch) {
    const nextState = mergeState(Object.assign({}, getState(), patch || {}));
    saveState(nextState);
    return nextState;
  }

  function getModuleProgress(state, moduleId) {
    const value = Number(state.moduleProgress[moduleId] || 0);
    return Number.isFinite(value) ? Math.max(0, Math.min(100, value)) : 0;
  }

  function getModuleStatus(progress) {
    if (progress >= 100) return 'Completed';
    if (progress > 0) return 'In Progress';
    return 'Not Started';
  }

  function calculateRank(points) {
    if (points <= 0) return 0;
    if (points >= 4000) return 1;
    if (points >= 3500) return 3;
    if (points >= 3000) return 5;
    if (points >= 2500) return 8;
    if (points >= 2000) return 12;
    if (points >= 1500) return 18;
    return 24;
  }

  function recordProgress(options) {
    const currentState = getState();
    const currentUser = getCurrentUser();
    const config = options && typeof options === 'object' ? options : {};
    const moduleId = config.moduleId;
    const pointsEarned = Number(config.points || 0);
    const practiceMinutes = Number(config.practiceMinutes || 0);
    const progressDelta = Number(config.progressDelta || 0);
    const completed = Boolean(config.completed);
    const activityName = String(config.activityName || 'Activity').trim();
    const activityMeta = String(config.activityMeta || '').trim();

    const nextState = mergeState(currentState);
    nextState.points = Math.max(0, Number(nextState.points || 0) + pointsEarned);
    nextState.completedActivities = Math.max(0, Number(nextState.completedActivities || 0) + (completed ? 1 : 0));
    nextState.practiceMinutes = Math.max(0, Number(nextState.practiceMinutes || 0) + practiceMinutes);
    nextState.rank = calculateRank(nextState.points);

    if (moduleId) {
      const currentProgress = getModuleProgress(nextState, moduleId);
      const updatedProgress = completed ? 100 : Math.min(100, currentProgress + progressDelta);
      nextState.moduleProgress[moduleId] = updatedProgress;
    }

    const activityEntry = {
      icon: config.icon || '🎮',
      text: config.activityText || `${activityName} completed`,
      meta: activityMeta || `${pointsEarned > 0 ? '+' : ''}${pointsEarned} points`,
    };
    nextState.recentActivity = [activityEntry].concat(nextState.recentActivity || []).slice(0, 10);

    const leaderboard = Array.isArray(nextState.leaderboard) ? nextState.leaderboard.slice() : [];
    const selfIndex = leaderboard.findIndex(entry => entry.name === 'You');
    if (selfIndex >= 0) {
      leaderboard[selfIndex] = Object.assign({}, leaderboard[selfIndex], { points: nextState.points });
    } else {
      leaderboard.push({ name: currentUser.name || 'You', points: nextState.points });
    }
    nextState.leaderboard = leaderboard.sort((a, b) => Number(b.points || 0) - Number(a.points || 0));

    saveState(nextState);
    return nextState;
  }

  function getFilteredModules(level) {
    const modules = getVisibleModules();
    if (!level || level === 'all') {
      return modules;
    }

    return modules.filter(module => module.level === level);
  }

  function getModuleById(moduleId) {
    const modules = getVisibleModules();
    return modules.find(module => String(module.id) === String(moduleId)) || null;
  }

  function closeModuleDetails() {
    const modal = document.getElementById('learningModuleModal');
    if (modal) {
      modal.classList.remove('active');
    }
  }

  function openModuleDetails(moduleId) {
    const module = getModuleById(moduleId);
    if (!module) {
      return;
    }

    const modal = document.getElementById('learningModuleModal');
    const title = document.getElementById('learningModuleTitle');
    const description = document.getElementById('learningModuleDescription');
    const meta = document.getElementById('learningModuleMeta');
    const files = document.getElementById('learningModuleFiles');
    const startButton = document.getElementById('learningModuleStartButton');
    const reviewButton = document.getElementById('learningModuleReviewButton');
    const state = getState();
    const moduleProgress = getModuleProgress(state, module.id);
    const completed = moduleProgress >= 100;
    const moduleFiles = Array.isArray(module.files) ? module.files : [];

    if (title) title.textContent = module.title || 'Module';
    const heroTitle = document.getElementById('learningModuleTitleHero');
    if (heroTitle) heroTitle.textContent = module.title || 'Module details';
    if (description) description.textContent = module.description || 'No description available.';
    if (meta) {
      meta.innerHTML = `
        <span class="module-chip">${safeText(module.level)} Year</span>
        <span class="module-chip">📚 ${Number(module.activities || 0)} activities</span>
        <span class="module-chip">⏱️ ${Number(module.minutes || 0)} min</span>
        <span class="module-chip">📎 ${Number(module.filesCount || 0)} materials</span>
        <span class="module-chip">${moduleProgress}% complete</span>
      `;
    }

    if (files) {
      files.innerHTML = moduleFiles.length
        ? moduleFiles.map(file => `
            <div class="learning-file-row">
              <div>
                <div class="learning-file-name">${safeText(file.file_name)}</div>
                <small>${safeText(file.description || 'Teacher-uploaded material')}</small>
              </div>
              <div style="display:flex; gap:8px; flex-wrap:wrap; align-items:center;">
                ${file.file_url ? `<a class="learning-file-link" href="${safeText(file.file_url)}" target="_blank" rel="noopener">Open</a>` : ''}
              </div>
            </div>
          `).join('')
          : '<div style="padding:14px;color:#6b7280;background:#f8fafc;border:1px dashed #d1d5db;border-radius:12px;">No uploaded files yet.</div>';
      }

      // Show Open Quiz button if module has quizzes
      try {
        const actions = modal ? modal.querySelector('.module-detail-actions') : null;
        let openQuizBtn = document.getElementById('learningModuleOpenQuizButton');
        if (!openQuizBtn && actions) {
          openQuizBtn = document.createElement('button');
          openQuizBtn.type = 'button';
          openQuizBtn.id = 'learningModuleOpenQuizButton';
          openQuizBtn.className = 'btn-primary';
          openQuizBtn.textContent = 'Open Quiz';
          actions.appendChild(openQuizBtn);
        }
        if (openQuizBtn) {
          openQuizBtn.style.display = module && (Number(module.quizCount || 0) > 0) ? 'inline-flex' : 'none';
          openQuizBtn.onclick = (e) => { e.stopPropagation(); openQuiz(module.id); };
        }
      } catch (e) {
        // ignore
      }

    if (startButton) {
      startButton.textContent = completed ? 'Review Module' : 'Start Learning';
      startButton.onclick = () => {
        window.location.href = completed ? `activity.html?module=${module.id}&review=true` : `activity.html?module=${module.id}`;
      };
    }

    if (reviewButton) {
      reviewButton.style.display = completed ? 'inline-flex' : 'none';
      reviewButton.onclick = () => {
        window.location.href = `activity.html?module=${module.id}&review=true`;
      };
    }

    if (modal) {
      modal.classList.add('active');
    }
  }

  window.openModuleDetails = openModuleDetails;
  window.closeModuleDetails = closeModuleDetails;

  function closeQuizModal() {
    const modal = document.getElementById('quizModal');
    if (modal) modal.classList.remove('active');
  }

  async function openQuiz(moduleId) {
    const module = getModuleById(moduleId);
    if (!module) return;

    const modal = document.getElementById('quizModal');
    const body = document.getElementById('quizModalBody');
    if (!modal || !body) return;

    const moduleQuizzes = Array.isArray(module.quizzes) ? module.quizzes : [];
    if (!moduleQuizzes.length) {
      body.innerHTML = '<div style="padding:12px;color:#6b7280;background:#f8fafc;border:1px dashed #d1d5db;border-radius:12px;">No quizzes available for this module.</div>';
      modal.classList.add('active');
      return;
    }

    const totalQuestions = moduleQuizzes.length;
    const progressLabel = document.getElementById('quizProgressLabel');
    const progressFill = document.getElementById('quizProgressFill');
    if (progressLabel) progressLabel.textContent = `${totalQuestions} question${totalQuestions === 1 ? '' : 's'}`;
    if (progressFill) progressFill.style.width = '0%';

    let formHtml = `<form id="popupModuleQuizForm">`;
    moduleQuizzes.forEach((q, i) => {
      const idx = i + 1;
      formHtml += `<div class="quiz-question-card" data-question-index="${i}">`;
      formHtml += `<div class="quiz-question-text">Q${idx}. ${safeText(q.question_text)}</div>`;
      const choices = Array.isArray(q.choices) ? q.choices : [];
      if (choices.length) {
        formHtml += `<div class="quiz-choice-list">`;
        choices.forEach((choice, choiceIdx) => {
          formHtml += `
            <label class="quiz-choice">
              <input type="radio" name="q_${q.id}" value="${safeText(choice)}" data-question-index="${i}">
              <span>${safeText(choice)}</span>
            </label>`;
        });
        formHtml += `</div>`;
      } else {
        formHtml += `<input type="text" class="quiz-text-answer" name="q_${q.id}" placeholder="Your answer" data-question-index="${i}">`;
      }
      formHtml += `</div>`;
    });
    formHtml += `</form>`;

    body.innerHTML = formHtml;
    modal.classList.add('active');

    const form = document.getElementById('popupModuleQuizForm');
    const submitButton = document.getElementById('quizSubmitButton');

    const updateQuizProgress = () => {
      if (!form) return;
      const answered = new Set();
      form.querySelectorAll('input[data-question-index]').forEach(input => {
        const isAnswered = input.type === 'radio' ? input.checked : String(input.value || '').trim() !== '';
        if (isAnswered) answered.add(input.getAttribute('data-question-index'));
      });
      const answeredCount = answered.size;
      if (progressLabel) progressLabel.textContent = `${answeredCount} of ${totalQuestions} answered`;
      if (progressFill) progressFill.style.width = `${totalQuestions ? Math.round((answeredCount / totalQuestions) * 100) : 0}%`;
    };

    if (form) {
      form.addEventListener('input', updateQuizProgress);
      updateQuizProgress();
    }

    if (submitButton) {
      submitButton.onclick = async () => {
        if (!form) return;
        const fd = new FormData(form);
        const answers = [];
        moduleQuizzes.forEach(q => {
          const name = `q_${q.id}`;
          const val = fd.get(name);
          if (val !== null) answers.push({ question_id: Number(q.id), answer: String(val) });
        });

        const currentUser = getCurrentUser();
        const payload = { email: currentUser.email || '', answers };
        const quizModuleId = Number.isFinite(module.numericId) ? module.numericId : module.id;

        submitButton.disabled = true;
        submitButton.textContent = 'Submitting…';

        try {
          const resp = await fetch(`${API_BASE}/modules/${encodeURIComponent(quizModuleId)}/submit_quiz/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify(payload),
          });
          if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            alert(err && err.error ? `Quiz submission failed: ${err.error}` : 'Quiz submission failed');
            submitButton.disabled = false;
            submitButton.textContent = 'Submit Quiz';
            return;
          }
          const result = await resp.json();
          const score = Number(result.score || 0);
          const total = Number(result.total || 0);
          const details = Array.isArray(result.details) ? result.details : [];

          if (result.state && typeof result.state === 'object') {
            hydratedState = mergeState(result.state);
          }

          if (progressLabel) progressLabel.textContent = 'Completed';
          if (progressFill) progressFill.style.width = '100%';

          body.innerHTML = `
            <div class="quiz-results">
              <div class="quiz-results-score">Score: <strong>${score}</strong> / ${total}</div>
              <div class="quiz-results-list">
                ${details.map(d => `
                  <div class="quiz-results-row ${d.correct ? 'quiz-answer-correct' : 'quiz-answer-incorrect'}">
                    <span>Question ${d.question_id}</span>
                    <span>${d.correct ? 'Correct' : 'Incorrect'}</span>
                  </div>
                `).join('')}
              </div>
            </div>`;
          submitButton.style.display = 'none';

          if (typeof renderLearning === 'function') renderLearning();
          if (typeof openModuleDetails === 'function') openModuleDetails(module.id);
        } catch (e) {
          alert('Quiz submission failed. Try again later.');
          submitButton.disabled = false;
          submitButton.textContent = 'Submit Quiz';
        }
      };
    }
  }

  window.openQuiz = openQuiz;
  window.closeQuizModal = closeQuizModal;

  async function renderDashboard() {
    const currentUser = (await ensureCurrentUser()) || getCurrentUser();
    const state = getState();
    const visibleModules = getVisibleModules();

    const welcomeName = document.getElementById('dashboardWelcomeName');
    if (welcomeName) {
      welcomeName.textContent = `Welcome back, ${currentUser.name || 'Learner'}!`;
    }

    const welcomeMessage = document.getElementById('dashboardWelcomeMessage');
    if (welcomeMessage) {
      welcomeMessage.textContent = 'Ready to continue your structured FSL learning journey?';
    }

    const profileName = document.getElementById('dashboardProfileName');
    if (profileName) {
      profileName.textContent = currentUser.name || 'Learner';
    }

    const profileEmail = document.getElementById('dashboardProfileEmail');
    if (profileEmail) {
      profileEmail.textContent = currentUser.email || 'n/a';
    }

    const profileYear = document.getElementById('dashboardProfileYear');
    if (profileYear) {
      profileYear.textContent = getYearLabel(currentUser.yearLevel);
    }

    const profileMeta = document.getElementById('dashboardProfileMeta');
    if (profileMeta) {
      profileMeta.textContent = `${currentUser.email || ''} • ${getYearLabel(currentUser.yearLevel)}`;
    }

    const statMap = {
      dashboardPointsValue: state.points,
      dashboardModulesValue: state.completedActivities,
      dashboardRankValue: state.points > 0 ? `#${state.rank}` : 'Unranked',
      dashboardAccuracyValue: `${state.accuracy}%`
    };

    Object.keys(statMap).forEach(id => {
      const element = document.getElementById(id);
      if (element) {
        element.textContent = String(statMap[id]);
      }
    });

    const pointsMeta = document.getElementById('dashboardPointsMeta');
    if (pointsMeta) {
      pointsMeta.textContent = '';
    }

    const modulesMeta = document.getElementById('dashboardModulesMeta');
    if (modulesMeta) {
      modulesMeta.textContent = '';
    }

    const rankMeta = document.getElementById('dashboardRankMeta');
    if (rankMeta) {
      rankMeta.textContent = '';
    }

    const accuracyMeta = document.getElementById('dashboardAccuracyMeta');
    if (accuracyMeta) {
      accuracyMeta.textContent = '';
    }

    const progressContainer = document.getElementById('dashboardProgressList');
    if (progressContainer) {
      progressContainer.innerHTML = visibleModules.map(module => {
        const progress = getModuleProgress(state, module.id);
        return `
          <div class="progress-item">
            <div class="progress-info">
              <span class="progress-name">${module.title}</span>
              <span class="progress-percentage">${progress}%</span>
            </div>
            <div class="progress-bar"><div class="progress-fill" style="width: ${progress}%;"></div></div>
            <small>${progress >= 100 ? 'Completed' : progress > 0 ? `${progress}% complete` : 'Not started yet'}</small>
          </div>
        `;
      }).join('');
    }

    const performanceContainer = document.getElementById('dashboardPerformanceSummary');
    if (performanceContainer) {
      const strengths = state.performance.slice(0, 2);
      const needsWork = state.performance.slice(-2);
      performanceContainer.innerHTML = `
        <ul style="margin: 0; padding-left: 18px; color: #374151; line-height: 1.8;">
          <li>Strongest skills: ${strengths.map(item => `${item.label} (${item.value}%)`).join(', ')}</li>
          <li>Focus area: ${needsWork.map(item => `${item.label} (${item.value}%)`).join(', ')}</li>
          <li>Practice time this week: ${state.practiceMinutes} minutes</li>
          <li>Current learning streak: ${state.streak} days</li>
        </ul>
      `;
    }

    const recentActivity = document.getElementById('dashboardRecentActivityList');
    if (recentActivity) {
      renderRecentActivityList(recentActivity, state.recentActivity || []);
    }

    const achievements = document.getElementById('dashboardAchievementsGrid');
    if (achievements) {
      achievements.innerHTML = state.achievements.map(achievement => `
        <div class="achievement-badge ${achievement.earned ? 'earned' : 'locked'}">
          <div class="achievement-icon" style="background: ${achievement.earned ? 'linear-gradient(135deg, #2563eb 0%, #7c3aed 100%)' : '#e5e7eb'};">
            <i class="${achievement.icon}"></i>
          </div>
          <div class="achievement-name">${achievement.name}</div>
        </div>
      `).join('');
    }

    const leaderboard = document.getElementById('dashboardLeaderboardList');
    if (leaderboard) {
      leaderboard.innerHTML = '<li style="padding: 0.75rem 0; color: #666;">Loading live top learners...</li>';
    }

    const weeklyBars = document.getElementById('dashboardWeeklyBars');
    const weeklyLegend = document.getElementById('dashboardWeeklyLegend');
    const weeklySummary = document.getElementById('dashboardWeeklySummary');
    if (weeklyBars) {
      const labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
      const maxValue = Math.max.apply(null, state.weeklyActivity.concat([1]));
      weeklyBars.innerHTML = state.weeklyActivity.map((value, index) => {
        const height = Math.max(20, Math.round((value / maxValue) * 100));
        return `<div class="chart-bar${index === state.weeklyActivity.length - 1 ? ' active' : ''}" style="height: ${height}%;" data-day="${labels[index]}" data-value="${value}"></div>`;
      }).join('');
      if (weeklyLegend) {
        weeklyLegend.innerHTML = labels.map(label => `<span>${label}</span>`).join('');
      }
      if (weeklySummary) {
        weeklySummary.innerHTML = `
          <div class="summary-item"><i class="fas fa-clock"></i><span>${Math.round(state.practiceMinutes / 60)}h ${state.practiceMinutes % 60}min total practice time</span></div>
          <div class="summary-item"><i class="fas fa-check-circle"></i><span>${state.completedActivities} activities completed</span></div>
          <div class="summary-item"><i class="fas fa-star"></i><span>${state.points.toLocaleString()} points earned</span></div>
        `;
      }
    }
  }

  async function loadDashboardAsyncData() {
    try {
      const announcements = await loadPublicAnnouncements(3);
      const recentActivity = document.getElementById('dashboardRecentActivityList');
      if (recentActivity && announcements.length) {
        const state = getState();
        const announcementEntries = announcements.map(item => ({
          icon: '📢',
          text: String(item.title || 'Announcement').trim(),
          meta: 'Announcement',
        }));
        const mergedEntries = announcementEntries.concat(state.recentActivity || []).slice(0, 10);
        renderRecentActivityList(recentActivity, mergedEntries);
      }
    } catch (e) {
      // Silent
    }

    try {
      const payload = await loadLeaderboardFromBackend({ limit: 5 });
      const leaderboard = document.getElementById('dashboardLeaderboardList');
      if (leaderboard && payload) {
        const players = Array.isArray(payload.players) ? payload.players : [];
        leaderboard.innerHTML = players.length
          ? players.slice(0, 5).map((entry, index) => `
            <li style="display:flex; justify-content:space-between; padding: 0.75rem 0; border-bottom: 1px solid #eee; gap: 12px;">
              <span>${index + 1}. ${entry.name}${entry.isCurrentUser ? ' (You)' : ''}</span>
              <strong>${Number(entry.points || 0).toLocaleString()} pts</strong>
            </li>
          `).join('')
          : '<li style="padding: 0.75rem 0; color: #666;">No ranked learners yet. Complete an activity to appear here.</li>';

        const rankElement = document.getElementById('dashboardRankValue');
        const rankMeta = document.getElementById('dashboardRankMeta');
        const currentUser = payload.currentUser || null;
        if (rankElement && currentUser) {
          rankElement.textContent = Number(currentUser.points || 0) > 0 ? `#${Number(currentUser.rank || 0)}` : 'Unranked';
        }
        if (rankMeta && currentUser) {
          rankMeta.textContent = '';
        }
      }
    } catch (e) {
      // Silent
    }
  }

  function renderLearning() {
    const state = getState();
    const currentUser = getCurrentUser();
    const ownLevel = getLevelTextFromYear(currentUser.yearLevel || '1');
    const visibleModules = getVisibleModules();

    const overviewFill = document.getElementById('learningOverallProgressFill');
    const overviewText = document.getElementById('learningOverallProgressText');
    const modulesCompleted = document.getElementById('learningModulesCompleted');
    const totalPoints = document.getElementById('learningTotalPoints');
    const streakDays = document.getElementById('learningStreakDays');

    const completedCount = visibleModules.filter(module => getModuleProgress(state, module.id) >= 100).length;
    const averageProgress = visibleModules.length
      ? Math.round(visibleModules.reduce((sum, module) => sum + getModuleProgress(state, module.id), 0) / visibleModules.length)
      : 0;

    if (overviewFill) overviewFill.style.width = `${averageProgress}%`;
    if (overviewText) overviewText.textContent = `${averageProgress}%`;
    if (modulesCompleted) modulesCompleted.textContent = `${completedCount}/${visibleModules.length || 0}`;
    if (totalPoints) totalPoints.textContent = state.points.toLocaleString();
    if (streakDays) streakDays.textContent = `${state.streak} days`;

    const target = document.getElementById('learningModulesGrid');
    if (!target) return;

    const pagination = document.getElementById('learningModulesPagination');
    const PAGE_SIZE = 5;
    let activeLevel = target.getAttribute('data-active-level') || 'all';
    let currentPage = 1;

    const render = () => {
      const allModules = getFilteredModules(activeLevel);
      if (pagination) pagination.innerHTML = '';

      if (!allModules.length) {
        target.innerHTML = `
          <div class="table-container" style="padding:24px; text-align:center; color:#6b7280;">
            <div style="font-size:1.05rem; font-weight:700; margin-bottom:8px;">No modules available</div>
            <p style="margin:0;">Teachers will post learning modules here.</p>
          </div>
        `;
        return;
      }

      const totalPages = Math.max(1, Math.ceil(allModules.length / PAGE_SIZE));
      currentPage = Math.min(Math.max(1, currentPage), totalPages);
      const start = (currentPage - 1) * PAGE_SIZE;
      const modules = allModules.slice(start, start + PAGE_SIZE);

      const rows = modules.map(module => {
        const progress = getModuleProgress(state, module.id);
        const completed = progress >= 100;
        const moduleFiles = Array.isArray(module.files) ? module.files : [];
        const filesCount = moduleFiles.length;
        const previewFiles = moduleFiles.slice(0, 2);

        return `
          <tr class="module-table-row" onclick="openModuleDetails('${safeText(module.id)}')" role="button" tabindex="0">
            <td>
              <div class="learning-module-title">${safeText(module.title)}</div>
              <p class="learning-module-description">${safeText(module.description)}</p>
              <p class="learning-module-outcome"><strong>Outcome:</strong> ${safeText(module.outcome)}</p>
            </td>
            <td>
              <span class="module-chip" style="background:#eef2ff;color:#2563eb;">${safeText(module.level)} Year</span>
            </td>
            <td>
              <div class="learning-module-meta">
                <span class="module-chip">📚 ${Number(module.activities || 0)} Activities</span>
                <span class="module-chip">⏱️ ${Number(module.minutes || 0)} min</span>
                ${filesCount > 0 ? `<span class="module-chip">📎 ${filesCount} Materials</span>` : ''}
                <span class="module-chip">📝 ${Number(module.quizCount || 0)} Quizzes</span>
              </div>
              ${filesCount > 0 ? `<div class="learning-module-files-preview">${previewFiles.map(file => safeText(file.file_name)).join(' • ')}</div>` : ''}
            </td>
            <td>
              <div class="progress-bar" style="margin-bottom:10px;"><div class="progress-fill" style="width: ${progress}%;"></div></div>
              ${completed ? '<span class="completion-badge">✓ Completed</span>' : `<span style="color:#475569;font-size:0.92rem;">${progress}% complete</span>`}
            </td>
            <td>
              <div class="learning-module-actions" onclick="event.stopPropagation();">
                <button class="btn btn-primary" onclick="event.stopPropagation(); openModuleDetails('${safeText(module.id)}')">${completed ? 'Review' : progress > 0 ? 'Continue Learning' : 'Open Module'}</button>
              </div>
            </td>
          </tr>
        `;
      }).join('');

      target.innerHTML = `
        <table class="learning-modules-table">
          <thead>
            <tr>
              <th>Module</th>
              <th>Year</th>
              <th>Details</th>
              <th>Progress</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      `;

      if (pagination) {
        const total = allModules.length;
        const rangeStart = start + 1;
        const rangeEnd = Math.min(start + PAGE_SIZE, total);
        pagination.innerHTML = `
          <span style="color:#6b7280;">Showing ${rangeStart}-${rangeEnd} of ${total}</span>
          <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
            <button type="button" class="btn btn-secondary btn-sm" ${currentPage <= 1 ? 'disabled' : ''} id="learningModulesPrevBtn">Prev</button>
            <span style="color:#6b7280;">Page ${currentPage} of ${totalPages}</span>
            <button type="button" class="btn btn-secondary btn-sm" ${currentPage >= totalPages ? 'disabled' : ''} id="learningModulesNextBtn">Next</button>
          </div>
        `;

        const prevBtn = document.getElementById('learningModulesPrevBtn');
        if (prevBtn) prevBtn.addEventListener('click', () => { currentPage -= 1; render(); });
        const nextBtn = document.getElementById('learningModulesNextBtn');
        if (nextBtn) nextBtn.addEventListener('click', () => { currentPage += 1; render(); });
      }
    };

    render();

    const filterButtons = document.querySelectorAll('.filter-btn[data-level]');
    filterButtons.forEach(button => {
      const buttonLevel = String(button.getAttribute('data-level') || '').trim();
      button.classList.toggle('active', buttonLevel === activeLevel);
      if (button.dataset.filterBound) return;
      button.dataset.filterBound = 'true';
      button.addEventListener('click', function () {
        filterButtons.forEach(btn => btn.classList.remove('active'));
        this.classList.add('active');
        activeLevel = this.getAttribute('data-level') || 'all';
        target.setAttribute('data-active-level', activeLevel);
        currentPage = 1;
        render();
      });
    });

    const moduleSummary = document.getElementById('learningPathSummary');
    if (moduleSummary) {
      moduleSummary.textContent = `${currentUser.name || 'Learner'} is currently at ${currentUser.yearLevel ? getYearLabel(currentUser.yearLevel) : 'foundation'} level with ${averageProgress}% overall module progress.`;
    }
  }

  let activitiesSelectedCategory = 'all';

  function renderActivities() {
    const currentUser = getCurrentUser();
    const currentYear = String(currentUser.yearLevel || '1').trim();
    const yearLabel = getYearLabel(currentYear);
    const state = getState();
    const visibleModules = getVisibleModules();

    const title = document.getElementById('activitiesPageTitle');
    if (title) {
      title.textContent = 'Learning Activities';
    }

    const subtitle = document.getElementById('activitiesPageSubtitle');
    if (subtitle) {
      subtitle.textContent = 'Practice FSL through interactive games and exercises organized by year level';
    }

    const yearFilter = document.getElementById('activitiesYearFilter');
    if (yearFilter && currentYear) {
      yearFilter.value = currentYear;
      yearFilter.addEventListener('change', function () {
        const selected = String(this.value || 'all').trim();
        renderActivitiesContent(selected);
      });
    }

    function getDifficultyLabel(activitiesCount) {
      if (activitiesCount >= 18) return 'Hard';
      if (activitiesCount >= 10) return 'Medium';
      return 'Easy';
    }

    function getAccentStyle(index) {
      const palette = [
        'linear-gradient(135deg, #2563eb 0%, #7c3aed 100%)',
        'linear-gradient(135deg, #0d9488 0%, #10b981 100%)',
        'linear-gradient(135deg, #f97316 0%, #ec4899 100%)',
        'linear-gradient(135deg, #7c3aed 0%, #ec4899 100%)',
        'linear-gradient(135deg, #2563eb 0%, #0d9488 100%)',
        'linear-gradient(135deg, #10b981 0%, #f59e0b 100%)'
      ];
      return palette[index % palette.length];
    }

    function renderActivitiesContent(filterYear, category) {
      const container = document.getElementById('activitiesPageContent');
      if (!container) {
        return;
      }

      const filteredModules = visibleModules.filter(module => {
        if (filterYear === 'all') {
          return true;
        }
        return String(module.level || '').includes(String(getLevelTextFromYear(filterYear)));
      });

      // If a category other than 'all' is selected, show curated quick cards for that category
      if (category && category !== 'all') {
        if (category === 'translators') {
          window.location.href = 'translator.html';
          return;
        }
        if (category === 'mini_games') {
          window.location.href = 'games.html';
          return;
        }

        container.innerHTML = '';
        return;
      }

      const cardBlocks = filteredModules.length
        ? filteredModules.map((module, index) => {
            const progress = getModuleProgress(state, module.id);
            const completed = progress >= 100;
            const yearText = String(module.level || yearLabel).trim();
            return `
              <div class="activity-card card" data-year="${safeText(String(module.level || ''))}">
                <div class="activity-header">
                  <div class="activity-icon" style="background: ${getAccentStyle(index)};">
                    <i class="fas fa-graduation-cap"></i>
                  </div>
                  <span class="difficulty-badge ${getDifficultyLabel(module.activities).toLowerCase()}">${getDifficultyLabel(module.activities)}</span>
                </div>
                <h3 class="activity-title">${safeText(module.title)}</h3>
                <p class="activity-description">${safeText(module.description)}</p>
                <div class="activity-meta">
                  <span><i class="fas fa-clock"></i> ${Number(module.minutes || 0)} min</span>
                  <span><i class="fas fa-layer-group"></i> ${Number(module.activities || 0)} activities</span>
                  <span><i class="fas fa-star"></i> ${Math.max(50, Number(module.activities || 0) * 10)} pts</span>
                </div>
                <div class="activity-progress">
                  <div class="progress">
                    <div class="progress-bar" style="width: ${progress}%;"></div>
                  </div>
                  <span class="progress-text">${completed ? 'Completed' : `${progress}% complete`}</span>
                </div>
                <div class="activity-actions">
                  <button class="btn ${completed ? 'btn-primary' : 'btn-secondary'} btn-sm" onclick="window.location.href='activity.html?module=${encodeURIComponent(module.id)}${completed ? '&review=true' : ''}'">
                    <i class="fas ${completed ? 'fa-redo' : 'fa-play'}"></i> ${completed ? 'Retry' : progress > 0 ? 'Continue' : 'Start'}
                  </button>
                </div>
              </div>
            `;
          }).join('')
        : '';

      const quickToolsHtml = `
        <div class="quick-actions-section">
          <h2>Explore More</h2>
          <div class="quick-actions grid grid-2">
            <a href="translator.html" class="quick-action-card card">
              <div class="quick-icon" style="background: var(--gradient-primary);"><i class="fas fa-language"></i></div>
              <h3>Translators</h3>
              <p>Convert between text and sign language for seamless communication</p>
            </a>
            <a href="games.html" class="quick-action-card card">
              <div class="quick-icon" style="background: var(--gradient-warm);"><i class="fas fa-gamepad"></i></div>
              <h3>Mini Games</h3>
              <p>Learn sign language through fun and interactive games</p>
            </a>
          </div>
        </div>
      `;

      container.innerHTML = `
        <div class="section-header">
          <h2>${yearLabel} Activities</h2>
          <p>Progressive learning activities tailored for your level</p>
        </div>
        <div class="activities-grid grid grid-3">
          ${cardBlocks}
        </div>
        ${quickToolsHtml}
      `;
    }

    // wire category buttons
    const categoryContainer = document.getElementById('activitiesCategoryFilters');
    if (categoryContainer) {
      const buttons = categoryContainer.querySelectorAll('.category-btn[data-category]');
      buttons.forEach(btn => {
        btn.addEventListener('click', function () {
          buttons.forEach(b => b.classList.remove('active'));
          this.classList.add('active');
          activitiesSelectedCategory = String(this.getAttribute('data-category') || 'all');
          renderActivitiesContent(currentYear, activitiesSelectedCategory);
        });
      });
    }

    renderActivitiesContent(currentYear, activitiesSelectedCategory);
  }

  function clearViewedProfile() {
    try {
      localStorage.removeItem('kumpasViewedProfile');
    } catch (_) {
      // ignore storage errors
    }
  }

  function setProfileActionsEnabled(enabled) {
    const editButton = document.querySelector('.section-header .btn-text');
    if (editButton) editButton.style.display = enabled ? '' : 'none';

    const settingsSection = document.querySelectorAll('.profile-section')[2];
    if (settingsSection) settingsSection.style.display = enabled ? '' : 'none';

    const preferencesSection = document.querySelectorAll('.profile-section')[3];
    if (preferencesSection) preferencesSection.style.display = enabled ? '' : 'none';

    const avatarContainer = document.querySelector('.avatar-container');
    if (avatarContainer) avatarContainer.style.pointerEvents = enabled ? '' : 'none';
  }

  function renderViewingBanner(viewedName) {
    let banner = document.getElementById('profileViewingBanner');
    if (!viewedName) {
      if (banner) banner.remove();
      return;
    }

    if (!banner) {
      banner = document.createElement('div');
      banner.id = 'profileViewingBanner';
      banner.style.cssText = 'max-width:1200px;margin:1rem auto 0;padding:0.9rem 1.5rem;background:#eef3ff;border:1px solid #c7d7fb;border-radius:14px;display:flex;align-items:center;justify-content:space-between;gap:1rem;color:#16233f;font-weight:600;';
      const main = document.querySelector('main.profile-container');
      if (main) main.insertBefore(banner, main.firstChild);
    }

    banner.innerHTML = `
      <span>Viewing <strong>${safeText(viewedName)}</strong>'s profile</span>
      <button type="button" class="btn-secondary" id="profileBackToMineBtn">Back to my profile</button>
    `;

    const backButton = document.getElementById('profileBackToMineBtn');
    if (backButton) {
      backButton.addEventListener('click', function () {
        clearViewedProfile();
        renderProfile();
      });
    }
  }

  async function renderProfile() {
    const currentUser = (await ensureCurrentUser()) || getCurrentUser();

    let viewedEmail = '';
    try {
      viewedEmail = String(localStorage.getItem('kumpasViewedProfile') || '').trim().toLowerCase();
    } catch (_) {
      viewedEmail = '';
    }
    const isViewingOther = Boolean(viewedEmail) && viewedEmail !== String(currentUser.email || '').trim().toLowerCase();

    let profileUser = currentUser;
    let state = getState();

    if (isViewingOther) {
      const leaderboardPayload = await loadLeaderboardFromBackend({ limit: 500 });
      const players = leaderboardPayload && Array.isArray(leaderboardPayload.players) ? leaderboardPayload.players : [];
      const viewedEntry = players.find(entry => String(entry.email || '').trim().toLowerCase() === viewedEmail);

      if (!viewedEntry) {
        // Viewed player is no longer available (e.g. filtered out); fall back to own profile.
        clearViewedProfile();
      } else {
        const viewedState = await loadStateForEmail(viewedEntry.email);
        profileUser = {
          name: viewedEntry.name,
          email: viewedEntry.email,
          yearLevel: viewedEntry.yearLevel,
          role: viewedEntry.role,
          photoUrl: viewedEntry.photoUrl,
          avatarId: viewedEntry.avatarId,
        };
        state = viewedState || mergeState({
          points: viewedEntry.points,
          rank: viewedEntry.rank,
          accuracy: viewedEntry.accuracy,
          streak: viewedEntry.streak,
          completedActivities: viewedEntry.completedActivities,
          practiceMinutes: viewedEntry.practiceMinutes,
        });
      }
    }

    const viewingSomeoneElse = isViewingOther && profileUser !== currentUser;
    renderViewingBanner(viewingSomeoneElse ? (profileUser.name || 'Learner') : '');
    setProfileActionsEnabled(!viewingSomeoneElse);

    const name = document.getElementById('profileDisplayName');
    if (name) name.textContent = profileUser.name || 'Learner';

    const metaYear = document.getElementById('profileYearLevel');
    if (metaYear) metaYear.textContent = getYearLabel(profileUser.yearLevel);

    const email = document.getElementById('profileEmail');
    if (email) email.textContent = profileUser.email || '';

    const yearText = document.getElementById('profileYearText');
    if (yearText) yearText.textContent = getYearLabel(profileUser.yearLevel);

    const fullName = document.getElementById('profileFullName');
    if (fullName) fullName.textContent = profileUser.name || 'Learner';

    const studentId = document.getElementById('profileStudentId');
    if (studentId) {
      studentId.textContent = profileUser.id ? String(profileUser.id) : String(profileUser.email || '');
    }

    const points = document.getElementById('profilePoints');
    if (points) points.textContent = state.points.toLocaleString();

    const rank = document.getElementById('profileRank');
    if (rank) rank.textContent = state.points > 0 ? `#${state.rank}` : 'Unranked';

    if (!viewingSomeoneElse) {
      void (async () => {
        const payload = await loadLeaderboardFromBackend({ limit: 50 });
        const liveCurrentUser = payload && payload.currentUser ? payload.currentUser : null;
        if (rank) {
          rank.textContent = liveCurrentUser && Number(liveCurrentUser.points || 0) > 0
            ? `#${Number(liveCurrentUser.rank || 0)}`
            : 'Unranked';
        }
      })();
    }

    const stats = {
      profileModulesCompleted: Object.values(state.moduleProgress).filter(value => Number(value) >= 100).length,
      profileAccuracy: `${state.accuracy}%`,
      profileStreak: `${state.streak} days`,
      profilePracticeTime: `${Math.round(state.practiceMinutes / 60)} hrs`
    };

    Object.keys(stats).forEach(id => {
      const el = document.getElementById(id);
      if (el) el.textContent = stats[id];
    });

    const activitySummary = document.getElementById('profileActivitySummary');
    if (activitySummary) {
      const summaryItems = [
        { label: 'Activities Completed', value: Number(state.completedActivities || 0) },
        { label: 'Practice Minutes', value: Number(state.practiceMinutes || 0) },
        { label: 'Current Points', value: Number(state.points || 0).toLocaleString() },
        { label: 'Modules Completed', value: Object.values(state.moduleProgress).filter(value => Number(value) >= 100).length }
      ];

      activitySummary.innerHTML = summaryItems.map(item => `
        <div class="activity-item">
          <span>${item.label}</span>
          <span class="badge secondary">${item.value}</span>
        </div>
      `).join('');
    }

    const achievementsList = document.getElementById('profileAchievementsList');
    if (achievementsList) {
      const mapIcon = function (iconClass) {
        if (String(iconClass).indexOf('graduation-cap') !== -1) return '🎓';
        if (String(iconClass).indexOf('star') !== -1) return '⭐';
        if (String(iconClass).indexOf('lock') !== -1) return '🔒';
        return '🏅';
      };

      achievementsList.innerHTML = (state.achievements || []).map(item => `
        <div class="achievement" style="opacity: ${item.earned ? 1 : 0.55};">
          <span class="achievement-icon">${mapIcon(item.icon)}</span>
          <span class="achievement-name">${item.name}</span>
        </div>
      `).join('');
    }

    const certificatesList = document.getElementById('profileCertificatesList');
    if (certificatesList) {
      void (async () => {
        const certificates = await loadCertificatesForEmail(profileUser.email);
        if (!certificates.length) {
          certificatesList.innerHTML = `
            <div class="achievement" style="opacity: 0.55;">
              <span class="achievement-icon">📜</span>
              <span class="achievement-name">Complete a game's Hard difficulty to earn your first certificate!</span>
            </div>
          `;
          return;
        }

        certificatesList.innerHTML = certificates.map(item => `
          <div class="achievement">
            <span class="achievement-icon">📜</span>
            <span class="achievement-name">${safeText(item.title)}</span>
            ${viewingSomeoneElse ? '' : `<a href="${safeText(item.downloadUrl)}" target="_blank" rel="noopener" class="btn-secondary" style="margin-left:auto; padding:4px 12px; font-size:0.85em; white-space:nowrap;">Download</a>`}
          </div>
        `).join('');
      })();
    }

    const moduleProgressContainer = document.getElementById('profileModuleProgress');
    if (moduleProgressContainer) {
      moduleProgressContainer.innerHTML = getVisibleModules().slice(0, 4).map(module => {
        const progress = getModuleProgress(state, module.id);
        return `
          <div class="progress-item">
            <span>${module.title}</span>
            <div class="progress-bar"><div class="progress-fill" style="width: ${progress}%;"></div></div>
            <span class="progress-status">${getModuleStatus(progress)}</span>
          </div>
        `;
      }).join('');
    }

    const skillContainer = document.getElementById('profileSkillBreakdown');
    if (skillContainer) {
      skillContainer.innerHTML = state.performance.map(skill => `
        <div class="skill-item">
          <span class="skill-name">${skill.label}</span>
          <div class="skill-meter"><div class="skill-fill" style="width: ${skill.value}%;"></div></div>
          <span class="skill-value">${skill.value}%</span>
        </div>
      `).join('');
    }

    // Render profile avatar if available
    try {
      const avatarPlaceholder = document.querySelector('.avatar-placeholder');
      const photoUrl = (profileUser && (profileUser.photoUrl || profileUser.photo)) || '';
      const savedAvatar = viewingSomeoneElse ? String(profileUser.avatarId || '').trim() : getSelectedAvatar();
      if (avatarPlaceholder) {
        if (photoUrl) {
          avatarPlaceholder.innerHTML = `<img id="profileAvatarImg" src="${safeText(photoUrl)}" alt="Profile photo" style="width:100%;height:100%;border-radius:50%;object-fit:cover;opacity:0;transition:opacity 0.3s ease;" onload="this.style.opacity='1';">`;
        } else if (savedAvatar) {
          avatarPlaceholder.innerHTML = renderAvatarPreset(savedAvatar);
        } else {
          avatarPlaceholder.innerHTML = '<i class="fas fa-user" style="font-size:3.4rem;opacity:0.85;"></i>';
        }
      }
    } catch (e) {
      // ignore avatar rendering errors
    }
  }

  // Game-style character-select avatars, sourced from DiceBear's free,
  // open-license "Micah" avatar API (https://www.dicebear.com/styles/micah/) --
  // bold flat-color half-body portraits with a modern gaming-platform look.
  // Each preset pins an explicit hair/facialHair combo so the set stays a
  // deliberate, even split of masculine- and feminine-presenting characters
  // rather than whatever a bare seed happens to randomize to.
  const DICEBEAR_BASE = 'https://api.dicebear.com/9.x/micah/svg';

  function buildDicebearAvatarHtml(preset) {
    const params = new URLSearchParams({
      seed: preset.seed,
      backgroundColor: preset.to.replace('#', ''),
      backgroundType: 'gradientLinear',
      radius: '50',
      hair: preset.hair,
      hairColor: preset.hairColor,
      baseColor: preset.skin,
    });
    if (preset.facialHair) {
      params.set('facialHair', preset.facialHair);
      params.set('facialHairProbability', '100');
    } else {
      params.set('facialHairProbability', '0');
    }
    const url = `${DICEBEAR_BASE}?${params.toString()}`;
    return `<img src="${url}" alt="${preset.label}" loading="lazy" style="width:100%;height:100%;display:block;object-fit:cover;">`;
  }

  const AVATAR_PRESETS = [
    // Masculine-presenting
    { id: 'blue', from: '#8ec5ff', to: '#2563eb', seed: 'Rio', label: 'Rio', hair: 'fonze', hairColor: '2c1b18', skin: 'f2d3b1', facialHair: 'beard' },
    { id: 'green', from: '#9df5d1', to: '#059669', seed: 'Kai', label: 'Kai', hair: 'mrT', hairColor: '0f0d0c', skin: 'a26d3d', facialHair: 'scruff' },
    { id: 'orange', from: '#ffd2a1', to: '#ea580c', seed: 'Dex', label: 'Dex', hair: 'dougFunny', hairColor: '4a3222', skin: 'd8b088', facialHair: '' },
    { id: 'indigo', from: '#c7d2fe', to: '#4338ca', seed: 'Jett', label: 'Jett', hair: 'mrClean', hairColor: '1c1c1c', skin: 'edb98a', facialHair: 'beard' },
    { id: 'cyan', from: '#b3f5ff', to: '#0891b2', seed: 'Milo', label: 'Milo', hair: 'dannyPhantom', hairColor: '2c1b18', skin: 'ffd6b8', facialHair: 'scruff' },
    { id: 'teal', from: '#9ff5e8', to: '#0d9488', seed: 'Theo', label: 'Theo', hair: 'turban', hairColor: '2c1b18', skin: 'a26d3d', facialHair: 'beard' },
    // Feminine-presenting
    { id: 'purple', from: '#d9baff', to: '#7c3aed', seed: 'Vale', label: 'Vale', hair: 'full', hairColor: '6b3f2a', skin: 'f2d3b1', facialHair: '' },
    { id: 'pink', from: '#ffc2e2', to: '#db2777', seed: 'Mika', label: 'Mika', hair: 'pixie', hairColor: '2c1b18', skin: 'ffd6b8', facialHair: '' },
    { id: 'yellow', from: '#fff0b3', to: '#d97706', seed: 'Nova', label: 'Nova', hair: 'full', hairColor: 'a35c22', skin: 'edb98a', facialHair: '' },
    { id: 'red', from: '#ffb3b3', to: '#dc2626', seed: 'Remy', label: 'Remy', hair: 'pixie', hairColor: '922f1e', skin: 'd8b088', facialHair: '' },
    { id: 'lime', from: '#e4ffb3', to: '#65a30d', seed: 'Sana', label: 'Sana', hair: 'full', hairColor: '1c1c1c', skin: 'a26d3d', facialHair: '' },
    { id: 'rose', from: '#ffd6e7', to: '#e11d48', seed: 'Aiko', label: 'Aiko', hair: 'pixie', hairColor: '6b3f2a', skin: 'f2d3b1', facialHair: '' }
  ].map(preset => Object.assign({}, preset, {
    svg: buildDicebearAvatarHtml(preset)
  }));

  // The chosen preset avatar is persisted server-side on UserProfile.avatar_id
  // (see backend /api/profile/photo/). getSelectedAvatar() reads the value
  // already hydrated onto currentUserCache.avatarId by /api/auth/me/, so the
  // choice survives logout/login and is visible to other roles (teacher/admin).
  function getSelectedAvatar() {
    const currentUser = getCurrentUser();
    return String((currentUser && currentUser.avatarId) || '').trim();
  }

  async function setSelectedAvatar(avatarId) {
    const currentUser = (await ensureCurrentUser()) || getCurrentUser();
    const email = String(currentUser.email || '').trim();
    if (!email) return null;

    const form = new FormData();
    form.append('email', email);
    form.append('avatar_id', avatarId || '');

    try {
      const response = await fetch(`${API_BASE}/profile/photo/`, {
        method: 'POST',
        credentials: 'include',
        body: form,
      });
      if (!response.ok) return null;

      const payload = await response.json();
      currentUserCache = Object.assign({}, currentUserCache || currentUser, {
        avatarId: payload && payload.avatarId ? payload.avatarId : '',
        photoUrl: payload && payload.photoUrl ? payload.photoUrl : '',
      });
      return payload;
    } catch (_) {
      return null;
    }
  }

  function renderAvatarPreset(avatarId) {
    const preset = AVATAR_PRESETS.find(a => a.id === avatarId) || AVATAR_PRESETS[0];
    return `<div style="width:100%;height:100%;border-radius:50%;overflow:hidden;">${preset.svg}</div>`;
  }

  // Shared avatar markup builder so leaderboard/admin/instructor pages can
  // render the same photo-or-mascot avatar as the student's own profile.
  function renderAvatarMarkup(data) {
    const info = data && typeof data === 'object' ? data : {};
    const photoUrl = String(info.photoUrl || '').trim();
    const avatarId = String(info.avatarId || '').trim();
    if (photoUrl) {
      return `<img src="${safeText(photoUrl)}" alt="Profile photo" style="width:100%;height:100%;object-fit:cover;display:block;">`;
    }
    if (avatarId) {
      const preset = AVATAR_PRESETS.find(a => a.id === avatarId);
      if (preset) return preset.svg;
    }
    return '<div style="width:100%;height:100%;display:flex;align-items:center;justify-content:center;background:#e2e8f0;color:#94a3b8;font-size:60%;"><i class="fas fa-user"></i></div>';
  }

  function ensureAvatarPickerStyles() {
    if (document.getElementById('avatarPickerStyles')) return;
    const style = document.createElement('style');
    style.id = 'avatarPickerStyles';
    style.textContent = `
      #avatarPickerOverlay {
        position: fixed;
        inset: 0;
        background: rgba(15,23,42,0.6);
        backdrop-filter: blur(3px);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 9999;
        padding: 1rem;
        animation: kdAvatarFadeIn 0.2s ease;
      }
      @keyframes kdAvatarFadeIn { from { opacity: 0; } to { opacity: 1; } }
      @keyframes kdAvatarPopIn {
        from { opacity: 0; transform: translateY(14px) scale(0.97); }
        to { opacity: 1; transform: translateY(0) scale(1); }
      }
      .avatar-picker-panel {
        background: #fff;
        border-radius: 22px;
        width: 100%;
        max-width: 460px;
        max-height: 90vh;
        overflow-y: auto;
        box-shadow: 0 30px 70px rgba(15,23,42,0.35);
        animation: kdAvatarPopIn 0.25s cubic-bezier(.2,.8,.3,1.1);
        font-family: 'Inter', -apple-system, sans-serif;
      }
      .avatar-picker-header {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 1rem;
        padding: 1.6rem 1.75rem 0.25rem;
      }
      .avatar-picker-header h3 {
        margin: 0 0 0.3rem;
        color: #1e293b;
        font-family: 'Poppins', 'Inter', sans-serif;
        font-size: 1.3rem;
        font-weight: 800;
      }
      .avatar-picker-header p {
        margin: 0;
        color: #667085;
        font-size: 0.88rem;
      }
      .avatar-picker-close {
        background: #f1f5f9;
        border: none;
        color: #64748b;
        width: 34px;
        height: 34px;
        min-width: 34px;
        border-radius: 50%;
        cursor: pointer;
        font-size: 0.95rem;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: background 0.2s ease, color 0.2s ease, transform 0.2s ease;
      }
      .avatar-picker-close:hover {
        background: #e2e8f0;
        color: #1e293b;
        transform: rotate(90deg);
      }
      .avatar-picker-preview-row {
        display: flex;
        align-items: center;
        gap: 1rem;
        padding: 1rem 1.75rem 0.5rem;
      }
      .avatar-picker-preview-circle {
        width: 76px;
        height: 76px;
        min-width: 76px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 2.4rem;
        background: #eef2ff;
        border: 3px solid #fff;
        box-shadow: 0 6px 18px rgba(37,99,235,0.18);
        overflow: hidden;
        transition: transform 0.2s ease;
      }
      .avatar-picker-preview-circle svg,
      .avatar-picker-preview-circle img {
        width: 100%;
        height: 100%;
        display: block;
      }
      .avatar-picker-preview-text {
        display: flex;
        flex-direction: column;
        gap: 0.15rem;
      }
      .avatar-picker-preview-text strong {
        color: #1e293b;
        font-size: 0.95rem;
      }
      .avatar-picker-preview-text span {
        color: #94a3b8;
        font-size: 0.8rem;
      }
      .avatar-picker-section-label {
        margin: 0.6rem 1.75rem 0.75rem;
        font-size: 0.78rem;
        font-weight: 800;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: #94a3b8;
      }
      .avatar-picker-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 1rem;
        justify-items: center;
        padding: 0 1.75rem 0.5rem;
      }
      .avatar-option {
        width: 64px;
        height: 64px;
        border-radius: 50%;
        border: 3px solid transparent;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: transform 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease;
        position: relative;
        padding: 0;
        overflow: hidden;
        background: #fff;
      }
      .avatar-option svg,
      .avatar-option img {
        width: 100%;
        height: 100%;
        display: block;
      }
      .avatar-option:hover {
        transform: translateY(-3px) scale(1.05);
        box-shadow: 0 8px 18px rgba(15,23,42,0.2);
      }
      .avatar-option.selected {
        border-color: #2563eb;
        box-shadow: 0 0 0 4px rgba(37,99,235,0.15);
      }
      .avatar-option-check {
        position: absolute;
        bottom: -3px;
        right: -3px;
        width: 20px;
        height: 20px;
        border-radius: 50%;
        background: #2563eb;
        color: #fff;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.65rem;
        border: 2px solid #fff;
      }
      .avatar-picker-divider {
        border: none;
        border-top: 1px solid #eef1f6;
        margin: 1.1rem 1.75rem 0;
      }
      .avatar-picker-upload {
        margin: 1rem 1.75rem 0;
        display: flex;
        align-items: center;
        gap: 0.9rem;
        padding: 1rem 1.1rem;
        border: 1.5px dashed #c7d2fe;
        border-radius: 14px;
        background: #f8faff;
        cursor: pointer;
        transition: background 0.2s ease, border-color 0.2s ease;
        text-align: left;
      }
      .avatar-picker-upload:hover {
        background: #eef2ff;
        border-color: #2563eb;
      }
      .avatar-picker-upload-icon {
        width: 42px;
        height: 42px;
        min-width: 42px;
        border-radius: 50%;
        background: linear-gradient(135deg, #2563eb, #7c3aed);
        color: #fff;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.1rem;
      }
      .avatar-picker-upload-text strong {
        display: block;
        color: #1e293b;
        font-size: 0.92rem;
      }
      .avatar-picker-upload-text span {
        color: #94a3b8;
        font-size: 0.78rem;
      }
      .avatar-picker-footer {
        display: flex;
        justify-content: flex-end;
        gap: 0.7rem;
        padding: 1.25rem 1.75rem 1.6rem;
      }
      .avatar-picker-footer button {
        padding: 0.65rem 1.3rem;
        border-radius: 999px;
        font-weight: 700;
        font-size: 0.88rem;
        cursor: pointer;
        border: none;
        transition: transform 0.15s ease, background 0.15s ease;
      }
      .avatar-picker-footer button:hover { transform: translateY(-1px); }
      #avatarPickerRemove {
        background: #fef2f2;
        color: #dc2626;
      }
      #avatarPickerRemove:hover { background: #fee2e2; }
      #avatarPickerCancel {
        background: #f1f5f9;
        color: #475569;
      }
      #avatarPickerCancel:hover { background: #e2e8f0; }
      @media (max-width: 480px) {
        .avatar-picker-grid { grid-template-columns: repeat(4, 1fr); gap: 0.7rem; }
        .avatar-option { width: 54px; height: 54px; font-size: 1.6rem; }
      }
    `;
    document.head.appendChild(style);
  }

  function chooseAvatar() {
    if (document.getElementById('avatarPickerOverlay')) return;
    ensureAvatarPickerStyles();

    const currentUser = getCurrentUser();
    const photoUrl = (currentUser && (currentUser.photoUrl || currentUser.photo)) || '';
    let currentAvatar = getSelectedAvatar();

    const overlay = document.createElement('div');
    overlay.id = 'avatarPickerOverlay';

    const panel = document.createElement('div');
    panel.className = 'avatar-picker-panel';

    function previewHtml() {
      if (photoUrl) {
        return `<img src="${safeText(photoUrl)}" alt="Current photo" style="width:100%;height:100%;object-fit:cover;">`;
      }
      if (currentAvatar) {
        const preset = AVATAR_PRESETS.find(a => a.id === currentAvatar);
        if (preset) {
          return preset.svg;
        }
      }
      return '<span style="font-size:2.4rem;">👤</span>';
    }

    const optionsHtml = AVATAR_PRESETS.map(preset => `
      <button type="button" class="avatar-option${preset.id === currentAvatar ? ' selected' : ''}" data-avatar-id="${preset.id}" aria-label="Choose ${preset.id} avatar">
        ${preset.svg}
        ${preset.id === currentAvatar ? '<span class="avatar-option-check"><i class="fas fa-check"></i></span>' : ''}
      </button>
    `).join('');

    panel.innerHTML = `
      <div class="avatar-picker-header">
        <div>
          <h3>Update Your Photo</h3>
          <p>Pick a fun avatar or upload your own picture.</p>
        </div>
        <button type="button" class="avatar-picker-close" id="avatarPickerClose" aria-label="Close"><i class="fas fa-times"></i></button>
      </div>
      <div class="avatar-picker-preview-row">
        <div class="avatar-picker-preview-circle" id="avatarPickerPreview">${previewHtml()}</div>
        <div class="avatar-picker-preview-text">
          <strong>This is how others will see you</strong>
          <span>Choose an avatar below or upload a photo</span>
        </div>
      </div>
      <div class="avatar-picker-section-label">Preset Avatars</div>
      <div class="avatar-picker-grid">${optionsHtml}</div>
      <hr class="avatar-picker-divider">
      <button type="button" class="avatar-picker-upload" id="avatarPickerUpload">
        <span class="avatar-picker-upload-icon"><i class="fas fa-camera"></i></span>
        <span class="avatar-picker-upload-text">
          <strong>Upload your own photo</strong>
          <span>JPG or PNG, up to 5 MB</span>
        </span>
      </button>
      <div class="avatar-picker-footer">
        <button type="button" id="avatarPickerRemove">Remove Photo</button>
        <button type="button" id="avatarPickerCancel">Cancel</button>
      </div>
    `;

    overlay.appendChild(panel);
    document.body.appendChild(overlay);

    function close() {
      document.removeEventListener('keydown', onKeydown);
      overlay.remove();
    }

    function onKeydown(e) {
      if (e.key === 'Escape') close();
    }
    document.addEventListener('keydown', onKeydown);

    overlay.addEventListener('click', function (e) {
      if (e.target === overlay) close();
    });
    panel.querySelector('#avatarPickerClose').addEventListener('click', close);
    panel.querySelector('#avatarPickerCancel').addEventListener('click', close);
    panel.querySelector('#avatarPickerRemove').addEventListener('click', async function () {
      const btn = this;
      btn.disabled = true;
      const avatarPlaceholder = document.querySelector('.avatar-placeholder');
      const prevHtml = avatarPlaceholder ? avatarPlaceholder.innerHTML : '';
      if (avatarPlaceholder) avatarPlaceholder.textContent = '👤';
      const result = await setSelectedAvatar('');
      btn.disabled = false;
      if (!result) {
        if (avatarPlaceholder) avatarPlaceholder.innerHTML = prevHtml;
        alert('Could not remove avatar. Please try again.');
        return;
      }
      close();
    });
    panel.querySelector('#avatarPickerUpload').addEventListener('click', function () {
      close();
      uploadPhoto();
    });

    panel.querySelectorAll('.avatar-option').forEach(btn => {
      btn.addEventListener('click', async function () {
        const avatarId = this.getAttribute('data-avatar-id');
        const avatarPlaceholder = document.querySelector('.avatar-placeholder');
        const prevHtml = avatarPlaceholder ? avatarPlaceholder.innerHTML : '';
        if (avatarPlaceholder) avatarPlaceholder.innerHTML = renderAvatarPreset(avatarId);
        panel.querySelectorAll('.avatar-option').forEach(b => { b.disabled = true; });
        const result = await setSelectedAvatar(avatarId);
        panel.querySelectorAll('.avatar-option').forEach(b => { b.disabled = false; });
        if (!result) {
          if (avatarPlaceholder) avatarPlaceholder.innerHTML = prevHtml;
          alert('Could not save avatar. Please try again.');
          return;
        }
        close();
      });
    });
  }

  async function uploadPhoto() {
    const currentUser = (await ensureCurrentUser()) || getCurrentUser();
    const email = String(currentUser.email || '').trim();
    if (!email) {
      alert('No authenticated user found. Please login first.');
      return;
    }

    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/*';
    input.addEventListener('change', async function () {
      const file = input.files && input.files[0];
      if (!file) return;
      if (file.size > 5 * 1024 * 1024) {
        alert('Please choose an image smaller than 5 MB.');
        return;
      }

      const form = new FormData();
      form.append('email', email);
      form.append('photo', file);

      const avatarPlaceholder = document.querySelector('.avatar-placeholder');
      const prevAvatarHtml = avatarPlaceholder ? avatarPlaceholder.innerHTML : '';

      if (avatarPlaceholder) {
        avatarPlaceholder.innerHTML = '<i class="fas fa-spinner fa-spin" style="font-size:2.2rem;"></i>';
      }

      try {
        const response = await fetch(`${API_BASE}/profile/photo/`, {
          method: 'POST',
          credentials: 'include',
          body: form,
        });

        if (!response.ok) {
          const err = await response.json().catch(() => ({}));
          if (avatarPlaceholder) avatarPlaceholder.innerHTML = prevAvatarHtml;
          alert(err && err.error ? `Upload failed: ${err.error}` : 'Upload failed. Try again.');
          return;
        }

        const payload = await response.json();
        const photoUrl = payload && payload.photoUrl ? payload.photoUrl : null;
        if (photoUrl) {
          currentUserCache = Object.assign({}, currentUserCache || currentUser, {
            photoUrl,
            avatarId: payload && payload.avatarId ? payload.avatarId : '',
          });

          if (avatarPlaceholder) {
            avatarPlaceholder.innerHTML = `<img id="profileAvatarImg" src="${safeText(photoUrl)}" alt="Profile photo" style="width:100%;height:100%;border-radius:50%;object-fit:cover;opacity:0;transition:opacity 0.3s ease;">`;
            const img = avatarPlaceholder.querySelector('img');
            if (img) {
              setTimeout(() => { img.style.opacity = '1'; }, 10);
            }
          }
        } else {
          if (avatarPlaceholder) avatarPlaceholder.innerHTML = prevAvatarHtml;
          alert('Upload succeeded but no photo URL returned');
        }
      } catch (e) {
        if (avatarPlaceholder) avatarPlaceholder.innerHTML = prevAvatarHtml;
        alert('Photo upload failed. Please try again later.');
      }
    });

    // trigger file chooser
    input.click();
  }

  function getCurrentUserYear() {
    return getYearNumberFromLevel(getCurrentUser().yearLevel || '1');
  }

  function applyYearAccessRules() {
    const body = document.body;
    if (!body) {
      return;
    }

    const currentYear = getCurrentUserYear();
    const requiredYear = String(body.getAttribute('data-required-year') || '').trim();

    // If we're on a games page, do not enforce the global required-year redirect
    // or hide per-item elements by year. Games should be openable regardless of year.
    const pathname = String(window.location.pathname || '').toLowerCase();
    const isGamesPage = pathname.includes('game') || pathname.includes('games.html');
    if (isGamesPage) {
      // Ensure all year-tagged elements are visible on games pages
      document.querySelectorAll('[data-year]').forEach(el => {
        el.style.display = '';
      });
      return;
    }

    document.querySelectorAll('[data-year]').forEach(element => {
      const elementYear = String(element.getAttribute('data-year') || '').trim();
      if (!elementYear || elementYear === 'all') {
        element.style.display = '';
        return;
      }

      if (elementYear === currentYear) {
        element.style.display = '';
      } else {
        element.style.display = 'none';
      }
    });

    const yearLabel = getYearLabel(currentYear);
    const yearHeading = document.querySelector('[data-year-heading]');
    if (yearHeading) {
      yearHeading.textContent = `${yearLabel} Activities`;
    }
  }

  function initNavbarUserMenu() {
    const navbar = document.querySelector('.navbar');
    if (!navbar || navbar.querySelector('.nav-user-menu')) {
      return;
    }

    const profileLink = navbar.querySelector('a.profile-link') || navbar.querySelector('a[href="profile.html"]');
    const logoutLink = navbar.querySelector('a.logout-btn') || navbar.querySelector('a[href="index.html"]');

    if (!profileLink || !logoutLink) {
      return;
    }

    const profileTarget = profileLink.closest('li') || profileLink;
    const logoutTarget = logoutLink.closest('li') || logoutLink;
    profileTarget.style.display = 'none';
    logoutTarget.style.display = 'none';

    const menu = document.createElement('div');
    menu.className = 'nav-user-menu';

    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'nav-user-toggle';
    button.setAttribute('aria-label', 'Open user menu');
    button.innerHTML = '<i class="fas fa-user-circle"></i>';

    const dropdown = document.createElement('div');
    dropdown.className = 'nav-user-dropdown';

    const profileItem = document.createElement('a');
    profileItem.href = profileLink.getAttribute('href') || 'profile.html';
    profileItem.innerHTML = '<i class="fas fa-id-badge"></i><span>Profile</span>';

    const logoutItem = document.createElement('a');
    logoutItem.href = logoutLink.getAttribute('href') || 'index.html';
    logoutItem.className = 'logout';
    logoutItem.innerHTML = '<i class="fas fa-right-from-bracket"></i><span>Logout</span>';

    dropdown.appendChild(profileItem);
    dropdown.appendChild(logoutItem);
    menu.appendChild(button);
    menu.appendChild(dropdown);

    const appendTarget = navbar.querySelector('.navbar-container') || navbar;
    appendTarget.appendChild(menu);

    button.addEventListener('click', function (event) {
      event.preventDefault();
      event.stopPropagation();
      dropdown.classList.toggle('open');
    });

    document.addEventListener('click', function (event) {
      if (!menu.contains(event.target)) {
        dropdown.classList.remove('open');
      }
    });
  }

  async function loadDashboardAsyncData() {
    try {
      const announcements = await loadPublicAnnouncements(3);
      const recentActivity = document.getElementById('dashboardRecentActivityList');
      if (recentActivity && announcements.length) {
        const state = getState();
        const announcementEntries = announcements.map(item => ({
          icon: '📢',
          text: String(item.title || 'Announcement').trim(),
          meta: 'Announcement',
        }));
        const mergedEntries = announcementEntries.concat(state.recentActivity || []).slice(0, 10);
        renderRecentActivityList(recentActivity, mergedEntries);
      }
    } catch (e) {
      // Silent
    }

    try {
      const payload = await loadLeaderboardFromBackend({ limit: 5 });
      const leaderboard = document.getElementById('dashboardLeaderboardList');
      if (leaderboard && payload) {
        const players = Array.isArray(payload.players) ? payload.players : [];
        leaderboard.innerHTML = players.length
          ? players.slice(0, 5).map((entry, index) => `
            <li style="display:flex; justify-content:space-between; padding: 0.75rem 0; border-bottom: 1px solid #eee; gap: 12px;">
              <span>${index + 1}. ${entry.name}${entry.isCurrentUser ? ' (You)' : ''}</span>
              <strong>${Number(entry.points || 0).toLocaleString()} pts</strong>
            </li>
          `).join('')
          : '<li style="padding: 0.75rem 0; color: #666;">No ranked learners yet. Complete an activity to appear here.</li>';

        const rankElement = document.getElementById('dashboardRankValue');
        const rankMeta = document.getElementById('dashboardRankMeta');
        const currentUser = payload.currentUser || null;
        if (rankElement && currentUser) {
          rankElement.textContent = Number(currentUser.points || 0) > 0 ? `#${Number(currentUser.rank || 0)}` : 'Unranked';
        }
        if (rankMeta && currentUser) {
          rankMeta.textContent = Number(currentUser.points || 0) > 0
            ? `Live rank from the leaderboard: #${Number(currentUser.rank || 0)}`
            : 'No rank yet until you earn your first points';
        }
      }
    } catch (e) {
      // Silent
    }
  }

  function getCurrentPageType() {
    const pathname = window.location.pathname.toLowerCase();
    if (pathname.includes('profile')) return 'profile';
    if (pathname.includes('learning')) return 'learning';
    if (pathname.includes('activities')) return 'activities';
    if (pathname.includes('dashboard')) return 'dashboard';
    if (pathname.includes('instructor')) return 'instructor';
    if (pathname.includes('admin')) return 'admin';
    return 'unknown';
  }

  async function hydrateAndRender() {
    const pageType = getCurrentPageType();
    
    if (!hydratedState) {
      hydratedState = getState();
    }

    // Render page-specific content once
    if (pageType === 'dashboard' || pageType === 'unknown') {
      try { await renderDashboard(); } catch (e) { console.error('renderDashboard error:', e); }
      // Load async data after small delay
      setTimeout(() => {
        loadDashboardAsyncData().catch(e => console.error('loadDashboardAsyncData error:', e));
      }, 500);
    } else if (pageType === 'learning') {
      try {
        await loadStudentContentFromBackend();
      } catch (e) {
        console.error('loadStudentContentFromBackend error:', e);
      }
      try { renderLearning(); } catch (e) { console.error('renderLearning error:', e); }
    } else if (pageType === 'activities') {
      try { renderActivities(); } catch (e) { console.error('renderActivities error:', e); }
    } else if (pageType === 'profile') {
      try { await renderProfile(); } catch (e) { console.error('renderProfile error:', e); }
    }
  }

  // Admin/instructor dashboards (.dashboard-layout + .dashboard-sidebar) have
  // no mobile drawer behavior on their own -- below the sidebar breakpoint the
  // sidebar just stacks in normal flow. This injects a toggle button and a
  // backdrop so the sidebar can slide in/out as an overlay on small screens
  // without shifting the rest of the layout.
  function initDashboardSidebar() {
    const layout = document.querySelector('.dashboard-layout');
    const sidebar = document.querySelector('.dashboard-sidebar');
    if (!layout || !sidebar || sidebar.dataset.drawerBound) return;
    sidebar.dataset.drawerBound = 'true';

    const toggle = document.createElement('button');
    toggle.type = 'button';
    toggle.className = 'sidebar-toggle';
    toggle.setAttribute('aria-label', 'Toggle menu');
    toggle.setAttribute('aria-expanded', 'false');
    toggle.innerHTML = '<i class="fas fa-bars"></i><span>Menu</span>';

    const backdrop = document.createElement('div');
    backdrop.className = 'sidebar-backdrop';

    layout.insertBefore(toggle, sidebar);
    layout.appendChild(backdrop);

    function closeSidebar() {
      sidebar.classList.remove('open');
      backdrop.classList.remove('open');
      toggle.setAttribute('aria-expanded', 'false');
      document.body.classList.remove('sidebar-open-lock');
    }

    function openSidebar() {
      sidebar.classList.add('open');
      backdrop.classList.add('open');
      toggle.setAttribute('aria-expanded', 'true');
      document.body.classList.add('sidebar-open-lock');
    }

    toggle.addEventListener('click', function () {
      if (sidebar.classList.contains('open')) {
        closeSidebar();
      } else {
        openSidebar();
      }
    });

    backdrop.addEventListener('click', closeSidebar);

    sidebar.querySelectorAll('a').forEach(function (link) {
      link.addEventListener('click', function () {
        if (window.matchMedia('(max-width: 900px)').matches) {
          closeSidebar();
        }
      });
    });

    window.addEventListener('resize', function () {
      if (!window.matchMedia('(max-width: 900px)').matches) {
        closeSidebar();
      }
    });
  }

  // Mirrors the hamburger toggle in js/main.js -- duplicated here (not
  // imported) because this is a no-build-step static site, and not every
  // page that needs it also loads main.js.
  function initHamburgerMenu() {
    const hamburger = document.getElementById('hamburger');
    const navMenu = document.getElementById('navMenu');
    if (!hamburger || !navMenu || hamburger.dataset.bound) return;
    hamburger.dataset.bound = 'true';

    hamburger.addEventListener('click', function () {
      navMenu.classList.toggle('active');
      hamburger.classList.toggle('active');
    });

    navMenu.querySelectorAll('.nav-link').forEach(function (link) {
      link.addEventListener('click', function () {
        navMenu.classList.remove('active');
        hamburger.classList.remove('active');
      });
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    initNavbarUserMenu();
    initHamburgerMenu();
    initDashboardSidebar();
    applyYearAccessRules();
    hydrateAndRender();
  });

  window.KumpasPortal = {
    DEFAULT_STATE,
    getCurrentUser,
    ensureCurrentUser,
    getState,
    loadStateFromBackend,
    loadLeaderboardFromBackend,
    loadPublicAnnouncements,
    loadStudentContentFromBackend,
    applyYearAccessRules,
    saveState,
    updateState,
    recordProgress,
    renderDashboard,
    renderLearning,
    renderActivities,
    renderProfile,
    uploadPhoto,
    chooseAvatar,
    renderAvatarMarkup,
    getVisibleModules,
    getModuleById,
    getModuleProgress
  };
  // Backwards compatibility: allow inline onclick="uploadPhoto()" in profile.html
  window.uploadPhoto = function () {
    if (window.KumpasPortal && typeof window.KumpasPortal.uploadPhoto === 'function') {
      return window.KumpasPortal.uploadPhoto();
    }
    return null;
  };
  window.chooseAvatar = function () {
    if (window.KumpasPortal && typeof window.KumpasPortal.chooseAvatar === 'function') {
      return window.KumpasPortal.chooseAvatar();
    }
    return null;
  };
})();
