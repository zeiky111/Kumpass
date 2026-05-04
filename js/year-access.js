(function () {
  const API_BASE = localStorage.getItem('kumpasApiBase') || 'http://127.0.0.1:8000/api';

  function getCurrentUser() {
    try {
      return JSON.parse(localStorage.getItem('currentUser') || '{}') || {};
    } catch (_) {
      return {};
    }
  }

  function getCurrentYearLevel() {
    const user = getCurrentUser();
    const year = String(user.yearLevel || '').trim();
    return ['1', '2', '3', '4'].includes(year) ? year : '1';
  }

  function enforceGamePageYear() {
    const body = document.body;
    if (!body) return;

    const requiredYear = String(body.getAttribute('data-required-year') || '').trim();
    if (!requiredYear) return;

    const currentYear = getCurrentYearLevel();
    if (requiredYear !== currentYear) {
      window.location.href = 'games.html';
    }
  }

  function filterGamesPageByYear() {
    const cards = Array.from(document.querySelectorAll('.game-card[data-year]'));
    if (!cards.length) return;

    const currentYear = getCurrentYearLevel();
    cards.forEach(function (card) {
      const cardYear = String(card.getAttribute('data-year') || '').trim();
      if (cardYear !== currentYear) {
        card.style.display = 'none';
      }
    });
  }

  async function filterGamesPageByServerAccess() {
    const cards = Array.from(document.querySelectorAll('.game-card[data-year]'));
    if (!cards.length) return;

    const user = getCurrentUser();
    const email = String(user.email || '').trim();
    if (!email) {
      filterGamesPageByYear();
      return;
    }

    try {
      const response = await fetch(`${API_BASE}/student/content/?email=${encodeURIComponent(email)}`);
      if (!response.ok) {
        filterGamesPageByYear();
        return;
      }

      const payload = await response.json();
      const gameAccess = Array.isArray(payload.gameAccess) ? payload.gameAccess : [];
      const allowedRoutes = new Set(
        gameAccess
          .map(item => String(item.route || '').trim())
          .filter(Boolean)
      );

      if (!allowedRoutes.size) {
        filterGamesPageByYear();
        return;
      }

      cards.forEach(function (card) {
        const gameButton = card.querySelector('.game-btn');
        const href = String((gameButton && gameButton.getAttribute('href')) || '').trim();
        card.style.display = allowedRoutes.has(href) ? '' : 'none';
      });
    } catch (_) {
      filterGamesPageByYear();
    }
  }

  function showRandomLevelTag() {
    const difficulty = String(document.body.getAttribute('data-game-difficulty') || 'easy').trim().toLowerCase();
    const map = {
      easy: [1, 2, 3],
      medium: [1, 2, 3],
      hard: [1, 2, 3],
    };
    const levels = map[difficulty] || [1, 2, 3];
    const selected = levels[Math.floor(Math.random() * levels.length)];

    const target = document.getElementById('randomLevelTag');
    if (target) {
      target.textContent = 'Level ' + selected;
    }
  }

  document.addEventListener('DOMContentLoaded', function () {
    enforceGamePageYear();
    void filterGamesPageByServerAccess();
    showRandomLevelTag();
  });

  window.KumpasYearAccess = {
    getCurrentYearLevel,
  };
})();
