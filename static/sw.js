// SMM Agent - Service Worker
// Handles caching, offline functionality, and background sync

const CACHE_NAME = 'smm-agent-v1';
const RUNTIME = 'runtime';

// Cache resources during install
const PRECACHE_URLS = [
  '/',
  '/static/css/style.css',
  '/static/js/app.js',
  '/static/js/offline.js',
  '/static/manifest.json',
  '/dashboard',
  '/schedule-post',
  '/bulk-upload',
  '/social/accounts',
  'https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js',
  'https://code.jquery.com/jquery-3.7.1.min.js'
];

// Install event - cache resources
self.addEventListener('install', event => {
  console.log('Service worker installing...');
  
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('Opened cache');
        return cache.addAll(PRECACHE_URLS);
      })
      .then(() => {
        console.log('Precached resources');
        return self.skipWaiting();
      })
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
  console.log('Service worker activating...');
  
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames
          .filter(cacheName => cacheName !== CACHE_NAME && cacheName !== RUNTIME)
          .map(cacheName => {
            console.log('Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          })
      );
    }).then(() => {
      console.log('Service worker activated');
      return self.clients.claim();
    })
  );
});

// Fetch event - serve from cache, fallback to network
self.addEventListener('fetch', event => {
  // Skip cross-origin requests
  if (!event.request.url.startsWith(self.location.origin)) {
    return;
  }

  // Handle API requests
  if (event.request.url.includes('/api/')) {
    event.respondWith(handleApiRequest(event.request));
    return;
  }

  // Handle form submissions
  if (event.request.method === 'POST') {
    event.respondWith(handleFormSubmission(event.request));
    return;
  }

  // Handle regular requests
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        // Return cached version if available
        if (response) {
          return response;
        }

        // Otherwise fetch from network
        return fetch(event.request).then(response => {
          // Don't cache if not a valid response
          if (!response || response.status !== 200 || response.type !== 'basic') {
            return response;
          }

          // Clone the response
          const responseToCache = response.clone();

          // Cache the response for next time
          caches.open(RUNTIME)
            .then(cache => {
              cache.put(event.request, responseToCache);
            });

          return response;
        }).catch(() => {
          // Return offline fallback for HTML requests
          if (event.request.mode === 'navigate') {
            return getOfflineFallback();
          }
        });
      })
  );
});

