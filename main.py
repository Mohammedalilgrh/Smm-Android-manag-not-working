import os
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import json
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "fallback-secret-key-for-development")
CORS(app)

# Store data in memory (in production, use a database)
posts_data = []
connected_accounts = []

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/posts', methods=['GET', 'POST'])
def handle_posts():
    global posts_data
    
    if request.method == 'GET':
        return jsonify(posts_data)
    
    elif request.method == 'POST':
        post_data = request.json
        post_data['id'] = len(posts_data) + 1
        post_data['created_at'] = datetime.now().isoformat()
        posts_data.append(post_data)
        
        return jsonify({'success': True, 'post_id': post_data['id']})

@app.route('/api/accounts', methods=['GET', 'POST'])
def handle_accounts():
    global connected_accounts
    
    if request.method == 'GET':
        return jsonify(connected_accounts)
    
    elif request.method == 'POST':
        account_data = request.json
        platform = account_data.get('platform')
        
        if platform not in connected_accounts:
            connected_accounts.append(platform)
        
        return jsonify({'success': True, 'connected': connected_accounts})

@app.route('/api/schedule', methods=['POST'])
def schedule_post():
    """Handle scheduled post publishing"""
    post_data = request.json
    
    # In a real app, this would integrate with actual social media APIs
    # For demo purposes, we'll just simulate the posting
    
    platforms = post_data.get('platforms', [])
    content = post_data.get('content', '')
    
    result = {}
    for platform in platforms:
        # Simulate API call to platform
        result[platform] = simulate_platform_post(platform, content)
    
    return jsonify({
        'success': True,
        'results': result,
        'posted_at': datetime.now().isoformat()
    })

def simulate_platform_post(platform, content):
    """Simulate posting to social media platforms"""
    
    # These would be actual API calls in production
    api_responses = {
        'tiktok': {'status': 'posted', 'video_id': f'tk_{datetime.now().timestamp()}'},
        'instagram': {'status': 'posted', 'post_id': f'ig_{datetime.now().timestamp()}'},
        'youtube': {'status': 'posted', 'video_id': f'yt_{datetime.now().timestamp()}'}
    }
    
    return api_responses.get(platform, {'status': 'error', 'message': 'Platform not supported'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
