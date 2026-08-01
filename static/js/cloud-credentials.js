/**
 * ConfigSync Dashboard - Cloud Credentials Form JavaScript
 * Handles form validation, file upload, and submission for cloud provider credentials
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize cloud credentials form functionality
    initializeCloudCredentialsForm();
    initializeFileUpload();
    initializeFormValidation();
    initializeSectionStatus();
});

/**
 * Initialize the main cloud credentials form functionality
 */
function initializeCloudCredentialsForm() {
    const form = document.getElementById('cloudCredentialsForm');
    const submitBtn = document.getElementById('submitBtn');
    
    if (form) {
        form.addEventListener('submit', handleFormSubmission);
    }
    
    // Add real-time validation to all input fields
    const inputs = form.querySelectorAll('input, textarea');
    inputs.forEach(input => {
        input.addEventListener('input', validateField);
        input.addEventListener('blur', validateField);
    });
}

/**
 * Handle file upload for GCP service account JSON
 */
function initializeFileUpload() {
    const fileInput = document.getElementById('gcp_service_account_file');
    const textarea = document.getElementById('gcp_service_account');
    
    if (fileInput) {
        fileInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file && file.type === 'application/json') {
                const reader = new FileReader();
                reader.onload = function(e) {
                    const content = e.target.result;
                    textarea.value = content;
                    validateJSONContent(content);
                    updateSectionStatus('gcp', true);
                };
                reader.readAsText(file);
            } else if (file) {
                showError('Please select a valid JSON file');
            }
        });
    }
}

/**
 * Initialize form validation
 */
function initializeFormValidation() {
    // AWS Account ID validation
    const awsAccountId = document.getElementById('aws_account_id');
    if (awsAccountId) {
        awsAccountId.addEventListener('input', function() {
            const value = this.value.replace(/\D/g, ''); // Remove non-digits
            if (value.length > 12) {
                this.value = value.substring(0, 12);
            } else {
                this.value = value;
            }
            validateField.call(this);
        });
    }
    
    // Azure GUID validation
    const azureFields = ['azure_tenant_id', 'azure_client_id'];
    azureFields.forEach(fieldId => {
        const field = document.getElementById(fieldId);
        if (field) {
            field.addEventListener('input', function() {
                validateGUID(this);
                validateField.call(this);
            });
        }
    });
}

/**
 * Initialize section status indicators
 */
function initializeSectionStatus() {
    // Check initial status of each section
    updateAllSectionStatus();
}

/**
 * Validate individual form field
 */
function validateField() {
    const field = this;
    const value = field.value.trim();
    let isValid = true;
    let errorMessage = '';
    
    // Check if field is required and empty
    if (field.hasAttribute('required') && !value) {
        isValid = false;
        errorMessage = 'This field is required';
    }
    
    // Field-specific validation
    if (value && isValid) {
        switch (field.id) {
            case 'aws_account_id':
                isValid = /^\d{12}$/.test(value);
                errorMessage = isValid ? '' : 'AWS Account ID must be exactly 12 digits';
                break;
                
            case 'aws_role_arn':
                isValid = /^arn:aws:iam::\d{12}:role\/.+/.test(value);
                errorMessage = isValid ? '' : 'Invalid Role ARN format';
                break;
                
            case 'azure_tenant_id':
            case 'azure_client_id':
                isValid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value);
                errorMessage = isValid ? '' : 'Invalid GUID format';
                break;
                
            case 'gcp_service_account':
                if (value) {
                    isValid = validateJSONContent(value);
                    errorMessage = isValid ? '' : 'Invalid JSON format';
                }
                break;
        }
    }
    
    // Update field appearance
    updateFieldValidation(field, isValid, errorMessage);
    
    // Update section status
    updateSectionStatusForField(field);
    
    return isValid;
}

/**
 * Validate JSON content
 */
function validateJSONContent(content) {
    try {
        const parsed = JSON.parse(content);
        
        // Check if it's a valid GCP service account JSON
        const requiredFields = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email', 'client_id'];
        const hasRequiredFields = requiredFields.every(field => parsed.hasOwnProperty(field));
        
        if (!hasRequiredFields) {
            showError('Invalid GCP service account JSON. Missing required fields.');
            return false;
        }
        
        return true;
    } catch (e) {
        showError('Invalid JSON format: ' + e.message);
        return false;
    }
}

/**
 * Validate GUID format
 */
function validateGUID(field) {
    const value = field.value.trim();
    if (value) {
        // Remove any extra characters and format as GUID
        const cleaned = value.replace(/[^0-9a-f-]/gi, '');
        const parts = cleaned.split('-');
        
        if (parts.length === 5 && 
            parts[0].length === 8 && 
            parts[1].length === 4 && 
            parts[2].length === 4 && 
            parts[3].length === 4 && 
            parts[4].length === 12) {
            field.value = cleaned;
        }
    }
}

/**
 * Update field validation appearance
 */