// Handle API requests with network-first strategy
async function handleApiRequest(request) {
  try {
    // Try network first
    const response = await fetch(request);
    
    // If successful, cache for later
    if (response.status === 200) {
      const cache = await caches.open(RUNTIME);
      cache.put(request, response.clone());
    }
    
    return response;
  } catch (error) {
    console.log('API request failed, checking cache:', request.url);
    
    // Fallback to cache
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }
    
    // Return offline response
    return new Response(JSON.stringify({
      error: 'Network unavailable',
      offline: true
    }), {
      status: 503,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

// Handle form submissions
async function handleFormSubmission(request) {
  try {
    // Try to submit normally
    return await fetch(request);
  } catch (error) {
    console.log('Form submission failed, storing offline');
    
    // Store form data for later sync
    const formData = await request.formData();
    const data = {};
    for (let [key, value] of formData.entries()) {
      data[key] = value;
    }
    
    // Store in IndexedDB via message to main thread
    const clients = await self.clients.matchAll();
    if (clients.length > 0) {
      clients[0].postMessage({
        type: 'STORE_OFFLINE_FORM',
        data: {
          url: request.url,
          method: request.method,
          data: data,
          timestamp: Date.now()
        }
      });
    }
    
    // Return success response to prevent error display
    return new Response(null, {
      status: 302,
      headers: {
        'Location': '/?offline=true'
      }
    });
  }
}

// Generate offline fallback page
function getOfflineFallback() {
  return new Response(`
    <!DOCTYPE html>
    <html lang="en" data-bs-theme="dark">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>Offline - SMM Agent</title>
      <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
      <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    </head>
    <body class="bg-dark text-light">
      <div class="container min-vh-100 d-flex align-items-center justify-content-center">
        <div class="text-center">
          <i class="fas fa-wifi-slash fa-4x text-muted mb-4"></i>
          <h1 class="h3 mb-3">You're Offline</h1>
          <p class="text-muted mb-4">
            Don't worry! You can still prepare your content offline.<br>
            Everything will sync when you're back online.
          </p>
          <div class="d-flex gap-3 justify-content-center">
            <button onclick="location.reload()" class="btn btn-primary">
              <i class="fas fa-refresh me-2"></i>Try Again
            </button>
            <button onclick="history.back()" class="btn btn-outline-secondary">
              <i class="fas fa-arrow-left me-2"></i>Go Back
            </button>
          </div>
          <hr class="my-4">
          <div class="row">
            <div class="col-md-6">
              <div class="card bg-dark border-secondary">
                <div class="card-body">
                  <i class="fas fa-edit fa-2x text-primary mb-3"></i>
                  <h6>Create Content</h6>
                  <p class="small text-muted">Prepare posts offline and sync later</p>
                </div>
              </div>
            </div>
            <div class="col-md-6">
              <div class="card bg-dark border-secondary">
                <div class="card-body">
                  <i class="fas fa-sync fa-2x text-success mb-3"></i>
                  <h6>Auto Sync</h6>
                  <p class="small text-muted">Changes sync automatically when online</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </body>
    </html>
  `, {
    headers: { 'Content-Type': 'text/html' }
  });
}

// Background sync event
self.addEventListener('sync', event => {
  console.log('Background sync event:', event.tag);
  
  if (event.tag === 'smm-agent-sync') {
    event.waitUntil(doBackgroundSync());
  }
});

// Perform background sync
async function doBackgroundSync() {
  console.log('Performing background sync...');
  
  try {
    // Notify main thread to process offline queue
    const clients = await self.clients.matchAll();
    clients.forEach(client => {
      client.postMessage({
        type: 'BACKGROUND_SYNC',
        timestamp: Date.now()
      });
    });
    
    console.log('Background sync completed');
  } catch (error) {
    console.error('Background sync failed:', error);
    throw error;
  }
}

// Push notification event
self.addEventListener('push', event => {
  console.log('Push notification received');
  
  const options = {
    body: 'Your scheduled post has been published!',
    icon: '/static/icons/icon-192.png',
    badge: '/static/icons/icon-96.png',
    tag: 'post-published',
    requireInteraction: true,
    actions: [
      {
        action: 'view',
        title: 'View Post'
      },
      {
        action: 'close',
        title: 'Close'
      }
    ]
  };
  
  if (event.data) {
    const data = event.data.json();
    options.body = data.message || options.body;
    options.data = data;
  }
  
  event.waitUntil(
    self.registration.showNotification('SMM Agent', options)
  );
});

// Notification click event
self.addEventListener('notificationclick', event => {
  console.log('Notification clicked:', event.action);
  
  event.notification.close();
  
  if (event.action === 'view') {
    event.waitUntil(
      clients.openWindow('/posts')
    );
  }
});

// Message event - communicate with main thread
self.addEventListener('message', event => {
  console.log('Service worker message:', event.data);
  
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
  
  if (event.data && event.data.type === 'CACHE_URLS') {
    event.waitUntil(
      caches.open(RUNTIME).then(cache => {
        return cache.addAll(event.data.urls);
      })
    );
  }
});

// Periodic background sync (if supported)
self.addEventListener('periodicsync', event => {
  if (event.tag === 'smm-agent-periodic-sync') {
    console.log('Periodic sync triggered');
    event.waitUntil(doBackgroundSync());
  }
});

// Handle cache storage quota
self.addEventListener('quotaexceeded', event => {
  console.warn('Storage quota exceeded');
  
  // Clean up old caches
  event.waitUntil(
    caches.keys().then(cacheNames => {
      // Keep only the latest cache
      const cachesToDelete = cacheNames.filter(name => 
        name !== CACHE_NAME && name !== RUNTIME
      );
      
      return Promise.all(
        cachesToDelete.map(name => caches.delete(name))
      );
    })
  );
});

console.log('Service worker loaded');
