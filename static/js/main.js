/**
 * ConfigSync Dashboard - JavaScript
 * Handles form validation, password strength checking, and UI interactions
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize all functionality
    initializePasswordValidation();
    initializeFormValidation();
    initializeUIInteractions();
    initializeFlashMessages();
});

/**
 * Password validation and strength checking
 */
function initializePasswordValidation() {
    const passwordInput = document.getElementById('password');
    const confirmPasswordInput = document.getElementById('confirm_password');
    const passwordStrengthDiv = document.getElementById('passwordStrength');
    const passwordMatchDiv = document.getElementById('passwordMatch');

    if (passwordInput) {
        passwordInput.addEventListener('input', function() {
            checkPasswordStrength(this.value);
            if (confirmPasswordInput && confirmPasswordInput.value) {
                checkPasswordMatch(passwordInput.value, confirmPasswordInput.value);
            }
        });
    }

    if (confirmPasswordInput) {
        confirmPasswordInput.addEventListener('input', function() {
            if (passwordInput) {
                checkPasswordMatch(passwordInput.value, this.value);
            }
        });
    }
}

function checkPasswordStrength(password) {
    const strengthDiv = document.getElementById('passwordStrength');
    if (!strengthDiv) return;

    const strength = calculatePasswordStrength(password);
    const strengthText = getStrengthText(strength);
    const strengthClass = getStrengthClass(strength);

    strengthDiv.textContent = strengthText;
    strengthDiv.className = `password-strength ${strengthClass}`;
}

function calculatePasswordStrength(password) {
    let score = 0;
    
    if (password.length >= 8) score += 1;
    if (password.length >= 12) score += 1;
    if (/[a-z]/.test(password)) score += 1;
    if (/[A-Z]/.test(password)) score += 1;
    if (/[0-9]/.test(password)) score += 1;
    if (/[^A-Za-z0-9]/.test(password)) score += 1;
    
    if (score <= 2) return 'weak';
    if (score <= 4) return 'medium';
    return 'strong';
}

function getStrengthText(strength) {
    switch (strength) {
        case 'weak': return 'Password strength: Weak';
        case 'medium': return 'Password strength: Medium';
        case 'strong': return 'Password strength: Strong';
        default: return '';
    }
}

function getStrengthClass(strength) {
    return strength;
}

function checkPasswordMatch(password, confirmPassword) {
    const matchDiv = document.getElementById('passwordMatch');
    if (!matchDiv) return;

    if (confirmPassword === '') {
        matchDiv.textContent = '';
        matchDiv.className = 'password-match';
        return;
    }

    if (password === confirmPassword) {
        matchDiv.textContent = 'Passwords match ✓';
        matchDiv.className = 'password-match match';
    } else {
        matchDiv.textContent = 'Passwords do not match ✗';
        matchDiv.className = 'password-match no-match';
    }
}

/**
 * Password visibility toggle
 */
function togglePassword(inputId) {
    const input = document.getElementById(inputId);
    const toggle = input.parentElement.querySelector('.password-toggle i');
    
    if (input.type === 'password') {
        input.type = 'text';
        toggle.className = 'fas fa-eye-slash';
    } else {
        input.type = 'password';
        toggle.className = 'fas fa-eye';
    }
}

/**
 * Form validation
 */
function initializeFormValidation() {
    const loginForm = document.getElementById('loginForm');
    const signupForm = document.getElementById('signupForm');

    if (loginForm) {
        loginForm.addEventListener('submit', function(e) {
            if (!validateLoginForm()) {
                e.preventDefault();
            }
        });
    }

    if (signupForm) {
        signupForm.addEventListener('submit', function(e) {
            if (!validateSignupForm()) {
                e.preventDefault();
            }
        });
    }
}

function validateLoginForm() {
    const email = document.getElementById('email').value.trim();
    const password = document.getElementById('password').value.trim();

    if (!email || !password) {
        showError('Please fill in all fields');
        return false;
    }

    if (!isValidEmail(email)) {
        showError('Please enter a valid email address');
        return false;
    }

    return true;
}

