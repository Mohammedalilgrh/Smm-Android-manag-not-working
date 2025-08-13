// Dashboard JavaScript for authenticated users
let userStats = {};
let userPosts = [];
let userAccounts = [];

// Initialize dashboard
document.addEventListener('DOMContentLoaded', function() {
    loadUserStats();
    loadUserPosts();
    loadUserAccounts();
    
    // Set up form handlers
    document.getElementById('postForm').addEventListener('submit', handlePostSubmit);
    document.getElementById('bulkUploadForm').addEventListener('submit', handleBulkUpload);
    
    // Schedule type change handler
    document.querySelectorAll('input[name="scheduleType"]').forEach(radio => {
        radio.addEventListener('change', function() {
            const picker = document.getElementById('datetimePicker');
            picker.style.display = this.value === 'later' ? 'block' : 'none';
        });
    });
    
    // Set minimum datetime to current time
    const now = new Date();
    now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
    document.getElementById('scheduleTime').min = now.toISOString().slice(0, 16);
});

function showTab(tabName) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.style.display = 'none';
    });
    
    // Remove active class from all tab buttons
    document.querySelectorAll('.nav-link').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Show selected tab and activate button
    const targetTab = document.getElementById(tabName + 'Tab');
    if (targetTab) {
        targetTab.style.display = 'block';
    }
    
    // Find and activate the correct button
    const buttons = document.querySelectorAll('.nav-link');
    buttons.forEach(btn => {
        if (btn.onclick && btn.onclick.toString().includes(tabName)) {
            btn.classList.add('active');
        }
    });
    
    // Refresh icons and load data if needed
    feather.replace();
    
    if (tabName === 'posts') {
        loadUserPosts();
    } else if (tabName === 'accounts') {
        loadUserAccounts();
    } else if (tabName === 'bulk') {
        loadBulkUploadHistory();
    }
}

async function loadUserStats() {
    try {
        const response = await fetch('/api/stats');
        if (response.ok) {
            userStats = await response.json();
            updateStatsDisplay();
        }
    } catch (error) {
        console.error('Failed to load user stats:', error);
    }
}

function updateStatsDisplay() {
    document.getElementById('totalPosts').textContent = userStats.total_posts || 0;
    document.getElementById('scheduledPosts').textContent = userStats.scheduled_posts || 0;
    document.getElementById('postedPosts').textContent = userStats.posted_posts || 0;
    document.getElementById('connectedAccounts').textContent = userStats.connected_accounts || 0;
}

async function loadUserPosts() {
    try {
        const response = await fetch('/api/posts');
        if (response.ok) {
            userPosts = await response.json();
            displayPosts();
        }
    } catch (error) {
        console.error('Failed to load posts:', error);
        showStatus('Failed to load posts', 'error');
    }
}

function displayPosts() {
    const container = document.getElementById('postsList');
    
    if (userPosts.length === 0) {
        container.innerHTML = `
            <div class="card">
                <div class="card-body text-center text-muted">
                    <i data-feather="calendar" class="mb-2" style="width: 48px; height: 48px;"></i>
                    <p class="mb-0">No posts yet. Create your first post!</p>
                </div>
            </div>
        `;
        feather.replace();
        return;
    }
    
    const postsHTML = userPosts.map(post => {
        const scheduledTime = new Date(post.scheduled_time);
        const createdTime = new Date(post.created_at);
        
        return `
            <div class="card mb-3 post-item ${post.status}">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-start mb-2">
                        <h5 class="card-title mb-1">${post.content.substring(0, 50)}${post.content.length > 50 ? '...' : ''}</h5>
                        <span class="badge ${getStatusBadgeClass(post.status)}">${post.status.toUpperCase()}</span>
                    </div>
                    
                    <p class="card-text">${post.content}</p>
                    
                    <div class="platform-badges mb-2">
                        ${(post.target_platforms || []).map(platform => `
                            <span class="badge bg-secondary me-1">
                                <i data-feather="${getPlatformIcon(platform)}" style="width: 12px; height: 12px;"></i>
                                ${platform}
                            </span>
                        `).join('')}
                    </div>
                    
                    <div class="row">
                        <div class="col-md-6">
                            <small class="text-muted">
                                <strong>Scheduled:</strong> ${scheduledTime.toLocaleString()}
                            </small>
                        </div>
                        <div class="col-md-6">
                            <small class="text-muted">
                                <strong>Created:</strong> ${createdTime.toLocaleString()}
                            </small>
                        </div>
                    </div>
                    
                    ${post.posting_results ? renderPostingResults(post.posting_results) : ''}
                    
                    <div class="mt-3">
                        <button class="btn btn-sm btn-outline-danger" onclick="deletePost(${post.id})">
                            <i data-feather="trash-2" style="width: 14px; height: 14px;"></i>
                            Delete
                        </button>
                    </div>
                </div>
            </div>
        `;
    }).join('');
    
    container.innerHTML = postsHTML;
    feather.replace();
}

