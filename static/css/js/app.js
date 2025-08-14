// SMM Agent - Main Application JavaScript
// Mobile-first, offline-ready functionality

class SMMAgent {
    constructor() {
        this.isOnline = navigator.onLine;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.setupPWA();
        this.setupOfflineHandling();
        this.setupFormValidation();
        this.setupTooltips();
    }

    setupEventListeners() {
        document.addEventListener('DOMContentLoaded', () => {
            console.log('SMM Agent initialized');
            this.animateElements();
        });

        // Online/offline events
        window.addEventListener('online', () => this.handleOnline());
        window.addEventListener('offline', () => this.handleOffline());

        // Form submissions
        document.addEventListener('submit', (e) => {
            if (e.target.tagName === 'FORM') {
                this.handleFormSubmit(e);
            }
        });

        // Dynamic content loading
        document.addEventListener('click', (e) => {
            if (e.target.matches('[data-action]')) {
                this.handleAction(e);
            }
        });
    }

    setupPWA() {
        // Register service worker
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/static/sw.js')
                .then(registration => {
                    console.log('Service Worker registered:', registration);
                })
                .catch(error => {
                    console.log('Service Worker registration failed:', error);
                });
        }

        // Handle PWA installation
        let deferredPrompt;
        window.addEventListener('beforeinstallprompt', (e) => {
            e.preventDefault();
            deferredPrompt = e;
            this.showInstallButton();
        });

