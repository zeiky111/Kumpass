// Dashboard functionality
document.addEventListener('DOMContentLoaded', function() {
    // Get current user from localStorage
    const currentUser = JSON.parse(localStorage.getItem('currentUser'));
    
    if (!currentUser) {
        // If no user, redirect to login
        window.location.href = 'login.html';
        return;
    }
    
    // Display user info
    const userNameElements = document.querySelectorAll('[data-user-name]');
    userNameElements.forEach(el => {
        el.textContent = currentUser.name;
    });
    
    // Handle sidebar navigation
    const sidebarLinks = document.querySelectorAll('.sidebar-link');
    sidebarLinks.forEach(link => {
        link.addEventListener('click', function() {
            // Remove active class from all links
            sidebarLinks.forEach(l => l.classList.remove('active'));
            // Add active class to clicked link
            this.classList.add('active');
        });
    });
});

// Game simulation function
function playGame(gameName) {
    alert(`Loading ${gameName}...
    
Game Features:
- Interactive gameplay
- Real-time scoring
- Level progression
- Achievement rewards

Simulating game play...`);
    
    // Simulate game completion
    setTimeout(() => {
        const score = Math.floor(Math.random() * 100);
        alert(`Game Complete!
        
Score: ${score}/100
Accuracy: ${80 + Math.floor(Math.random() * 20)}%
Time: ${Math.floor(Math.random() * 10) + 1}:${Math.floor(Math.random() * 60).toString().padStart(2, '0')}

Points Earned: ${Math.floor(score / 10) * 10}`);
    }, 1000);
}

// Translation tool function
function translateText(text) {
    if (!text) {
        alert('Please enter text to translate');
        return;
    }
    
    alert(`Translating: "${text}"
    
This would display the corresponding FSL signs.

[Mock Sign Image Display]
Hand shape: C-hand
Movement: Forward
Location: Neutral space
Orientation: Palm inward`);
}

// Progress tracking
function viewScores() {
    alert(`Progress & Scores

Completed Modules: 45
Total Score: 12,340 points
Average Accuracy: 87%
Current Rank: #12 on Leaderboard

Detailed Breakdown:
- Basic Signs: 90%
- Intermediate Signs: 65%
- Finger-spelling: 75%
- Advanced Grammar: 30%`);
}

// Announcement function
function readAnnouncement(title, message) {
    alert(`Announcement: ${title}
    
${message}`);
}

// Profile editing
function editProfile() {
    alert(`Edit Profile Modal would open here.
    
You can update:
- Name
- Year Level
- Course
- Profile Picture
- Contact Information`);
}

// Modal functions for dashboard
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('active');
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('active');
    }
}

// Close modal when clicking outside
document.addEventListener('click', function(event) {
    if (event.target.classList && event.target.classList.contains('modal')) {
        event.target.classList.remove('active');
    }
});

// Simulated game functions
function handleGameScoring(gameName) {
    const score = Math.floor(Math.random() * 100);
    alert(`${gameName} Complete!
    
Score: ${score}/100
Time: ${Math.floor(Math.random() * 10)}:${Math.floor(Math.random() * 60).toString().padStart(2, '0')}
Accuracy: ${75 + Math.floor(Math.random() * 25)}%
Points Earned: +${Math.floor(score / 10) * 10}`);
}

// Learning module viewer
function openModule(moduleName, yearLevel) {
    alert(`Opening Module: ${moduleName}
    
Year Level: ${yearLevel}
    
Contents:
- Sign Images (interactive)
- Video Demonstrations
- Lesson Text
- Practice Exercises
- Quiz

This module would open in a full learning interface.`);
}

// Chart filter functionality
document.addEventListener('DOMContentLoaded', function() {
    const filterButtons = document.querySelectorAll('.filter-btn');
    filterButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            filterButtons.forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            console.log('Filtering data for:', this.textContent);
        });
    });
});

// Tab switching function
function switchTab(tabName) {
    // Hide all tabs
    const tabs = document.querySelectorAll('.tab-content');
    tabs.forEach(tab => tab.style.display = 'none');
    
    // Remove active class from all sidebar links
    const sidebarLinks = document.querySelectorAll('.sidebar-link');
    sidebarLinks.forEach(link => link.classList.remove('active'));
    
    // Show selected tab
    const tabElement = document.getElementById(tabName + '-tab');
    if (tabElement) {
        tabElement.style.display = 'block';
    }
    
    // Add active class to the clicked link
    const clickedLink = event.target.closest('.sidebar-link');
    if (clickedLink) {
        clickedLink.classList.add('active');
    }
}

// Logout function
function logout() {
    localStorage.removeItem('currentUser');
    window.location.href = 'login.html';
}