function updateFieldValidation(field, isValid, errorMessage) {
    const formGroup = field.closest('.form-group');
    const existingError = formGroup.querySelector('.field-error');
    
    // Remove existing error message
    if (existingError) {
        existingError.remove();
    }
    
    // Update field border color
    field.style.borderColor = isValid ? (field.value ? '#00ff88' : '#333333') : '#ff4757';
    
    // Add error message if invalid
    if (!isValid && errorMessage) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'field-error';
        errorDiv.style.cssText = 'color: #ff4757; font-size: 0.85rem; margin-top: 4px;';
        errorDiv.textContent = errorMessage;
        formGroup.appendChild(errorDiv);
    }
}

/**
 * Update section status based on field completion
 */
function updateSectionStatusForField(field) {
    const section = field.closest('.cloud-section');
    if (section) {
        const sectionId = section.id || getSectionIdFromField(field);
        const isComplete = isSectionComplete(section);
        updateSectionStatus(sectionId, isComplete);
    }
}

/**
 * Get section ID from field
 */
function getSectionIdFromField(field) {
    if (field.id.includes('aws')) return 'aws';
    if (field.id.includes('gcp')) return 'gcp';
    if (field.id.includes('azure')) return 'azure';
    return '';
}

/**
 * Check if a section is complete
 */
function isSectionComplete(section) {
    const requiredFields = section.querySelectorAll('input[required], textarea[required]');
    let allValid = true;
    
    requiredFields.forEach(field => {
        const value = field.value.trim();
        if (!value) {
            allValid = false;
            return;
        }
        
        // Additional validation for specific fields
        if (field.id === 'gcp_service_account' && value) {
            allValid = validateJSONContent(value);
        } else if (field.id === 'aws_account_id') {
            allValid = /^\d{12}$/.test(value);
        } else if (field.id === 'aws_role_arn') {
            allValid = /^arn:aws:iam::\d{12}:role\/.+/.test(value);
        } else if (field.id === 'azure_tenant_id' || field.id === 'azure_client_id') {
            allValid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value);
        }
    });
    
    return allValid && requiredFields.length > 0;
}

/**
 * Update section status indicator
 */
function updateSectionStatus(sectionId, isConfigured) {
    const statusElement = document.getElementById(sectionId + '-status');
    if (statusElement) {
        const icon = statusElement.querySelector('i');
        const text = statusElement.querySelector('span');
        
        if (isConfigured) {
            statusElement.classList.add('configured');
            icon.className = 'fas fa-check-circle';
            text.textContent = 'Configured';
        } else {
            statusElement.classList.remove('configured');
            icon.className = 'fas fa-circle';
            text.textContent = 'Not Configured';
        }
    }
}

/**
 * Update all section statuses
 */
function updateAllSectionStatus() {
    const sections = ['aws', 'gcp', 'azure'];
    sections.forEach(sectionId => {
        const section = document.querySelector(`.cloud-section:has(#${sectionId}_account_id), .cloud-section:has(#${sectionId}_service_account), .cloud-section:has(#${sectionId}_tenant_id)`);
        if (section) {
            const isComplete = isSectionComplete(section);
            updateSectionStatus(sectionId, isComplete);
        }
    });
}

/**
 * Handle form submission
 */
function handleFormSubmission(e) {
    e.preventDefault();
    
    const form = e.target;
    const submitBtn = document.getElementById('submitBtn');
    
    // Validate all fields
    const allValid = validateAllFields();
    
    if (!allValid) {
        showError('Please fill in all required fields correctly before submitting.');
        return;
    }
    
    // Show loading state
    setLoadingState(submitBtn, true);
    
    // Prepare form data
    const formData = new FormData(form);
    
    // Submit form
    fetch(form.action, {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        setLoadingState(submitBtn, false);
        
        if (data.success) {
            showSuccess(data.message || 'Cloud credentials saved successfully!');
            updateAllSectionStatus();
            
            // Show notification email step if next step is required
            if (data.next_step === 'notification_email') {
                showNotificationEmailStep();
            }
        } else {
            showError(data.message || 'Failed to save cloud credentials. Please try again.');
        }
    })
    .catch(error => {
        setLoadingState(submitBtn, false);
        console.error('Error:', error);
        showError('An error occurred while saving credentials. Please try again.');
    });
}

/**
 * Validate all form fields
 */
function validateAllFields() {
    const form = document.getElementById('cloudCredentialsForm');
    const requiredFields = form.querySelectorAll('input[required], textarea[required]');
    let allValid = true;
    
    requiredFields.forEach(field => {
        const isValid = validateField.call(field);
        if (!isValid) {
            allValid = false;
        }
    });
    
    return allValid;
}

/**
 * Set loading state for submit button
 */
function setLoadingState(button, isLoading) {
    if (isLoading) {
        button.disabled = true;
        button.classList.add('loading');
        button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';
    } else {
        button.disabled = false;
        button.classList.remove('loading');
        button.innerHTML = '<i class="fas fa-save"></i> Save Cloud Credentials';
    }
}

/**
 * Clear all form fields
 */