        // Handle app installed
        window.addEventListener('appinstalled', () => {
            console.log('PWA installed');
            this.hideInstallButton();
        });
    }

    setupOfflineHandling() {
        // Update online status
        this.updateOnlineStatus();

        // Cache form data for offline use
        this.setupOfflineStorage();
    }

    setupFormValidation() {
        // Real-time form validation
        document.addEventListener('input', (e) => {
            if (e.target.matches('input, textarea, select')) {
                this.validateField(e.target);
            }
        });
    }

    setupTooltips() {
        // Initialize Bootstrap tooltips
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(tooltipTriggerEl => {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }

    // Online/Offline handling
    handleOnline() {
        this.isOnline = true;
        this.updateOnlineStatus();
        this.syncOfflineData();
        console.log('App is online');
    }

    handleOffline() {
        this.isOnline = false;
        this.updateOnlineStatus();
        console.log('App is offline');
    }

    updateOnlineStatus() {
        const offlineBanner = document.getElementById('offline-banner');
        if (this.isOnline) {
            offlineBanner?.classList.add('d-none');
        } else {
            offlineBanner?.classList.remove('d-none');
        }
    }

    setupOfflineStorage() {
        // Store form data in localStorage for offline use
        document.addEventListener('input', (e) => {
            if (e.target.matches('textarea, input[type="text"], input[type="email"]')) {
                const formId = e.target.form?.id || 'default';
                const fieldName = e.target.name;
                const value = e.target.value;
                
                if (fieldName && value) {
                    this.setOfflineData(`${formId}_${fieldName}`, value);
                }
            }
        });
    }

    setOfflineData(key, value) {
        try {
            localStorage.setItem(`smm_offline_${key}`, value);
        } catch (e) {
            console.warn('Unable to save offline data:', e);
        }
    }

    getOfflineData(key) {
        try {
            return localStorage.getItem(`smm_offline_${key}`);
        } catch (e) {
            console.warn('Unable to retrieve offline data:', e);
            return null;
        }
    }

    clearOfflineData(key) {
        try {
            localStorage.removeItem(`smm_offline_${key}`);
        } catch (e) {
            console.warn('Unable to clear offline data:', e);
        }
    }

    syncOfflineData() {
        // Sync any offline form data when back online
        const offlineKeys = Object.keys(localStorage).filter(key => 
            key.startsWith('smm_offline_')
        );

        if (offlineKeys.length > 0) {
            console.log('Syncing offline data...');
            // In a real implementation, you would send this data to the server
            offlineKeys.forEach(key => {
                localStorage.removeItem(key);
            });
        }
    }

    // Form handling
    handleFormSubmit(e) {
        const form = e.target;
        const submitBtn = form.querySelector('button[type="submit"], input[type="submit"]');
        
        if (submitBtn) {
            this.showLoadingState(submitBtn);
        }

        // If offline, store form data
        if (!this.isOnline && form.method.toLowerCase() === 'post') {
            e.preventDefault();
            this.storeOfflineForm(form);
            this.showAlert('Form saved offline. Will sync when connection is restored.', 'info');
        }
    }

    showLoadingState(button) {
        const originalText = button.innerHTML;
        button.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Processing...';
        button.disabled = true;
        
        // Reset after timeout as fallback
        setTimeout(() => {
            button.innerHTML = originalText;
            button.disabled = false;
        }, 30000);
    }

    storeOfflineForm(form) {
        const formData = new FormData(form);
        const data = {};
        for (let [key, value] of formData.entries()) {
            data[key] = value;
        }
        
        const timestamp = new Date().getTime();
        this.setOfflineData(`form_${timestamp}`, JSON.stringify({
            action: form.action,
            method: form.method,
            data: data
        }));
    }

    // Field validation
    validateField(field) {
        const value = field.value.trim();
        const type = field.type;
        const required = field.hasAttribute('required');
        
        // Clear previous validation
        field.classList.remove('is-valid', 'is-invalid');
        
        // Skip validation for empty non-required fields
        if (!required && !value) return;
        
        let isValid = true;
        let errorMessage = '';
        
        // Required field validation
        if (required && !value) {
            isValid = false;
            errorMessage = 'This field is required';
        }
        
        // Type-specific validation
        if (value && type === 'email') {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(value)) {
                isValid = false;
                errorMessage = 'Please enter a valid email address';
            }
        }
        
        if (value && type === 'password') {
            if (value.length < 8) {
                isValid = false;
                errorMessage = 'Password must be at least 8 characters long';
            }
        }
        
        if (value && field.name === 'username') {
            if (value.length < 3) {
                isValid = false;
                errorMessage = 'Username must be at least 3 characters long';
            }
        }
        
        // Apply validation styling
        field.classList.add(isValid ? 'is-valid' : 'is-invalid');
        
        // Show error message
        if (!isValid) {
            this.showFieldError(field, errorMessage);
        } else {
            this.hideFieldError(field);
        }
        
        return isValid;
    }

    showFieldError(field, message) {
        // Remove existing error
        this.hideFieldError(field);
        
        // Create error element
        const errorDiv = document.createElement('div');
        errorDiv.className = 'invalid-feedback';
        errorDiv.textContent = message;
        
        // Insert after field
        field.parentNode.insertBefore(errorDiv, field.nextSibling);
    }

    hideFieldError(field) {
        const errorDiv = field.parentNode.querySelector('.invalid-feedback');
        if (errorDiv) {
            errorDiv.remove();
        }
    }

    // Action handling
    handleAction(e) {
        e.preventDefault();
        const action = e.target.dataset.action;
        
        switch (action) {
            case 'delete-post':
                this.deletePost(e.target.dataset.postId);
                break;
            case 'refresh-stats':
                this.refreshStats();
                break;
            default:
                console.log('Unknown action:', action);
        }
    }

    async deletePost(postId) {
        if (!confirm('Are you sure you want to delete this post?')) return;
        
        try {
            const response = await fetch(`/api/post/${postId}/delete`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showAlert('Post deleted successfully', 'success');
                // Remove post element from DOM
                const postElement = document.querySelector(`[data-post-id="${postId}"]`);
                if (postElement) {
                    postElement.remove();
                }
            } else {
                this.showAlert(data.error || 'Failed to delete post', 'danger');
            }
        } catch (error) {
            console.error('Error deleting post:', error);
            this.showAlert('Network error. Please try again.', 'danger');
        }
    }

    async refreshStats() {
        try {
            const response = await fetch('/api/stats');
            const stats = await response.json();
            
            // Update stats in the DOM
            Object.keys(stats).forEach(key => {
                const element = document.querySelector(`[data-stat="${key}"]`);
                if (element) {
                    element.textContent = stats[key];
                }
            });
            
            this.showAlert('Stats refreshed', 'success');
        } catch (error) {
            console.error('Error refreshing stats:', error);
            this.showAlert('Failed to refresh stats', 'danger');
        }
    }

    // PWA installation
    showInstallButton() {
        const installButton = document.createElement('button');
        installButton.id = 'pwa-install';
        installButton.className = 'btn btn-outline-primary position-fixed bottom-0 end-0 m-3';
        installButton.innerHTML = '<i class="fas fa-download me-2"></i>Install App';
        installButton.onclick = this.installPWA;
        document.body.appendChild(installButton);
    }

    hideInstallButton() {
        const installButton = document.getElementById('pwa-install');
        if (installButton) {
            installButton.remove();
        }
    }

    installPWA() {
        if (window.deferredPrompt) {
            window.deferredPrompt.prompt();
            window.deferredPrompt.userChoice.then((choiceResult) => {
                if (choiceResult.outcome === 'accepted') {
                    console.log('User accepted the install prompt');
                }
                window.deferredPrompt = null;
            });
        }
    }

    // Utility functions
    showAlert(message, type = 'info', duration = 5000) {
        // Create alert element
        const alert = document.createElement('div');
        alert.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        alert.style.cssText = 'top: 80px; right: 20px; z-index: 1050; max-width: 400px;';
        alert.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        // Add to page
        document.body.appendChild(alert);
        
        // Auto-dismiss
        setTimeout(() => {
            if (alert.parentNode) {
                alert.remove();
            }
        }, duration);
    }

    animateElements() {
        // Add fade-in animation to cards
        const cards = document.querySelectorAll('.card');
        cards.forEach((card, index) => {
            setTimeout(() => {
                card.classList.add('fade-in');
            }, index * 100);
        });
    }

    // Utility to show/hide loading overlay
    showLoading() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.classList.remove('d-none');
        }
    }

    hideLoading() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.classList.add('d-none');
        }
    }
}

// Global utility functions
window.showAlert = function(message, type = 'info') {
    if (window.smmAgent) {
        window.smmAgent.showAlert(message, type);
    }
};

// Initialize application
window.smmAgent = new SMMAgent();

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SMMAgent;
}
