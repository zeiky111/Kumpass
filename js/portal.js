(function () {
  const STORAGE_KEY_PREFIX = 'kumpasLearningState';
  const API_BASE = localStorage.getItem('kumpasApiBase') || 'http://127.0.0.1:8000/api';
  const DEFAULT_USER_NAME = 'Learner';
  const DEFAULT_USER_EMAIL = 'student@kumpas.local';
  let hydratedState = null;
  let studentContentCache = null;

  const MODULES = [
    {
      id: 'lesson1',
      level: '1st',
      title: 'Lesson 1: Basic Finger Spelling',
      outcome: 'Recognize the alphabet and build accurate finger shapes for spelling.',
      description: 'Start with the alphabet, hand positions, and visual recognition drills that support reading and spelling.',
      activities: 4,
      minutes: 45,
      progressKey: 'lesson1',
      unlocks: 'Prepares learners for everyday word recognition and camera-based practice.'
    },
    {
      id: 'lesson2',
      level: '1st',
      title: 'Lesson 2: Common Everyday Signs',
      outcome: 'Translate everyday words into clear and meaningful signs.',
      description: 'Build vocabulary for common communication needs such as greetings, thanks, requests, and polite expressions.',
      activities: 5,
      minutes: 60,
      progressKey: 'lesson2',
      unlocks: 'Supports short conversational phrases and game-based practice.'
    },
    {
      id: 'lesson3',
      level: '1st',
      title: 'Lesson 3: Greetings & Polite Expressions',
      outcome: 'Use greetings and courteous responses in simple communication.',
      description: 'Practice hello, how are you, thank you, sorry, and related forms of respectful interaction.',
      activities: 3,
      minutes: 30,
      progressKey: 'lesson3',
      unlocks: 'Prepares learners for real-life introductions and short exchanges.'
    },
    {
      id: 'lesson4',
      level: '2nd',
      title: 'Lesson 4: Family & Relationships',
      outcome: 'Describe family members and people around you with accuracy.',
      description: 'Learn signs for family, relatives, and relationship words that appear in daily conversation.',
      activities: 6,
      minutes: 75,
      progressKey: 'lesson4',
      unlocks: 'Supports sentence building and scenario-based communication.'
    },
    {
      id: 'lesson5',
      level: '2nd',
      title: 'Lesson 5: Numbers & Counting',
      outcome: 'Represent numbers and quantity clearly in sign language.',
      description: 'Learn numerical signs, counting patterns, and number-based expressions used in practical settings.',
      activities: 5,
      minutes: 60,
      progressKey: 'lesson5',
      unlocks: 'Supports schedules, ages, quantities, and ranking tasks.'
    },
    {
      id: 'lesson6',
      level: '3rd',
      title: 'Lesson 6: Sign Language Grammar',
      outcome: 'Structure signs into clearer and more accurate messages.',
      description: 'Focus on word order, sentence patterns, and the grammar needed for understandable communication.',
      activities: 8,
      minutes: 100,
      progressKey: 'lesson6',
      unlocks: 'Prepares learners for long-form communication and contextual sentences.'
    },
    {
      id: 'lesson7',
      level: '3rd',
      title: 'Lesson 7: Emotions & Expressions',
      outcome: 'Express feelings with appropriate facial and body cues.',
      description: 'Use signs for happy, sad, sorry, excited, and related emotions with correct expression.',
      activities: 7,
      minutes: 85,
      progressKey: 'lesson7',
      unlocks: 'Improves comprehension and natural communication in conversations.'
    },
    {
      id: 'lesson8',
      level: '4th',
      title: 'Lesson 8: Complex Conversations',
      outcome: 'Handle practical conversations with confidence and clarity.',
      description: 'Apply learned signs in scenario-based dialogue, questions, responses, and more advanced communication.',
      activities: 10,
      minutes: 120,
      progressKey: 'lesson8',
      unlocks: 'Focuses on real-world communication, performance, and fluency.'
    }
  ];

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
    recentActivity: [
      { icon: '📚', text: 'Ready to start learning', meta: 'No progress yet' }
    ],
    achievements: [
      { icon: 'fas fa-graduation-cap', name: 'Quick Learner', earned: false },
      { icon: 'fas fa-star', name: 'Perfect Score', earned: false },
      { icon: 'fas fa-lock', name: 'Master Signer', earned: false },
      { icon: 'fas fa-lock', name: 'FSL Expert', earned: false },
      { icon: 'fas fa-lock', name: 'Champion', earned: false }
    ],
    leaderboard: [],
    performance: [
      { label: 'Sign Recognition', value: 0 },
      { label: 'Finger-Spelling', value: 0 },
      { label: 'Sign Grammar', value: 0 },
      { label: 'Communication', value: 0 }
    ]
  };

  function getStorageKey(user) {
    const email = String(user && user.email ? user.email : 'guest').toLowerCase().trim();
    return `${STORAGE_KEY_PREFIX}:${email}`;
  }

  function buildSeedState(user) {
    return Object.assign({}, DEFAULT_STATE, {
      recentActivity: [
        { icon: '📚', text: 'Ready to start learning', meta: 'No progress yet' }
      ]
    });
  }

  function getCurrentUser() {
    try {
      const stored = JSON.parse(localStorage.getItem('currentUser'));
      if (stored && stored.email) {
        return stored;
      }
    } catch (_) {
      // ignore
    }

    return {
      name: DEFAULT_USER_NAME,
      email: DEFAULT_USER_EMAIL,
      yearLevel: '1',
      role: 'student'
    };
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

  function mapBackendModule(module, index) {
    const key = String((module && module.module_key) || '').trim() || `module${index + 1}`;
    const title = String((module && module.title) || `Module ${index + 1}`).trim();
    const description = String((module && module.description) || 'Structured sign language practice.').trim();
    const activities = Number((module && module.activities_count) || 4);
    const yearLevel = String((module && module.year_level) || '1').trim();
    const level = getLevelTextFromYear(yearLevel);

    return {
      id: key,
      level,
      title,
      outcome: `Focus area for ${getYearLabel(yearLevel)} learners.`,
      description,
      activities: Number.isFinite(activities) ? activities : 4,
      minutes: Math.max(20, (Number.isFinite(activities) ? activities : 4) * 15),
      progressKey: key,
      unlocks: 'Unlocks the next guided activities and game challenges.'
    };
  }

  function getVisibleModules() {
    if (studentContentCache && Array.isArray(studentContentCache.modules) && studentContentCache.modules.length) {
      return studentContentCache.modules.map(mapBackendModule);
    }

    const currentUser = getCurrentUser();
    const ownYear = getLevelTextFromYear(currentUser.yearLevel || '1');
    return MODULES.filter(module => module.level === ownYear);
  }

  function getState() {
    if (hydratedState) {
      return mergeState(hydratedState);
    }

    const currentUser = getCurrentUser();
    const storageKey = getStorageKey(currentUser);
    try {
      const stored = JSON.parse(localStorage.getItem(storageKey));
      if (stored) {
        return mergeState(stored);
      }
    } catch (_) {
      // ignore
    }

    return mergeState(buildSeedState(currentUser));
  }

  async function loadStateFromBackend() {
    const currentUser = getCurrentUser();
    const email = String(currentUser.email || '').trim();
    if (!email) {
      return null;
    }

    try {
      const response = await fetch(`${API_BASE}/learning/state/?email=${encodeURIComponent(email)}`);
      if (!response.ok) {
        return null;
      }

      const payload = await response.json();
      if (!payload || typeof payload.state !== 'object') {
        return null;
      }

      const merged = mergeState(payload.state);
      hydratedState = merged;
      localStorage.setItem(getStorageKey(currentUser), JSON.stringify(merged));
      return merged;
    } catch (_) {
      return null;
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
    const currentUser = getCurrentUser();
    const email = String(currentUser.email || '').trim();
    if (!email) {
      return null;
    }

    try {
      const response = await fetch(`${API_BASE}/student/content/?email=${encodeURIComponent(email)}`);
      if (!response.ok) {
        return null;
      }

      const payload = await response.json();
      if (!payload || !Array.isArray(payload.modules)) {
        return null;
      }

      studentContentCache = payload;
      return payload;
    } catch (_) {
      return null;
    }
  }

  function renderRecentActivityList(target, entries) {
    if (!target) {
      return;
    }

    target.innerHTML = entries.map(activity => `
      <li style="padding: 10px; border-bottom: 1px solid #e0e0e0; display:flex; justify-content:space-between; gap:12px;">
        <span>${activity.icon} ${activity.text}</span>
        <span style="color: green; white-space: nowrap;">${activity.meta}</span>
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
        body: JSON.stringify({ email, state }),
      });

      if (!response.ok) {
        return null;
      }

      const payload = await response.json();
      if (payload && typeof payload.state === 'object') {
        localStorage.setItem(getStorageKey(currentUser), JSON.stringify(mergeState(payload.state)));
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
    localStorage.setItem(getStorageKey(getCurrentUser()), JSON.stringify(merged));
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

  function renderDashboard() {
    const currentUser = getCurrentUser();
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

    const profileRole = document.getElementById('dashboardProfileRole');
    if (profileRole) {
      profileRole.textContent = currentUser.role || 'student';
    }

    const profileMeta = document.getElementById('dashboardProfileMeta');
    if (profileMeta) {
      profileMeta.textContent = `${currentUser.email || ''} • ${getYearLabel(currentUser.yearLevel)} • ${currentUser.role || 'student'}`;
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
      pointsMeta.textContent = `${state.points.toLocaleString()} total points saved for ${currentUser.name || 'the current user'}`;
    }

    const modulesMeta = document.getElementById('dashboardModulesMeta');
    if (modulesMeta) {
      const completedVisible = visibleModules.filter(module => getModuleProgress(state, module.id) >= 100).length;
      modulesMeta.textContent = `${completedVisible} modules completed across ${visibleModules.length} lessons`;
    }

    const rankMeta = document.getElementById('dashboardRankMeta');
    if (rankMeta) {
      rankMeta.textContent = `Current backend rank: #${state.rank}`;
    }

    const accuracyMeta = document.getElementById('dashboardAccuracyMeta');
    if (accuracyMeta) {
      accuracyMeta.textContent = `${state.accuracy}% accuracy from your saved learner profile`;
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

      void (async () => {
        const announcements = await loadPublicAnnouncements(3);
        if (!announcements.length) {
          return;
        }

        const announcementEntries = announcements.map(item => ({
          icon: '📢',
          text: String(item.title || 'Announcement').trim(),
          meta: 'Announcement',
        }));

        const mergedEntries = announcementEntries.concat(state.recentActivity || []).slice(0, 10);
        renderRecentActivityList(recentActivity, mergedEntries);
      })();
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
      void (async () => {
        const payload = await loadLeaderboardFromBackend({ limit: 5 });
        const players = payload && Array.isArray(payload.players) ? payload.players : state.leaderboard;
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
        const currentUser = payload && payload.currentUser ? payload.currentUser : null;
        if (rankElement) {
          rankElement.textContent = currentUser && Number(currentUser.points || 0) > 0 ? `#${Number(currentUser.rank || 0)}` : 'Unranked';
        }
        if (rankMeta) {
          rankMeta.textContent = currentUser && Number(currentUser.points || 0) > 0
            ? `Live rank from the leaderboard: #${Number(currentUser.rank || 0)}`
            : 'No rank yet until you earn your first points';
        }
      })();
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

    let activeLevel = target.getAttribute('data-active-level') || ownLevel;
    const render = () => {
      const modules = getFilteredModules(activeLevel);
      target.innerHTML = modules.map(module => {
        const progress = getModuleProgress(state, module.id);
        const completed = progress >= 100;
        return `
          <div class="module-card" data-level="${module.level}">
            <div class="module-header">
              <div class="level-badge">${module.level} Year</div>
              <div class="completion-percentage">${progress}%</div>
            </div>
            <h3>${module.title}</h3>
            <p>${module.description}</p>
            <p style="font-size: 0.9rem; color: #555; margin-top: -6px;"><strong>Outcome:</strong> ${module.outcome}</p>
            <div class="module-activities">
              <span class="activity-type">📚 ${module.activities} Activities</span>
              <span class="activity-type">⏱️ ${module.minutes} min</span>
            </div>
            <div class="progress-bar"><div class="progress-fill" style="width: ${progress}%;"></div></div>
            <div style="margin-bottom: 15px; font-size: 0.85rem; color: #666;">${module.unlocks}</div>
            ${completed ? '<div class="completion-badge">✓ Completed</div>' : ''}
            <button class="btn-primary" onclick="window.location.href='activity.html?module=' + '${module.id}' + '${completed ? '&review=true' : ''}'">${completed ? 'Review' : progress > 0 ? 'Continue Learning' : 'Start Learning'}</button>
          </div>
        `;
      }).join('');
    };

    render();

    const filterButtons = document.querySelectorAll('.filter-btn[data-level]');
    const currentYearButton = document.getElementById('currentYearOnlyFilter');
    if (currentYearButton) {
      currentYearButton.setAttribute('data-level', ownLevel);
      currentYearButton.textContent = `${ownLevel} Year`;
    }
    filterButtons.forEach(button => {
      const buttonLevel = String(button.getAttribute('data-level') || '').trim();
      if (buttonLevel === 'all' || buttonLevel !== ownLevel) {
        button.style.display = 'none';
      }
      button.addEventListener('click', function () {
        filterButtons.forEach(btn => btn.classList.remove('active'));
        this.classList.add('active');
        activeLevel = this.getAttribute('data-level') || 'all';
        target.setAttribute('data-active-level', activeLevel);
        render();
      });
    });

    target.setAttribute('data-active-level', ownLevel);
    activeLevel = ownLevel;
    render();

    const moduleSummary = document.getElementById('learningPathSummary');
    if (moduleSummary) {
      moduleSummary.textContent = `${currentUser.name || 'Learner'} is currently at ${currentUser.yearLevel ? getYearLabel(currentUser.yearLevel) : 'foundation'} level with ${averageProgress}% overall module progress.`;
    }
  }

  function renderProfile() {
    const currentUser = getCurrentUser();
    const state = getState();
    let profileExtras = {};
    try {
      const extrasKey = `kumpasProfileExtras:${String(currentUser.email || 'guest').toLowerCase().trim() || 'guest'}`;
      profileExtras = JSON.parse(localStorage.getItem(extrasKey) || '{}') || {};
    } catch (_) {
      profileExtras = {};
    }

    const name = document.getElementById('profileDisplayName');
    if (name) name.textContent = currentUser.name || 'Learner';

    const metaYear = document.getElementById('profileYearLevel');
    if (metaYear) metaYear.textContent = getYearLabel(currentUser.yearLevel);

    const metaRole = document.getElementById('profileRole');
    if (metaRole) metaRole.textContent = currentUser.role || 'student';

    const email = document.getElementById('profileEmail');
    if (email) email.textContent = currentUser.email || '';

    const yearText = document.getElementById('profileYearText');
    if (yearText) yearText.textContent = getYearLabel(currentUser.yearLevel);

    const fullName = document.getElementById('profileFullName');
    if (fullName) fullName.textContent = currentUser.name || 'Learner';

    const studentId = document.getElementById('profileStudentId');
    if (studentId) {
      const generatedId = (() => {
        const shortHash = (currentUser.email || 'user').split('').reduce((sum, char) => sum + char.charCodeAt(0), 0).toString().slice(-6);
        return `${new Date().getFullYear()}-${String(currentUser.yearLevel || '1').toUpperCase()}-${shortHash}`;
      })();
      studentId.textContent = String(profileExtras.studentId || generatedId).trim();
    }

    const points = document.getElementById('profilePoints');
    if (points) points.textContent = state.points.toLocaleString();

    const rank = document.getElementById('profileRank');
    if (rank) rank.textContent = state.points > 0 ? `#${state.rank}` : 'Unranked';

    void (async () => {
      const payload = await loadLeaderboardFromBackend({ limit: 50 });
      const liveCurrentUser = payload && payload.currentUser ? payload.currentUser : null;
      if (rank) {
        rank.textContent = liveCurrentUser && Number(liveCurrentUser.points || 0) > 0
          ? `#${Number(liveCurrentUser.rank || 0)}`
          : 'Unranked';
      }
    })();

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

  async function hydrateAndRender() {
    const backendState = await loadStateFromBackend();
    await loadStudentContentFromBackend();
    if (backendState) {
      saveState(backendState);
    } else if (!hydratedState) {
      hydratedState = getState();
    }

    renderDashboard();
    renderLearning();
    renderProfile();
  }

  document.addEventListener('DOMContentLoaded', function () {
    initNavbarUserMenu();
    void hydrateAndRender();
  });

  window.KumpasPortal = {
    MODULES,
    DEFAULT_STATE,
    getCurrentUser,
    getState,
    loadStateFromBackend,
    loadLeaderboardFromBackend,
    loadPublicAnnouncements,
    loadStudentContentFromBackend,
    saveState,
    updateState,
    recordProgress,
    renderDashboard,
    renderLearning,
    renderProfile
  };
})();
