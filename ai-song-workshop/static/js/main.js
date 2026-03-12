// AI Song Workshop Website - Main JavaScript

// Global error handler
window.addEventListener('error', function(e) {
    console.error('Error:', e.error);
});

// Utility function for API calls
async function apiCall(url, method = 'GET', data = null) {
    const options = {
        method: method,
        headers: {
            'Content-Type': 'application/json'
        }
    };
    
    if (data) {
        options.body = JSON.stringify(data);
    }
    
    try {
        const response = await fetch(url, options);
        return await response.json();
    } catch (error) {
        console.error('API call failed:', error);
        throw error;
    }
}

// Form validation helper
function validateForm(formId) {
    const form = document.getElementById(formId);
    if (!form) return true;
    
    const inputs = form.querySelectorAll('input[required], textarea[required], select[required]');
    for (let input of inputs) {
        if (!input.value.trim()) {
            input.focus();
            return false;
        }
    }
    return true;
}

// Auto-save functionality
let autoSaveTimeout;
function scheduleAutoSave(callback, delay = 1000) {
    clearTimeout(autoSaveTimeout);
    autoSaveTimeout = setTimeout(callback, delay);
}

console.log('AI Song Workshop loaded');
