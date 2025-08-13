# Social Media Management (SMM) Scheduler

A comprehensive social media management application that allows you to schedule and post content across TikTok, Instagram, and YouTube platforms with real API integrations.

## Features

✅ **User Authentication System**
- Secure registration and login
- Password hashing with Werkzeug
- Session management

✅ **Real Social Media Integration**
- TikTok for Developers API
- Instagram Basic Display API  
- YouTube Data API v3
- OAuth 2.0 authentication flow

✅ **Bulk Upload Functionality**
- CSV/Excel file upload support
- Automatic daily scheduling
- Custom scheduling options
- Template file provided

✅ **Post Management**
- Create individual posts
- Schedule for specific times
- Multi-platform posting
- Real-time status tracking

✅ **Progressive Web App (PWA)**
- Mobile-responsive design
- Offline capabilities
- Service worker integration
- Bootstrap dark theme

✅ **Background Processing**
- Automatic post publishing
- Retry mechanism for failed posts
- Queue management system
- Error handling and logging

## Deployment Instructions

### 1. Environment Variables

Set up the following environment variables in your deployment platform:

#### Required for Database:
- `DATABASE_URL` - PostgreSQL connection string
- `SESSION_SECRET` - Secret key for sessions

#### For TikTok Integration:
- `TIKTOK_CLIENT_KEY` - Your TikTok app client key
- `TIKTOK_CLIENT_SECRET` - Your TikTok app client secret
- `TIKTOK_REDIRECT_URI` - Your callback URL (e.g., https://your-app.com/auth/tiktok/callback)

#### For Instagram Integration:
- `INSTAGRAM_APP_ID` - Your Instagram app ID
- `INSTAGRAM_APP_SECRET` - Your Instagram app secret
- `INSTAGRAM_REDIRECT_URI` - Your callback URL (e.g., https://your-app.com/auth/instagram/callback)

#### For YouTube Integration:
- `YOUTUBE_CLIENT_ID` - Your Google OAuth client ID
- `YOUTUBE_CLIENT_SECRET` - Your Google OAuth client secret
- `YOUTUBE_API_KEY` - Your YouTube Data API key
- `YOUTUBE_REDIRECT_URI` - Your callback URL (e.g., https://your-app.com/auth/youtube/callback)

### 2. Deploy on Render

1. Fork this repository to your GitHub account
2. Connect your GitHub repository to Render
3. Use the provided `render.yaml` configuration
4. Set up environment variables in Render dashboard
5. Deploy the application

#### Render Commands:
- **Build Command**: `pip install -r deployment_requirements.txt`
- **Start Command**: `gunicorn --bind 0.0.0.0:$PORT main:app`

### 3. Deploy on Heroku

1. Install Heroku CLI
2. Create a new Heroku app:
   ```bash
   heroku create your-app-name
   ```
3. Add PostgreSQL addon:
   ```bash
   heroku addons:create heroku-postgresql:mini
   ```
4. Set environment variables:
   ```bash
   heroku config:set SESSION_SECRET=your-secret-key
   heroku config:set TIKTOK_CLIENT_KEY=your-tiktok-key
   # ... add all other environment variables
   ```
5. Deploy:
   ```bash
   git push heroku main
   ```

### 4. Local Development

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd smm-scheduler
   ```

2. Install dependencies:
   ```bash
   pip install -r deployment_requirements.txt
   ```

3. Set up environment variables in a `.env` file:
   ```
   DATABASE_URL=postgresql://username:password@localhost/smm_scheduler
   SESSION_SECRET=your-development-secret
   # Add API keys for social media platforms
   ```

4. Run the application:
   ```bash
   python main.py
   ```

## API Setup Instructions

### TikTok for Developers

1. Visit [TikTok for Developers](https://developers.tiktok.com/)
2. Create a new app and get your Client Key and Client Secret
3. Set redirect URI to `https://your-domain.com/auth/tiktok/callback`
4. Request scopes: `user.info.basic`, `video.list`, `video.upload`

### Instagram Basic Display API

1. Visit [Facebook Developers](https://developers.facebook.com/)
2. Create a new app and add Instagram Basic Display product
3. Get your App ID and App Secret
4. Set redirect URI to `https://your-domain.com/auth/instagram/callback`
5. Request scopes: `user_profile`, `user_media`

### YouTube Data API v3

1. Visit [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project and enable YouTube Data API v3
3. Create OAuth 2.0 credentials
4. Set redirect URI to `https://your-domain.com/auth/youtube/callback`
5. Request scopes: `https://www.googleapis.com/auth/youtube.upload`

## Usage Instructions

### Single Post Creation

1. Log in to your account
2. Connect your social media accounts in the "Accounts" tab
3. Use the "Schedule Post" tab to create individual posts
4. Select platforms, set schedule time, and publish

### Bulk Upload

1. Download the CSV template from the "Bulk Upload" tab
2. Fill in your posts with the following columns:
   - `content` (required): Your post text
   - `platforms` (optional): Comma-separated platforms (tiktok,instagram,youtube)
   - `hashtags` (optional): Comma-separated hashtags
3. Upload the file and select scheduling options
4. Posts will be automatically scheduled according to your preferences

### CSV Template Format

```csv
content,platforms,hashtags
"Check out our amazing new product! #innovation #tech","tiktok,instagram","#product #launch #tech"
"Behind the scenes of our creative process","instagram,youtube","#behindthescenes #creative"
"Tips for improving your productivity 🚀","tiktok,instagram,youtube","#productivity #tips #motivation"
```

## File Structure

```
├── app.py                           # Flask application setup
├── main.py                          # Application entry point
├── models.py                        # Database models
├── auth.py                          # Authentication routes
├── routes.py                        # Basic routes
├── enhanced_routes.py               # API and social auth routes
├── social_media_integrations.py    # Real API integrations
├── bulk_upload_service.py           # Bulk upload processing
├── templates/                       # HTML templates
│   ├── auth/
│   │   ├── login.html
│   │   ├── register.html
│   │   └── profile.html
│   ├── dashboard.html
│   └── index.html
├── static/                          # Static files
│   ├── dashboard.js                 # Dashboard JavaScript
│   ├── style.css                    # Custom styles
│   ├── sw.js                        # Service worker
│   ├── manifest.json                # PWA manifest
│   └── bulk_upload_template.csv     # CSV template
├── deployment_requirements.txt      # Python dependencies
├── render.yaml                      # Render deployment config
├── Procfile                         # Heroku deployment config
└── README.md                        # This file
```

## Features in Detail

### Authentication & Security
- Secure password hashing using Werkzeug
- Session-based authentication with Flask-Login
- CSRF protection
- Environment-based configuration

### Database Schema
- User management with profile information
- Post scheduling and status tracking
- Social account connection management
- Bulk upload history and processing
- Background queue management

### Social Media Integration
- Real OAuth flows for all platforms
- Token management and refresh
- Error handling and retry logic
- Platform-specific posting logic
- Status tracking and result storage

### Bulk Processing
- CSV and Excel file parsing
- Flexible column mapping
- Daily scheduling distribution
- Background processing with queue
- Progress tracking and error reporting

### Mobile & PWA Support
- Responsive Bootstrap design
- Service worker for offline functionality
- Web app manifest for installation
- Touch-friendly interface
- Dark theme optimized for mobile

## Support

For issues and feature requests, please check the deployment logs and ensure all environment variables are properly configured.

## License

This project is licensed under the MIT License.
