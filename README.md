# Smm-Android-
# Social Media Scheduler

A Progressive Web App (PWA) for scheduling social media posts across TikTok, Instagram, and YouTube.

## Features

- 📱 Progressive Web App with offline support
- 🌙 Dark theme Bootstrap interface
- 📅 Schedule posts for immediate or future publishing
- 🔗 Connect multiple social media accounts
- 📊 View and manage scheduled posts
- 🔄 Background sync for offline posting

## Quick Start

### Deploy on Render

1. **Create a new Web Service on Render**
   - Go to [render.com](https://render.com)
   - Click "New +" → "Web Service"
   - Connect your GitHub repository

2. **Configure the service**
   - Build Command: `pip install -r requirements_download.txt`
   - Start Command: `gunicorn --bind 0.0.0.0:$PORT main:app`
   - Environment: Python 3

3. **Set Environment Variables**
   - Add `SESSION_SECRET` with a random string value

### Local Development

1. **Install dependencies**
   ```bash
   pip install -r requirements_download.txt
   ```

2. **Run the application**
   ```bash
   python main.py
   ```

3. **Access the app**
   - Open http://localhost:5000 in your browser

## File Structure

```
├── main.py                    # Flask backend application
├── requirements_download.txt  # Python dependencies
├── templates/
│   └── index.html            # Main HTML template
├── static/
│   ├── style.css             # Custom CSS styles
│   ├── app.js                # Frontend JavaScript
│   ├── sw.js                 # Service Worker for PWA
│   └── manifest.json         # PWA manifest
└── README.md                 # This file
```

## Usage

1. **Connect Accounts**: Click on the social media buttons to simulate connecting your accounts
2. **Create Posts**: Write your content and select target platforms
3. **Schedule**: Choose to post immediately or schedule for later
4. **Manage**: View and delete scheduled posts in the "My Posts" tab

## Environment Variables

- `SESSION_SECRET`: Secret key for Flask sessions (required for production)

## Technologies Used

- **Backend**: Flask, Flask-CORS, Gunicorn
- **Frontend**: Bootstrap 5, Feather Icons, Vanilla JavaScript
- **PWA**: Service Worker, Web App Manifest
- **Deployment**: Render (recommended)

## Notes

- This is a demo application with simulated social media API calls
- For production use, integrate with actual social media APIs
- The app uses localStorage for client-side data persistence
- All scheduled posts are stored in browser localStorage

## License

MIT License - feel free to use this code for your projects!
