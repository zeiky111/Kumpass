(function () {
  function getCurrentUser() {
    try {
      return JSON.parse(localStorage.getItem('currentUser') || '{}') || {};
    } catch (_) {
      return {};
    }
  }

  function getYearLabel(yearLevel) {
    const mapping = {
      '1': '1st Year',
      '2': '2nd Year',
      '3': '3rd Year',
      '4': '4th Year',
    };
    return mapping[String(yearLevel || '').trim()] || '1st Year';
  }

  document.addEventListener('DOMContentLoaded', function () {
    const currentUser = getCurrentUser();
    const yearLevel = String(currentUser.yearLevel || '1').trim();
    const yearSelect = document.getElementById('yearLevelFilter');

    if (yearSelect) {
      yearSelect.innerHTML = `<option value="${yearLevel}">${getYearLabel(yearLevel)}</option>`;
      yearSelect.value = yearLevel;
      yearSelect.disabled = true;
    }

    const sectionTitle = document.querySelector('.section-header h2');
    if (sectionTitle) {
      sectionTitle.textContent = `${getYearLabel(yearLevel)} Activities`;
    }
  });
})();
