OfflineManagerlineManagerSMM Agent - Offline Functionality
// Handles offline data storage, synchronization, and PWA features

class OfflineManager {
    constructor() {
        this.dbName = 'SMMAgentDB';
        this.dbVersion = 1;
        this.db = null;
        this.init();
    }

    async init() {
        await this.initDB();
        this.setupSyncListeners();
        this.scheduleSync();
    }

    // IndexedDB setup for robust offline storage
    async initDB() {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open(this.dbName, this.dbVersion);

            request.onerror = () => {
                console.error('IndexedDB error:', request.error);
                reject(request.error);
            };

            request.onsuccess = () => {
                this.db = request.result;
                console.log('IndexedDB initialized');
                resolve();
            };

            request.onupgradeneeded = (event) => {
                const db = event.target.result;

                // Posts store
                if (!db.objectStoreNames.contains('posts')) {
                    const postsStore = db.createObjectStore('posts', { keyPath: 'id', autoIncrement: true });
                    postsStore.createIndex('status', 'status', { unique: false });
                    postsStore.createIndex('created', 'created', { unique: false });
                }

                // Queue store for pending operations
                if (!db.objectStoreNames.contains('queue')) {
                    const queueStore = db.createObjectStore('queue', { keyPath: 'id', autoIncrement: true });
                    queueStore.createIndex('type', 'type', { unique: false });
                    queueStore.createIndex('priority', 'priority', { unique: false });
                }

                // Settings store
                if (!db.objectStoreNames.contains('settings')) {
                    db.createObjectStore('settings', { keyPath: 'key' });
                }

                console.log('IndexedDB schema created');
            };
        });
    }

    // Store post for offline editing
    async savePostOffline(post) {
        if (!this.db) return null;

        const transaction = this.db.transaction(['posts'], 'readwrite');
        const store = transaction.objectStore('posts');

        const postData = {
            ...post,
            status: 'offline',
            created: new Date().getTime(),
            modified: new Date().getTime()
        };

        return new Promise((resolve, reject) => {
            const request = store.add(postData);
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }

    // Get all offline posts
    async getOfflinePosts() {
        if (!this.db) return [];

        const transaction = this.db.transaction(['posts'], 'readonly');
        const store = transaction.objectStore('posts');

        return new Promise((resolve, reject) => {
            const request = store.getAll();
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }

    // Update offline post
    async updateOfflinePost(id, updates) {
        if (!this.db) return false;

        const transaction = this.db.transaction(['posts'], 'readwrite');
        const store = transaction.objectStore('posts');

        return new Promise((resolve, reject) => {
            const getRequest = store.get(id);
            
            getRequest.onsuccess = () => {
                const post = getRequest.result;
                if (post) {
                    const updatedPost = {
                        ...post,
                        ...updates,
                        modified: new Date().getTime()
                    };
                    
                    const putRequest = store.put(updatedPost);
                    putRequest.onsuccess = () => resolve(true);
                    putRequest.onerror = () => reject(putRequest.error);
                } else {
                    reject(new Error('Post not found'));
                }
            };
            
            getRequest.onerror = () => reject(getRequest.error);
        });
    }

    // Delete offline post
    async deleteOfflinePost(id) {
        if (!this.db) return false;

        const transaction = this.db.transaction(['posts'], 'readwrite');
        const store = transaction.objectStore('posts');

        return new Promise((resolve, reject) => {
            const request = store.delete(id);
            request.onsuccess = () => resolve(true);
            request.onerror = () => reject(request.error);
        });
    }

    // Queue operations for later sync
    async queueOperation(operation) {
        if (!this.db) return null;

        const transaction = this.db.transaction(['queue'], 'readwrite');
        const store = transaction.objectStore('queue');

        const queueItem = {
            ...operation,
            created: new Date().getTime(),
            priority: operation.priority || 1,
            attempts: 0,
            maxAttempts: operation.maxAttempts || 3
        };

        return new Promise((resolve, reject) => {
            const request = store.add(queueItem);
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }

    // Get queued operations
    async getQueuedOperations() {
        if (!this.db) return [];

        const transaction = this.db.transaction(['queue'], 'readonly');
        const store = transaction.objectStore('queue');

        return new Promise((resolve, reject) => {
            const request = store.getAll();
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }

    // Process sync queue
    async processQueue() {
        if (!navigator.onLine) {
            console.log('Offline - skipping queue processing');
            return;
        }

        const operations = await this.getQueuedOperations();
        console.log(`Processing ${operations.length} queued operations`);

        for (const operation of operations) {
            try {
                await this.processOperation(operation);
                await this.removeFromQueue(operation.id);
                console.log('Operation processed:', operation.type);
            } catch (error) {
                console.error('Failed to process operation:', operation.type, error);
                await this.incrementAttempts(operation.id);
            }
        }
    }

    // Process individual operation
    async processOperation(operation) {
        switch (operation.type) {
            case 'create_post':
                return await this.syncCreatePost(operation.data);
            case 'update_post':
                return await this.syncUpdatePost(operation.data);
            case 'delete_post':
                return await this.syncDeletePost(operation.data);
            case 'bulk_upload':
                return await this.syncBulkUpload(operation.data);
            default:
                throw new Error(`Unknown operation type: ${operation.type}`);
        }
    }

    // Sync operations with server
    async syncCreatePost(postData) {
        const response = await fetch('/api/posts', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(postData)
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await response.json();
    }

    async syncUpdatePost(postData) {
        const response = await fetch(`/api/posts/${postData.id}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(postData)
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await response.json();
    }

    async syncDeletePost(postId) {
        const response = await fetch(`/api/post/${postId}/delete`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await response.json();
    }

    async syncBulkUpload(uploadData) {
        const formData = new FormData();
        Object.keys(uploadData).forEach(key => {
            formData.append(key, uploadData[key]);
        });

        const response = await fetch('/bulk-upload', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await response.json();
    }

    // Queue management
    async removeFromQueue(id) {
        if (!this.db) return false;

        const transaction = this.db.transaction(['queue'], 'readwrite');
        const store = transaction.objectStore('queue');

        return new Promise((resolve, reject) => {
            const request = store.delete(id);
            request.onsuccess = () => resolve(true);
            request.onerror = () => reject(request.error);
        });
    }

    async incrementAttempts(id) {
        if (!this.db) return false;

        const transaction = this.db.transaction(['queue'], 'readwrite');
        const store = transaction.objectStore('queue');

        return new Promise((resolve, reject) => {
            const getRequest = store.get(id);
            
            getRequest.onsuccess = () => {
                const operation = getRequest.result;
                if (operation) {
                    operation.attempts = (operation.attempts || 0) + 1;
                    operation.lastAttempt = new Date().getTime();

                    // Remove if max attempts reached
                    if (operation.attempts >= operation.maxAttempts) {
                        console.warn('Max attempts reached for operation:', operation.type);
                        const deleteRequest = store.delete(id);
                        deleteRequest.onsuccess = () => resolve(true);
                        deleteRequest.onerror = () => reject(deleteRequest.error);
                    } else {
                        const putRequest = store.put(operation);
                        putRequest.onsuccess = () => resolve(true);
                        putRequest.onerror = () => reject(putRequest.error);
                    }
                } else {
                    reject(new Error('Operation not found'));
                }
            };
            
            getRequest.onerror = () => reject(getRequest.error);
        });
    }

    // Settings management
    async saveSetting(key, value) {
        if (!this.db) return false;

        const transaction = this.db.transaction(['settings'], 'readwrite');
        const store = transaction.objectStore('settings');

        return new Promise((resolve, reject) => {
            const request = store.put({ key, value, updated: new Date().getTime() });
            request.onsuccess = () => resolve(true);
            request.onerror = () => reject(request.error);
        });
    }

    async getSetting(key, defaultValue = null) {
        if (!this.db) return defaultValue;

        const transaction = this.db.transaction(['settings'], 'readonly');
        const store = transaction.objectStore('settings');

        return new Promise((resolve, reject) => {
            const request = store.get(key);
            request.onsuccess = () => {
                const result = request.result;
                resolve(result ? result.value : defaultValue);
            };
            request.onerror = () => reject(request.error);
        });
    }

    // Event listeners
    setupSyncListeners() {
        // Sync when coming online
        window.addEventListener('online', () => {
            console.log('Back online - starting sync');
            this.processQueue();
        });

        // Background sync when page becomes visible
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden && navigator.onLine) {
                this.processQueue();
            }
        });

        // Sync before page unload
        window.addEventListener('beforeunload', () => {
            if (navigator.onLine) {
                // Use sendBeacon for reliable delivery
                this.syncCriticalData();
            }
        });
    }

    // Schedule periodic sync
    scheduleSync() {
        // Sync every 5 minutes when online
        setInterval(() => {
            if (navigator.onLine) {
                this.processQueue();
            }
        }, 5 * 60 * 1000);

        // Clean up old data every hour
        setInterval(() => {
            this.cleanupOldData();
        }, 60 * 60 * 1000);
    }

    // Cleanup old offline data
    async cleanupOldData() {
        const cutoff = new Date().getTime() - (7 * 24 * 60 * 60 * 1000); // 7 days ago

        if (!this.db) return;

        const transaction = this.db.transaction(['posts', 'queue'], 'readwrite');
        
        // Clean up old posts
        const postsStore = transaction.objectStore('posts');
        const postsIndex = postsStore.index('created');
        const postsRequest = postsIndex.openCursor(IDBKeyRange.upperBound(cutoff));
        
        postsRequest.onsuccess = (event) => {
            const cursor = event.target.result;
            if (cursor) {
                cursor.delete();
                cursor.continue();
            }
        };

        // Clean up old queue items
        const queueStore = transaction.objectStore('queue');
        const queueIndex = queueStore.index('created');
        const queueRequest = queueIndex.openCursor(IDBKeyRange.upperBound(cutoff));
        
        queueRequest.onsuccess = (event) => {
            const cursor = event.target.result;
            if (cursor) {
                cursor.delete();
                cursor.continue();
            }
        };

        console.log('Cleaned up old offline data');
    }

    // Critical data sync using sendBeacon
    async syncCriticalData() {
        try {
            const operations = await this.getQueuedOperations();
            const criticalOps = operations.filter(op => op.priority === 1);
            
            if (criticalOps.length > 0 && navigator.sendBeacon) {
                const data = JSON.stringify({ operations: criticalOps });
                navigator.sendBeacon('/api/sync', data);
            }
        } catch (error) {
            console.error('Failed to sync critical data:', error);
        }
    }

    // Public API for form handling
    async handleOfflineForm(form) {
        const formData = new FormData(form);
        const data = {};
        
        for (let [key, value] of formData.entries()) {
            data[key] = value;
        }

        const operation = {
            type: 'create_post',
            data: data,
            priority: 1,
            url: form.action,
            method: form.method
        };

        await this.queueOperation(operation);
        console.log('Form queued for offline processing');
        
        return true;
    }

    // Export data for backup
    async exportData() {
        const data = {
            posts: await this.getOfflinePosts(),
            queue: await this.getQueuedOperations(),
            exported: new Date().toISOString()
        };

        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = `smm-agent-backup-${new Date().toISOString().split('T')[0]}.json`;
        a.click();
        
        URL.revokeObjectURL(url);
    }

    // Import data from backup
    async importData(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            
            reader.onload = async (e) => {
                try {
                    const data = JSON.parse(e.target.result);
                    
                    // Import posts
                    if (data.posts) {
                        for (const post of data.posts) {
                            await this.savePostOffline(post);
                        }
                    }
                    
                    // Import queued operations
                    if (data.queue) {
                        for (const operation of data.queue) {
                            await this.queueOperation(operation);
                        }
                    }
                    
                    resolve(true);
                } catch (error) {
                    reject(error);
                }
            };
            
            reader.onerror = () => reject(reader.error);
            reader.readAsText(file);
        });
    }
}

// Initialize offline manager
window.offlineManager = new OfflineManager();

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = OfflineManager;
}
