# 🚀 Deploy Your SMM Agent NOW

## Render Environment Variables

Add these to your Render app's Environment tab:

```bash
# Required
SESSION_SECRET=smm_agent_super_secure_key_2024_change_this_in_production

# Instagram (Ready to use!)
INSTAGRAM_APP_ID=1304680314575333
INSTAGRAM_APP_SECRET=e3e574ea09ccae27fdcaa0d1252c9560
INSTAGRAM_REDIRECT_URI=https://YOUR_APP_NAME.onrender.com/social/callback/instagram

# YouTube (Add when ready)
YOUTUBE_CLIENT_ID=your_youtube_client_id_here
YOUTUBE_CLIENT_SECRET=your_youtube_client_secret_here
YOUTUBE_REDIRECT_URI=https://YOUR_APP_NAME.onrender.com/social/callback/youtube

# TikTok (Add after app approval)
TIKTOK_CLIENT_KEY=your_tiktok_client_key_here
TIKTOK_CLIENT_SECRET=your_tiktok_client_secret_here
TIKTOK_REDIRECT_URI=https://YOUR_APP_NAME.onrender.com/social/callback/tiktok
```

## Instagram Setup (Final Step)

1. Go back to [developers.facebook.com](https://developers.facebook.com)
2. Open your SMM Agent app
3. Go to Instagram Basic Display → Basic Display
4. Add this redirect URI: `https://YOUR_APP_NAME.onrender.com/social/callback/instagram`
5. Save changes

**Replace YOUR_APP_NAME with your actual Render app name!**

## Deploy Status

✅ **Instagram** - Ready to connect  
⏳ **YouTube** - Need 2 more credentials  
⏳ **TikTok** - Need app review (can add later)

Your app is ready to deploy with Instagram working perfectly!