function validateSignupForm() {
    const email = document.getElementById('email').value.trim();
    const password = document.getElementById('password').value.trim();
    const confirmPassword = document.getElementById('confirm_password').value.trim();

    if (!email || !password || !confirmPassword) {
        showError('Please fill in all fields');
        return false;
    }

    if (!isValidEmail(email)) {
        showError('Please enter a valid email address');
        return false;
    }

    if (password.length < 6) {
        showError('Password must be at least 6 characters long');
        return false;
    }

    if (password !== confirmPassword) {
        showError('Passwords do not match');
        return false;
    }

    const strength = calculatePasswordStrength(password);
    if (strength === 'weak') {
        showError('Please choose a stronger password');
        return false;
    }

    return true;
}

function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

function showError(message) {
    // Create a temporary error message
    const errorDiv = document.createElement('div');
    errorDiv.className = 'flash-message flash-error';
    errorDiv.innerHTML = `<i class="fas fa-exclamation-circle"></i>${message}`;
    
    // Add to flash messages container
    let container = document.querySelector('.flash-messages');
    if (!container) {
        container = document.createElement('div');
        container.className = 'flash-messages';
        document.body.appendChild(container);
    }
    
    container.appendChild(errorDiv);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        if (errorDiv.parentNode) {
            errorDiv.parentNode.removeChild(errorDiv);
        }
    }, 5000);
}

/**
 * UI Interactions
 */
function initializeUIInteractions() {
    // Add loading states to forms
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function() {
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
                
                // Re-enable after 10 seconds as fallback
                setTimeout(() => {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = submitBtn.getAttribute('data-original-text') || 'Submit';
                }, 10000);
            }
        });
    });

    // Store original button text
    const submitButtons = document.querySelectorAll('button[type="submit"]');
    submitButtons.forEach(btn => {
        btn.setAttribute('data-original-text', btn.innerHTML);
    });

    // Add hover effects to cards
    const cards = document.querySelectorAll('.stat-card, .section-card, .action-btn');
    cards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-4px)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
        });
    });

    // Add click animations to buttons
    const buttons = document.querySelectorAll('button, .auth-btn, .primary-btn');
    buttons.forEach(button => {
        button.addEventListener('click', function(e) {
            // Create ripple effect
            const ripple = document.createElement('span');
            const rect = this.getBoundingClientRect();
            const size = Math.max(rect.width, rect.height);
            const x = e.clientX - rect.left - size / 2;
            const y = e.clientY - rect.top - size / 2;
            
            ripple.style.width = ripple.style.height = size + 'px';
            ripple.style.left = x + 'px';
            ripple.style.top = y + 'px';
            ripple.classList.add('ripple');
            
            this.appendChild(ripple);
            
            setTimeout(() => {
                ripple.remove();
            }, 600);
        });
    });
}

/**
 * Flash Messages Management
 */
function initializeFlashMessages() {
    const flashMessages = document.querySelectorAll('.flash-message');
    
    flashMessages.forEach(message => {
        // Auto-hide after 5 seconds
        setTimeout(() => {
            message.style.animation = 'slideOut 0.3s ease-in forwards';
            setTimeout(() => {
                if (message.parentNode) {
                    message.parentNode.removeChild(message);
                }
            }, 300);
        }, 5000);
        
        // Add close button
        const closeBtn = document.createElement('button');
        closeBtn.innerHTML = '<i class="fas fa-times"></i>';
        closeBtn.className = 'flash-close';
        closeBtn.style.cssText = `
            position: absolute;
            top: 8px;
            right: 8px;
            background: none;
            border: none;
            color: inherit;
            cursor: pointer;
            opacity: 0.7;
            transition: opacity 0.3s ease;
        `;
        
        closeBtn.addEventListener('click', () => {
            message.style.animation = 'slideOut 0.3s ease-in forwards';
            setTimeout(() => {
                if (message.parentNode) {
                    message.parentNode.removeChild(message);
                }
            }, 300);
        });
        
        closeBtn.addEventListener('mouseenter', () => {
            closeBtn.style.opacity = '1';
        });
        
        closeBtn.addEventListener('mouseleave', () => {
            closeBtn.style.opacity = '0.7';
        });
        
        message.style.position = 'relative';
        message.appendChild(closeBtn);
    });
}