function clearForm() {
    const form = document.getElementById('cloudCredentialsForm');
    const inputs = form.querySelectorAll('input, textarea');
    
    inputs.forEach(input => {
        input.value = '';
        input.style.borderColor = '#333333';
        
        // Remove error messages
        const formGroup = input.closest('.form-group');
        const error = formGroup.querySelector('.field-error');
        if (error) {
            error.remove();
        }
    });
    
    // Reset section statuses
    updateAllSectionStatus();
    
    // Hide any feedback messages
    hideFeedback();
}

/**
 * Show success message
 */
function showSuccess(message) {
    showFeedback(message, 'success');
}

/**
 * Show error message
 */
function showError(message) {
    showFeedback(message, 'error');
}

/**
 * Show feedback message
 */
function showFeedback(message, type) {
    const feedback = document.getElementById('formFeedback');
    const messageElement = document.getElementById('feedbackMessage');
    const icon = feedback.querySelector('i');
    
    feedback.className = `form-feedback ${type}`;
    messageElement.textContent = message;
    
    if (type === 'success') {
        icon.className = 'fas fa-check-circle';
    } else {
        icon.className = 'fas fa-exclamation-circle';
    }
    
    feedback.style.display = 'block';
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
        hideFeedback();
    }, 5000);
}

/**
 * Hide feedback message
 */
function hideFeedback() {
    const feedback = document.getElementById('formFeedback');
    feedback.style.display = 'none';
}

/**
 * Handle file upload (alternative method)
 */
function handleFileUpload(input) {
    const file = input.files[0];
    if (file && file.type === 'application/json') {
        const reader = new FileReader();
        reader.onload = function(e) {
            const content = e.target.result;
            const textarea = document.getElementById('gcp_service_account');
            textarea.value = content;
            validateJSONContent(content);
            updateSectionStatus('gcp', true);
        };
        reader.readAsText(file);
    } else if (file) {
        showError('Please select a valid JSON file');
    }
}

/**
 * Show notification email step
 */
function showNotificationEmailStep() {
    const notificationStep = document.getElementById('notificationEmailStep');
    const credentialsForm = document.getElementById('cloudCredentialsForm');
    
    if (notificationStep && credentialsForm) {
        credentialsForm.style.display = 'none';
        notificationStep.style.display = 'block';
        
        // Initialize notification form
        initializeNotificationForm();
    }
}

/**
 * Initialize notification form
 */
function initializeNotificationForm() {
    const notificationForm = document.getElementById('notificationForm');
    const saveBtn = document.getElementById('saveNotificationBtn');
    
    if (notificationForm) {
        notificationForm.addEventListener('submit', handleNotificationSubmission);
    }
}

/**
 * Handle notification email submission
 */
function handleNotificationSubmission(e) {
    e.preventDefault();
    
    const form = e.target;
    const saveBtn = document.getElementById('saveNotificationBtn');
    const email = document.getElementById('notification_email').value.trim();
    
    // Validate email
    if (!email) {
        showError('Please enter a notification email address');
        return;
    }
    
    // Show loading state
    setLoadingState(saveBtn, true);
    
    // Prepare form data
    const formData = new FormData(form);
    
    // Submit notification email
    fetch('/save-notification-email', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        setLoadingState(saveBtn, false);
        
        if (data.success) {
            showSuccess(data.message || 'Notification email saved and baseline collection completed!');
            
            // Show baseline results
            if (data.baseline_counts) {
                showBaselineResults(data.baseline_counts, data.clouds_processed, data.errors);
            }
            
            // Redirect to dashboard after a delay
            setTimeout(() => {
                window.location.href = '/dashboard';
            }, 3000);
        } else {
            showError(data.message || 'Failed to save notification email. Please try again.');
        }
    })
    .catch(error => {
        setLoadingState(saveBtn, false);
        console.error('Error:', error);
        showError('An error occurred while saving notification email. Please try again.');
    });
}

/**
 * Skip notification email
 */
function skipNotificationEmail() {
    // Trigger baseline collection without notification email
    const saveBtn = document.getElementById('saveNotificationBtn');
    setLoadingState(saveBtn, true);
    
    fetch('/trigger-baseline', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        setLoadingState(saveBtn, false);
        
        if (data.success) {
            showSuccess('Baseline collection completed!');
            
            // Show baseline results
            if (data.counts) {
                showBaselineResults(data.counts, ['AWS', 'GCP', 'AZURE'], []);
            }
            
            // Redirect to dashboard after a delay
            setTimeout(() => {
                window.location.href = '/dashboard';
            }, 3000);
        } else {
            showError(data.message || 'Failed to run baseline collection. Please try again.');
        }
    })
    .catch(error => {
        setLoadingState(saveBtn, false);
        console.error('Error:', error);
        showError('An error occurred during baseline collection. Please try again.');
    });
}

/**
 * Show baseline collection results
 */
function showBaselineResults(counts, cloudsProcessed, errors) {
    const message = `Baseline collection completed! Found ${counts.aws_count + counts.gcp_count + counts.azure_count} resources across ${cloudsProcessed.join(', ')}.`;
    
    if (errors.length > 0) {
        showError(`Baseline collection completed with some errors: ${errors.join(', ')}`);
    } else {
        showSuccess(message);
    }
}
