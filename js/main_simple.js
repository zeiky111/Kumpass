// Simple JavaScript for Kumpas
// Made by student

// Hamburger menu for mobile
function toggleMenu() {
    var menu = document.getElementById('navMenu');
    if (menu.style.display === 'block') {
        menu.style.display = 'none';
    } else {
        menu.style.display = 'block';
    }
}

// Smooth scrolling for anchor links
document.addEventListener('DOMContentLoaded', function() {
    var links = document.querySelectorAll('a[href^="#"]');
    
    for (var i = 0; i < links.length; i++) {
        links[i].addEventListener('click', function(e) {
            e.preventDefault();
            var targetId = this.getAttribute('href');
            var targetElement = document.querySelector(targetId);
            
            if (targetElement) {
                targetElement.scrollIntoView({ behavior: 'smooth' });
            }
        });
    }
});

// Simple form validation
function validateForm(formId) {
    var form = document.getElementById(formId);
    var inputs = form.querySelectorAll('input[required]');
    var isValid = true;
    
    for (var i = 0; i < inputs.length; i++) {
        if (inputs[i].value === '') {
            alert('Please fill in all required fields!');
            isValid = false;
            break;
        }
    }
    
    return isValid;
}

// Show/hide password
function togglePassword(inputId) {
    var input = document.getElementById(inputId);
    if (input.type === 'password') {
        input.type = 'text';
    } else {
        input.type = 'password';
    }
}

// Simple alert messages
function showAlert(message, type) {
    alert(message);
}

// Logout function
function logout() {
    if (confirm('Are you sure you want to logout?')) {
        window.location.href = 'index.html';
    }
}

// Print page
function printPage() {
    window.print();
}

console.log('Kumpas system loaded!');