/**
 * Utility Functions
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function throttle(func, limit) {
    let inThrottle;
    return function() {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// Add CSS for animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
    
    .ripple {
        position: absolute;
        border-radius: 50%;
        background: rgba(255, 255, 255, 0.3);
        transform: scale(0);
        animation: ripple-animation 0.6s linear;
        pointer-events: none;
    }
    
    @keyframes ripple-animation {
        to {
            transform: scale(4);
            opacity: 0;
        }
    }
    
    .flash-close:hover {
        opacity: 1 !important;
    }
`;
document.head.appendChild(style);

// Load cloud credentials JavaScript if on cloud credentials page
if (window.location.pathname.includes('cloud-credentials')) {
    const script = document.createElement('script');
    script.src = '/static/js/cloud-credentials.js';
    document.head.appendChild(script);
}

// Dashboard baseline collection functionality
if (window.location.pathname.includes('dashboard') || window.location.pathname === '/') {
    document.addEventListener('DOMContentLoaded', function() {
        initializeBaselineCollection();
        loadBaselineSummary();
        initializeDriftDetection();
    });
}

function initializeBaselineCollection() {
    const collectBtn = document.getElementById('collect-baseline-btn');
    const progressDiv = document.getElementById('baseline-progress');
    
    if (collectBtn) {
        collectBtn.addEventListener('click', function() {
            triggerBaselineCollection();
        });
    }
}

function triggerBaselineCollection() {
    const collectBtn = document.getElementById('collect-baseline-btn');
    const progressDiv = document.getElementById('baseline-progress');
    
    // Show loading state
    collectBtn.disabled = true;
    collectBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Collecting...';
    progressDiv.style.display = 'block';
    
    // Trigger baseline collection
    fetch('/trigger-baseline', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Update counts
            updateResourceCounts(data.counts);
            showSuccess('Baseline collection completed successfully!');
        } else {
            showError(data.message || 'Failed to collect baseline');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showError('An error occurred during baseline collection');
    })
    .finally(() => {
        // Reset button state
        collectBtn.disabled = false;
        collectBtn.innerHTML = '<i class="fas fa-play"></i> Start Baseline Collection';
        progressDiv.style.display = 'none';
    });
}

function loadBaselineSummary() {
    fetch('/get-baseline-summary')
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            updateResourceCounts(data.summary);
        }
    })
    .catch(error => {
        console.error('Error loading baseline summary:', error);
    });
}

function updateResourceCounts(counts) {
    const awsCount = document.getElementById('aws-count');
    const gcpCount = document.getElementById('gcp-count');
    const azureCount = document.getElementById('azure-count');
    const totalCount = document.getElementById('total-count');
    
    if (awsCount) awsCount.textContent = counts.aws_count || 0;
    if (gcpCount) gcpCount.textContent = counts.gcp_count || 0;
    if (azureCount) azureCount.textContent = counts.azure_count || 0;
    if (totalCount) {
        const total = (counts.aws_count || 0) + (counts.gcp_count || 0) + (counts.azure_count || 0);
        totalCount.textContent = total;
    }
}

// =============================================================================
// DRIFT DETECTION FUNCTIONS
// =============================================================================

function initializeDriftDetection() {
    const startBtn = document.getElementById('start-drift-btn');
    const stopBtn = document.getElementById('stop-drift-btn');
    const runCheckBtn = document.getElementById('run-check-btn');
    const testS3EmailBtn = document.getElementById('test-s3-email-btn');
    
    if (startBtn) {
        startBtn.addEventListener('click', startDriftDetection);
    }
    
    if (stopBtn) {
        stopBtn.addEventListener('click', stopDriftDetection);
    }
    
    if (runCheckBtn) {
        runCheckBtn.addEventListener('click', runDriftCheck);
    }
    
    if (testS3EmailBtn) {
        testS3EmailBtn.addEventListener('click', testS3VersioningEmail);
    }
    
    // Load initial drift status
    loadDriftStatus();
    
    // Refresh drift status every 30 seconds
    setInterval(loadDriftStatus, 30000);
}

function startDriftDetection() {
    const startBtn = document.getElementById('start-drift-btn');
    const stopBtn = document.getElementById('stop-drift-btn');
    
    // Show loading state
    setLoadingState(startBtn, true);
    
    fetch('/start-drift-detection', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        setLoadingState(startBtn, false);
        
        if (data.success) {
            showSuccess(data.message || 'Drift detection started successfully!');
            updateDriftStatus('Running');
            startBtn.style.display = 'none';
            stopBtn.style.display = 'inline-flex';
        } else {
            showError(data.message || 'Failed to start drift detection');
        }
    })
    .catch(error => {
        setLoadingState(startBtn, false);
        console.error('Error:', error);
        showError('An error occurred while starting drift detection');
    });
}

function stopDriftDetection() {
    const startBtn = document.getElementById('start-drift-btn');
    const stopBtn = document.getElementById('stop-drift-btn');
    
    // Show loading state
    setLoadingState(stopBtn, true);
    
    fetch('/stop-drift-detection', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        setLoadingState(stopBtn, false);
        
        if (data.success) {
            showSuccess(data.message || 'Drift detection stopped successfully!');
            updateDriftStatus('Stopped');
            startBtn.style.display = 'inline-flex';
            stopBtn.style.display = 'none';
        } else {
            showError(data.message || 'Failed to stop drift detection');
        }
    })
    .catch(error => {
        setLoadingState(stopBtn, false);
        console.error('Error:', error);
        showError('An error occurred while stopping drift detection');
    });
}

function runDriftCheck() {
    const runCheckBtn = document.getElementById('run-check-btn');
    
    // Show loading state
    setLoadingState(runCheckBtn, true);
    
    fetch('/run-drift-check', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        setLoadingState(runCheckBtn, false);
        
        if (data.success) {
            showSuccess(data.message || 'Drift check initiated successfully!');
            // Refresh drift status after a short delay
            setTimeout(loadDriftStatus, 2000);
        } else {
            showError(data.message || 'Failed to run drift check');
        }
    })
    .catch(error => {
        setLoadingState(runCheckBtn, false);
        console.error('Error:', error);
        showError('An error occurred while running drift check');
    });
}

function loadDriftStatus() {
    fetch('/get-drift-status')
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            updateDriftStatus(data.detection_status);
            updateDriftResults(data.drift_status);
        }
    })
    .catch(error => {
        console.error('Error loading drift status:', error);
    });
}

function updateDriftStatus(status) {
    const statusDot = document.getElementById('status-dot');
    const statusText = document.getElementById('status-text');
    const startBtn = document.getElementById('start-drift-btn');
    const stopBtn = document.getElementById('stop-drift-btn');
    
    if (statusDot && statusText) {
        statusDot.className = `status-dot ${status.toLowerCase()}`;
        statusText.textContent = status;
    }
    
    if (startBtn && stopBtn) {
        if (status === 'Running') {
            startBtn.style.display = 'none';
            stopBtn.style.display = 'inline-flex';
        } else {
            startBtn.style.display = 'inline-flex';
            stopBtn.style.display = 'none';
        }
    }
}

function updateDriftResults(driftStatus) {
    const lastCheck = document.getElementById('last-check');
    const totalDrifts = document.getElementById('total-drifts');
    const driftDetails = document.getElementById('drift-details');
    const driftResults = document.getElementById('drift-results');
    
    if (lastCheck) {
        lastCheck.textContent = driftStatus.last_check || 'Never';
    }
    
    if (totalDrifts) {
        totalDrifts.textContent = driftStatus.total_drifts || 0;
    }
    
    if (driftDetails && driftResults) {
        if (driftStatus.total_drifts > 0) {
            driftResults.style.display = 'block';
            driftDetails.innerHTML = '';
            
            // Display drift details
            driftStatus.drifts_detected.forEach((drift, index) => {
                const driftItem = createDriftItem(drift, index + 1);
                driftDetails.appendChild(driftItem);
            });
        } else {
            driftResults.style.display = 'none';
        }
    }
}

function createDriftItem(drift, index) {
    const driftItem = document.createElement('div');
    driftItem.className = 'drift-item';
    
    const iconClass = getDriftIconClass(drift.type);
    const iconSymbol = getDriftIconSymbol(drift.type);
    
    driftItem.innerHTML = `
        <div class="drift-icon ${iconClass}">
            <i class="fas ${iconSymbol}"></i>
        </div>
        <div class="drift-content-info">
            <h5>${drift.change_type}</h5>
            <p>${drift.cloud} - ${drift.resource_type}: ${drift.resource_name}</p>
        </div>
        <div class="drift-timestamp">
            ${new Date(drift.timestamp).toLocaleString()}
        </div>
    `;
    
    return driftItem;
}

function getDriftIconClass(type) {
    switch (type) {
        case 'field_change': return 'field-change';
        case 'new_resource': return 'new-resource';
        case 'deleted_resource': return 'deleted-resource';
        case 's3_parity': return 's3-parity';
        default: return 'field-change';
    }
}

function getDriftIconSymbol(type) {
    switch (type) {
        case 'field_change': return 'fa-edit';
        case 'new_resource': return 'fa-plus-circle';
        case 'deleted_resource': return 'fa-trash';
        case 's3_parity': return 'fa-exclamation-triangle';
        case 's3_versioning': return 'fa-shield-alt';
        default: return 'fa-edit';
    }
}

function testS3VersioningEmail() {
    const testBtn = document.getElementById('test-s3-email-btn');
    
    // Show loading state
    setLoadingState(testBtn, true);
    
    fetch('/test-s3-versioning-email', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        setLoadingState(testBtn, false);
        
        if (data.success) {
            showSuccess(data.message || 'S3 versioning test email sent successfully!');
        } else {
            showError(data.message || 'Failed to send S3 versioning test email');
        }
    })
    .catch(error => {
        setLoadingState(testBtn, false);
        console.error('Error:', error);
        showError('An error occurred while sending test email');
    });
}

function showSuccess(message) {
    // Create success message
    const successDiv = document.createElement('div');
    successDiv.className = 'flash-message flash-success';
    successDiv.innerHTML = `<i class="fas fa-check-circle"></i>${message}`;
    
    // Add to flash messages container
    let container = document.querySelector('.flash-messages');
    if (!container) {
        container = document.createElement('div');
        container.className = 'flash-messages';
        document.body.appendChild(container);
    }
    
    container.appendChild(successDiv);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        if (successDiv.parentNode) {
            successDiv.parentNode.removeChild(successDiv);
        }
    }, 5000);
}

function showError(message) {
    // Create error message
    const errorDiv = document.createElement('div');
    errorDiv.className = 'flash-message flash-error';
    errorDiv.innerHTML = `<i class="fas fa-exclamation-circle"></i>${message}`;
    
    // Add to flash messages container
    let container = document.querySelector('.flash-messages');
    if (!container) {
        container = document.createElement('div');
        container.className = 'flash-messages';
        document.body.appendChild(container);
    }
    
    container.appendChild(errorDiv);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        if (errorDiv.parentNode) {
            errorDiv.parentNode.removeChild(errorDiv);
        }
    }, 5000);
}