function renderPostingResults(results) {
    if (!results || Object.keys(results).length === 0) return '';
    
    const resultsHTML = Object.entries(results).map(([platform, result]) => {
        const statusClass = result.status === 'posted' ? 'text-success' : 'text-danger';
        return `
            <div class="small ${statusClass}">
                <i data-feather="${getPlatformIcon(platform)}" style="width: 12px; height: 12px;"></i>
                ${platform}: ${result.status}
                ${result.platform_post_id ? `(ID: ${result.platform_post_id})` : ''}
            </div>
        `;
    }).join('');
    
    return `
        <div class="mt-2 p-2 bg-dark rounded">
            <small class="text-muted d-block mb-1"><strong>Posting Results:</strong></small>
            ${resultsHTML}
        </div>
    `;
}

function getStatusBadgeClass(status) {
    switch (status) {
        case 'posted': return 'bg-success';
        case 'scheduled': return 'bg-warning';
        case 'posting': return 'bg-info';
        case 'failed': return 'bg-danger';
        default: return 'bg-secondary';
    }
}

function getPlatformIcon(platform) {
    const icons = {
        'tiktok': 'video',
        'instagram': 'camera',
        'youtube': 'play'
    };
    return icons[platform] || 'circle';
}

async function loadUserAccounts() {
    try {
        const response = await fetch('/api/accounts');
        if (response.ok) {
            userAccounts = await response.json();
            displayAccounts();
            updatePlatformSelect();
        }
    } catch (error) {
        console.error('Failed to load accounts:', error);
        showStatus('Failed to load accounts', 'error');
    }
}

function displayAccounts() {
    const container = document.getElementById('connectedAccountsList');
    
    if (userAccounts.length === 0) {
        container.innerHTML = '<p class="text-muted mb-0">No accounts connected yet.</p>';
        return;
    }
    
    const accountsHTML = userAccounts.map(account => `
        <div class="d-flex justify-content-between align-items-center py-2 border-bottom">
            <div class="d-flex align-items-center">
                <i data-feather="${getPlatformIcon(account.platform)}" class="me-2"></i>
                <div>
                    <span class="fw-medium">${account.platform.charAt(0).toUpperCase() + account.platform.slice(1)}</span>
                    ${account.platform_username ? `<br><small class="text-muted">@${account.platform_username}</small>` : ''}
                </div>
                <span class="badge bg-success ms-2">Connected</span>
            </div>
            <button class="btn btn-sm btn-outline-danger" onclick="disconnectAccount(${account.id})">
                Disconnect
            </button>
        </div>
    `).join('');
    
    container.innerHTML = accountsHTML;
    feather.replace();
}

function updatePlatformSelect() {
    const container = document.getElementById('platformSelect');
    const platforms = ['tiktok', 'instagram', 'youtube'];
    const connectedPlatforms = userAccounts.map(acc => acc.platform);
    
    const platformsHTML = platforms.map(platform => {
        const isConnected = connectedPlatforms.includes(platform);
        const disabled = !isConnected ? 'disabled' : '';
        const title = !isConnected ? `Connect your ${platform} account first` : '';
        
        return `
            <div class="form-check">
                <input class="form-check-input" type="checkbox" value="${platform}" id="${platform}" ${disabled} title="${title}">
                <label class="form-check-label d-flex align-items-center" for="${platform}">
                    <i data-feather="${getPlatformIcon(platform)}" class="me-1"></i>
                    ${platform.charAt(0).toUpperCase() + platform.slice(1)}
                    ${!isConnected ? '<span class="badge bg-warning ms-2">Not Connected</span>' : ''}
                </label>
            </div>
        `;
    }).join('');
    
    container.innerHTML = platformsHTML;
    feather.replace();
}

async function handlePostSubmit(event) {
    event.preventDefault();
    
    const formData = new FormData(event.target);
    const content = document.getElementById('postContent').value.trim();
    const selectedPlatforms = Array.from(document.querySelectorAll('#platformSelect input[type="checkbox"]:checked'))
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
    
    const postData = {
        content: content,
        platforms: selectedPlatforms,
        scheduleType: scheduleType,
        scheduleTime: scheduleTime
    };
    
    try {
        const response = await fetch('/api/posts', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(postData)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showStatus(result.message || 'Post created successfully!', 'success');
            
            // Clear form
            document.getElementById('postContent').value = '';
            document.getElementById('mediaFile').value = '';
            document.querySelectorAll('#platformSelect input[type="checkbox"]').forEach(cb => cb.checked = false);
            document.querySelector('input[name="scheduleType"][value="now"]').checked = true;
            document.getElementById('datetimePicker').style.display = 'none';
            
            // Refresh data
            loadUserStats();
            loadUserPosts();
        } else {
            showStatus(result.error || 'Failed to create post', 'error');
        }
    } catch (error) {
        console.error('Failed to create post:', error);
        showStatus('Failed to create post', 'error');
    }
}

