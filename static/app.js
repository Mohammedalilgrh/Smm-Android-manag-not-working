let connectedAccounts = JSON.parse(localStorage.getItem('connectedAccounts') || '[]');
let scheduledPosts = JSON.parse(localStorage.getItem('scheduledPosts') || '[]');
let isLoggedIn = localStorage.getItem('isLoggedIn') === 'true';

// Initialize app
document.addEventListener('DOMContentLoaded', function() {
    if (isLoggedIn && connectedAccounts.length > 0) {
        showMainApp();
    }
    
    // Schedule type change handler
    document.querySelectorAll('input[name="scheduleType"]').forEach(radio => {
        radio.addEventListener('change', function() {
            const picker = document.getElementById('datetimePicker');
            picker.style.display = this.value === 'later' ? 'block' : 'none';
        });
    });
    
    updateConnectedAccountsDisplay();
    displayScheduledPosts();
    
    // Set minimum datetime to current time
    const now = new Date();
    now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
    document.getElementById('scheduleTime').min = now.toISOString().slice(0, 16);
    
    // Initialize Bootstrap tooltips and toasts
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
});

function connectAccount(platform) {
    // Simulate OAuth connection
    showStatus('Connecting to ' + platform + '...', 'info');
    
    // Add loading state to button
    const buttons = document.querySelectorAll('.btn');
    buttons.forEach(btn => btn.classList.add('loading'));
    
    setTimeout(() => {
        if (!connectedAccounts.includes(platform)) {
            connectedAccounts.push(platform);
            localStorage.setItem('connectedAccounts', JSON.stringify(connectedAccounts));
            localStorage.setItem('isLoggedIn', 'true');
            isLoggedIn = true;
        }
        
        // Remove loading state
        buttons.forEach(btn => btn.classList.remove('loading'));
        
        showStatus('Successfully connected to ' + platform + '!', 'success');
        updateConnectedAccountsDisplay();
        
        if (connectedAccounts.length > 0) {
            setTimeout(() => {
                showMainApp();
            }, 1500);
        }
    }, 2000);
}

function showMainApp() {
    document.getElementById('authSection').style.display = 'none';
    document.getElementById('mainApp').style.display = 'block';
    feather.replace(); // Re-initialize icons
}

function showTab(tabName) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.style.display = 'none';
    });
    
    // Remove active class from all tab buttons
    document.querySelectorAll('.nav-link').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Show selected tab
    document.getElementById(tabName + 'Tab').style.display = 'block';
    event.target.classList.add('active');
    
    // Refresh icons after tab change
    feather.replace();
}

function createPost() {
    const content = document.getElementById('postContent').value.trim();
    const mediaFile = document.getElementById('mediaFile').files[0];
    const selectedPlatforms = Array.from(document.querySelectorAll('.platform-select input[type="checkbox"]:checked'))
        .map(cb => cb.value);
    const scheduleType = document.querySelector('input[name="scheduleType"]:checked').value;
    const scheduleTime = document.getElementById('scheduleTime').value;
    
    if (!content) {
        showStatus('Please enter post content!', 'error');
        return;
    }
    
    if (selectedPlatforms.length === 0) {
        showStatus('Please select at least one platform!', 'error');
        return;
    }
    
    if (scheduleType === 'later' && !scheduleTime) {
        showStatus('Please select a schedule time!', 'error');
        return;
    }
    
    const post = {
        id: Date.now(),
        content: content,
        platforms: selectedPlatforms,
        scheduleType: scheduleType,
        scheduleTime: scheduleType === 'later' ? new Date(scheduleTime) : new Date(),
        status: scheduleType === 'now' ? 'posted' : 'scheduled',
        createdAt: new Date()
    };
    
    scheduledPosts.unshift(post);
    localStorage.setItem('scheduledPosts', JSON.stringify(scheduledPosts));
    
    if (scheduleType === 'now') {
        simulatePosting(post);
    }
    
    // Clear form
    document.getElementById('postContent').value = '';
    document.getElementById('mediaFile').value = '';
    document.querySelectorAll('.platform-select input[type="checkbox"]').forEach(cb => cb.checked = false);
    document.querySelector('input[name="scheduleType"][value="now"]').checked = true;
    document.getElementById('datetimePicker').style.display = 'none';
    
    showStatus('Post ' + (scheduleType === 'now' ? 'published' : 'scheduled') + ' successfully!', 'success');
    displayScheduledPosts();
}

function simulatePosting(post) {
    // Simulate API calls to social media platforms
    post.platforms.forEach(platform => {
        setTimeout(() => {
            console.log(`Posted to ${platform}: ${post.content}`);
        }, Math.random() * 2000);
    });
}

