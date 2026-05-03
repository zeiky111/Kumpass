// Simple JavaScript for Kumpas
// Basic features only

document.addEventListener('DOMContentLoaded', function() {
  var hamburger = document.getElementById('hamburger');
  var navMenu = document.getElementById('navMenu');

  if (hamburger && navMenu) {
    hamburger.addEventListener('click', function() {
      navMenu.classList.toggle('active');
      hamburger.classList.toggle('active');
    });
  }

  var navLinks = document.querySelectorAll('.nav-link');
  for (var i = 0; i < navLinks.length; i++) {
    navLinks[i].addEventListener('click', function() {
      if (navMenu) {
        navMenu.classList.remove('active');
      }
      if (hamburger) {
        hamburger.classList.remove('active');
      }
    });
  }

  var anchors = document.querySelectorAll('a[href^="#"]');
  for (var j = 0; j < anchors.length; j++) {
    anchors[j].addEventListener('click', function(e) {
      var target = document.querySelector(this.getAttribute('href'));
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  }

  initNavbarUserMenu();
});

function initNavbarUserMenu() {
  var navbar = document.querySelector('.navbar');
  if (!navbar) return;

  var profileLink = navbar.querySelector('a.profile-link') || navbar.querySelector('a[href="profile.html"]');
  var logoutLink = navbar.querySelector('a.logout-btn') || navbar.querySelector('a[href="index.html"]');
  if (!profileLink || !logoutLink) return;

  if (navbar.querySelector('.nav-user-menu')) return;

  var profileTarget = profileLink.closest('li') || profileLink;
  var logoutTarget = logoutLink.closest('li') || logoutLink;
  profileTarget.style.display = 'none';
  logoutTarget.style.display = 'none';

  var menu = document.createElement('div');
  menu.className = 'nav-user-menu';

  var button = document.createElement('button');
  button.type = 'button';
  button.className = 'nav-user-toggle';
  button.setAttribute('aria-label', 'Open user menu');
  button.innerHTML = '<i class="fas fa-user-circle"></i>';

  var dropdown = document.createElement('div');
  dropdown.className = 'nav-user-dropdown';

  var profileItem = document.createElement('a');
  profileItem.href = profileLink.getAttribute('href') || 'profile.html';
  profileItem.innerHTML = '<i class="fas fa-id-badge"></i><span>Profile</span>';

  var logoutItem = document.createElement('a');
  logoutItem.href = logoutLink.getAttribute('href') || 'index.html';
  logoutItem.className = 'logout';
  logoutItem.innerHTML = '<i class="fas fa-right-from-bracket"></i><span>Logout</span>';

  dropdown.appendChild(profileItem);
  dropdown.appendChild(logoutItem);
  menu.appendChild(button);
  menu.appendChild(dropdown);

  var appendTarget = navbar.querySelector('.navbar-container') || navbar;
  appendTarget.appendChild(menu);

  button.addEventListener('click', function(event) {
    event.preventDefault();
    event.stopPropagation();
    dropdown.classList.toggle('open');
  });

  document.addEventListener('click', function(event) {
    if (!menu.contains(event.target)) {
      dropdown.classList.remove('open');
    }
  });
}
function validateEmail(email) {
  const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return re.test(email);
}

function validateForm(formId) {
  const form = document.getElementById(formId);
  if (!form) return true;
  
  const inputs = form.querySelectorAll('input[required], textarea[required], select[required]');
  let isValid = true;
  
  inputs.forEach(input => {
    if (!input.value.trim()) {
      input.classList.add('error');
      isValid = false;
    } else {
      input.classList.remove('error');
      
      // Email validation
      if (input.type === 'email' && !validateEmail(input.value)) {
        input.classList.add('error');
        isValid = false;
      }
    }
  });
  
  return isValid;
}

// Button hover effects
const buttons = document.querySelectorAll('.btn');
buttons.forEach(btn => {
  btn.addEventListener('mouseenter', function() {
    this.style.transform = 'translateY(-3px)';
  });
  
  btn.addEventListener('mouseleave', function() {
    this.style.transform = 'translateY(0)';
  });
});

// Local storage utilities
const storage = {
  set: (key, value) => {
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch (e) {
      console.error('Storage error:', e);
    }
  },
  
  get: (key, defaultValue = null) => {
    try {
      const item = localStorage.getItem(key);
      return item ? JSON.parse(item) : defaultValue;
    } catch (e) {
      console.error('Storage error:', e);
      return defaultValue;
    }
  },
  
  remove: (key) => {
    try {
      localStorage.removeItem(key);
    } catch (e) {
      console.error('Storage error:', e);
    }
  }
};

// Page load animation
window.addEventListener('load', () => {
  document.body.style.opacity = '1';
  document.body.style.transition = 'opacity 0.5s ease-in';
});

// Scroll to top button
function createScrollToTopButton() {
  const button = document.createElement('button');
  button.innerHTML = '<i class="fas fa-arrow-up"></i>';
  button.className = 'scroll-to-top';
  button.style.cssText = `
    position: fixed;
    bottom: 30px;
    right: 30px;
    width: 50px;
    height: 50px;
    background: linear-gradient(135deg, #2563eb 0%, #7c3aed 100%);
    color: white;
    border: none;
    border-radius: 50%;
    cursor: pointer;
    display: none;
    align-items: center;
    justify-content: center;
    z-index: 999;
    box-shadow: 0 4px 15px rgba(37, 99, 235, 0.3);
    transition: all 0.3s ease;
    font-size: 1.2rem;
  `;
  
  document.body.appendChild(button);
  
  window.addEventListener('scroll', () => {
    if (window.pageYOffset > 300) {
      button.style.display = 'flex';
    } else {
      button.style.display = 'none';
    }
  });
  
  button.addEventListener('click', () => {
    window.scrollTo({
      top: 0,
      behavior: 'smooth'
    });
  });
  
  button.addEventListener('mouseenter', () => {
    button.style.transform = 'translateY(-5px)';
    button.style.boxShadow = '0 6px 20px rgba(37, 99, 235, 0.4)';
  });
  
  button.addEventListener('mouseleave', () => {
    button.style.transform = 'translateY(0)';
    button.style.boxShadow = '0 4px 15px rgba(37, 99, 235, 0.3)';
  });
}

createScrollToTopButton();

// Dark mode toggle (optional)
function initDarkMode() {
  const darkModeToggle = document.getElementById('darkModeToggle');
  if (!darkModeToggle) return;
  
  const isDarkMode = storage.get('darkMode', false);
  
  if (isDarkMode) {
    document.documentElement.style.setProperty('--dark-navy', '#f1f5f9');
    document.documentElement.style.setProperty('--white', '#1e293b');
    document.documentElement.style.setProperty('--light-gray', '#0f172a');
  }
  
  darkModeToggle.addEventListener('click', () => {
    const currentDarkMode = storage.get('darkMode', false);
    storage.set('darkMode', !currentDarkMode);
    location.reload();
  });
}

initDarkMode();

// Console message
console.log('%c🤟 Kumpas - Interactive Sign Language Learning System', 
  'color: #2563eb; font-size: 20px; font-weight: bold;');
console.log('%cVersion 1.0.0 | City College of Calapan BSNED Program',
  'color: #7c3aed; font-size: 14px;');