async function connectAccount(platform) {
    showStatus(`Connecting to ${platform}...`, 'info');
    
    try {
        const response = await fetch('/api/accounts', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ platform: platform })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showStatus(result.message || `${platform} connected successfully!`, 'success');
            loadUserAccounts();
            loadUserStats();
        } else {
            showStatus(result.error || `Failed to connect ${platform}`, 'error');
        }
    } catch (error) {
        console.error('Failed to connect account:', error);
        showStatus(`Failed to connect ${platform}`, 'error');
    }
}

async function disconnectAccount(accountId) {
    if (!confirm('Are you sure you want to disconnect this account?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/accounts/${accountId}/disconnect`, {
            method: 'POST'
        });
        
        if (response.ok) {
            showStatus('Account disconnected successfully', 'success');
            loadUserAccounts();
            loadUserStats();
        } else {
            const result = await response.json();
            showStatus(result.error || 'Failed to disconnect account', 'error');
        }
    } catch (error) {
        console.error('Failed to disconnect account:', error);
        showStatus('Failed to disconnect account', 'error');
    }
}

async function deletePost(postId) {
    if (!confirm('Are you sure you want to delete this post?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/posts/${postId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            showStatus('Post deleted successfully', 'success');
            loadUserPosts();
            loadUserStats();
        } else {
            const result = await response.json();
            showStatus(result.error || 'Failed to delete post', 'error');
        }
    } catch (error) {
        console.error('Failed to delete post:', error);
        showStatus('Failed to delete post', 'error');
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

async function handleBulkUpload(event) {
    event.preventDefault();
    
    const fileInput = document.getElementById('bulkFile');
    const scheduleType = document.getElementById('scheduleType').value;
    const startDate = document.getElementById('startDate').value;
    const platforms = Array.from(document.querySelectorAll('#bulkPlatformSelect input[type="checkbox"]:checked'))
        .map(cb => cb.value);
    
    if (!fileInput.files[0]) {
        showStatus('Please select a file to upload!', 'error');
        return;
    }
    
    if (platforms.length === 0) {
        showStatus('Please select at least one platform!', 'error');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('schedule_type', scheduleType);
    formData.append('start_date', startDate || new Date().toISOString());
    platforms.forEach(platform => formData.append('platforms', platform));
    
    try {
        showStatus('Uploading and processing your posts...', 'info');
        
        const response = await fetch('/api/bulk-upload', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showStatus(result.message || 'Bulk upload completed successfully!', 'success');
            
            // Clear form
            document.getElementById('bulkUploadForm').reset();
            
            // Refresh data
            loadUserStats();
            loadUserPosts();
            loadBulkUploadHistory();
        } else {
            showStatus(result.error || 'Bulk upload failed', 'error');
        }
    } catch (error) {
        console.error('Bulk upload error:', error);
        showStatus('Bulk upload failed', 'error');
    }
}

async function loadBulkUploadHistory() {
    try {
        const response = await fetch('/api/bulk-uploads');
        if (response.ok) {
            const uploads = await response.json();
            displayBulkUploadHistory(uploads);
        }
    } catch (error) {
        console.error('Failed to load bulk upload history:', error);
    }
}

function displayBulkUploadHistory(uploads) {
    const container = document.getElementById('bulkUploadHistory');
    
    if (uploads.length === 0) {
        container.innerHTML = '<p class="text-muted mb-0">No bulk uploads yet.</p>';
        return;
    }
    
    const uploadsHTML = uploads.map(upload => {
        const createdDate = new Date(upload.created_at);
        const statusClass = getStatusBadgeClass(upload.status);
        
        return `
            <div class="d-flex justify-content-between align-items-center py-2 border-bottom">
                <div>
                    <div class="fw-medium">${upload.name}</div>
                    <small class="text-muted">
                        ${upload.processed_posts}/${upload.total_posts} posts • 
                        ${upload.schedule_type} • 
                        ${createdDate.toLocaleDateString()}
                    </small>
                </div>
                <span class="badge ${statusClass}">${upload.status.toUpperCase()}</span>
            </div>
        `;
    }).join('');
    
    container.innerHTML = uploadsHTML;
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