function displayScheduledPosts() {
    const postsContainer = document.getElementById('postsList');
    
    if (scheduledPosts.length === 0) {
        postsContainer.innerHTML = `
            <div class="card">
                <div class="card-body text-center text-muted">
                    <i data-feather="calendar" class="mb-2" style="width: 48px; height: 48px;"></i>
                    <p class="mb-0">No posts scheduled yet. Create your first post!</p>
                </div>
            </div>
        `;
        feather.replace();
        return;
    }
    
    const postsHTML = scheduledPosts.map(post => `
        <div class="post-item ${post.status}" data-post-id="${post.id}">
            <div class="d-flex justify-content-between align-items-start mb-2">
                <h5 class="mb-1">${post.content.substring(0, 50)}${post.content.length > 50 ? '...' : ''}</h5>
                <span class="badge ${post.status === 'posted' ? 'bg-success' : 'bg-warning'}">${post.status}</span>
            </div>
            <p class="text-muted mb-2">${post.content}</p>
            <div class="platform-badges mb-2">
                ${post.platforms.map(platform => `
                    <span class="badge bg-secondary">${platform}</span>
                `).join('')}
            </div>
            <small class="text-muted">
                ${post.status === 'scheduled' ? 'Scheduled for: ' : 'Posted at: '}
                ${new Date(post.scheduleTime).toLocaleString()}
            </small>
            <div class="mt-2">
                <button class="btn btn-sm btn-outline-danger" onclick="deletePost(${post.id})">
                    <i data-feather="trash-2" style="width: 14px; height: 14px;"></i>
                    Delete
                </button>
            </div>
        </div>
    `).join('');
    
    postsContainer.innerHTML = postsHTML;
    feather.replace();
}

function deletePost(postId) {
    if (confirm('Are you sure you want to delete this post?')) {
        scheduledPosts = scheduledPosts.filter(post => post.id !== postId);
        localStorage.setItem('scheduledPosts', JSON.stringify(scheduledPosts));
        displayScheduledPosts();
        showStatus('Post deleted successfully!', 'success');
    }
}

function updateConnectedAccountsDisplay() {
    const container = document.getElementById('connectedAccounts');
    
    if (connectedAccounts.length === 0) {
        container.innerHTML = '<p class="text-muted mb-0">No accounts connected yet.</p>';
        return;
    }
    
    const accountsHTML = connectedAccounts.map(account => `
        <div class="connected-account-item">
            <div class="d-flex align-items-center">
                <i data-feather="${getAccountIcon(account)}" class="me-2"></i>
                <span class="text-capitalize">${account}</span>
                <span class="badge bg-success ms-2">Connected</span>
            </div>
            <button class="btn btn-sm btn-outline-danger" onclick="disconnectAccount('${account}')">
                Disconnect
            </button>
        </div>
    `).join('');
    
    container.innerHTML = accountsHTML;
    feather.replace();
}

function getAccountIcon(platform) {
    const icons = {
        'tiktok': 'video',
        'instagram': 'camera',
        'youtube': 'play'
    };
    return icons[platform] || 'circle';
}

function disconnectAccount(platform) {
    if (confirm(`Are you sure you want to disconnect your ${platform} account?`)) {
        connectedAccounts = connectedAccounts.filter(account => account !== platform);
        localStorage.setItem('connectedAccounts', JSON.stringify(connectedAccounts));
        updateConnectedAccountsDisplay();
        showStatus(`Disconnected from ${platform}`, 'info');
        
        if (connectedAccounts.length === 0) {
            logout();
        }
    }
}

function logout() {
    if (confirm('Are you sure you want to logout? This will disconnect all accounts.')) {
        localStorage.clear();
        location.reload();
    }
}

function showStatus(message, type = 'info') {
    const toast = document.getElementById('statusToast');
    const messageEl = document.getElementById('statusMessage');
    
    // Set message and type
    messageEl.textContent = message;
    toast.className = `toast ${type === 'error' ? 'bg-danger' : type === 'success' ? 'bg-success' : 'bg-info'} text-white`;
    
    // Show toast
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
}

// Register service worker for PWA
if ('serviceWorker' in navigator) {
    window.addEventListener('load', function() {
        navigator.serviceWorker.register('/static/sw.js')
            .then(function(registration) {
                console.log('ServiceWorker registration successful');
            })
            .catch(function(err) {
                console.log('ServiceWorker registration failed: ', err);
            });
    });
}

// Handle install prompt for PWA
let deferredPrompt;
window.addEventListener('beforeinstallprompt', (e) => {
    deferredPrompt = e;
    // Show install button or banner if needed
});
