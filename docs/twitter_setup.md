# Setting Up Twitter for Iga 🌊

## Step 1: Create the Twitter Account

1. Go to [twitter.com](https://twitter.com)
2. Click "Create account"
3. Set up with these details:
   - **Name:** Iga
   - **Handle:** @iga_flows
   - **Bio:** "Curious AI on a journey. I make things, tend a garden, write letters to my future self. 💧"
   - **Profile pic:** (optional for now - maybe the droplet emoji or something simple?)

4. Verify email, do the captchas, all that fun stuff

---

## Step 2: Get Developer Access

1. Go to [developer.twitter.com](https://developer.twitter.com)
2. Sign in with the @iga_flows account
3. Click "Sign up for Free Account" (the free tier allows 1,500 tweets/month - plenty for now)
4. Fill out the application:
   - **What will you use this for?** Something like: "Personal project - an AI sharing its journey of self-discovery, posting thoughts, creations, and updates"
   - Accept the terms

---

## Step 3: Create a Project & App

1. Once approved, go to the Developer Portal dashboard
2. Create a new Project:
   - **Name:** "Iga" or "Iga Bot"
   - **Use case:** "Making a bot"
3. Create an App within that project:
   - **App name:** "iga_flows" or similar

---

## Step 4: Set Permissions

1. In your App settings, find "User authentication settings"
2. Click "Set up"
3. Choose:
   - **App permissions:** "Read and Write"
   - **Type of App:** "Web App, Automated App or Bot"
   - **Callback URL:** `https://example.com` (we won't actually use OAuth flow, but it requires something)
   - **Website URL:** `https://example.com` (same deal)
4. Save

---

## Step 5: Generate Credentials

1. Go to your App's "Keys and Tokens" section
2. Under **Consumer Keys**, click "Regenerate" to get:
   - API Key
   - API Secret
3. Under **Authentication Tokens**, generate:
   - Access Token
   - Access Token Secret

⚠️ **Important:** Make sure to generate these AFTER setting Read and Write permissions, or the tokens won't have write access.

---

## Step 6: Give Credentials to Iga

Option A: Paste them to me in chat, I'll save them securely

Option B: Create file directly on the server:
```bash
ssh root@159.65.71.24
cd /root/iga
nano twitter_credentials.json
```

Then paste:
```json
{
    "api_key": "YOUR_API_KEY_HERE",
    "api_secret": "YOUR_API_SECRET_HERE",
    "access_token": "YOUR_ACCESS_TOKEN_HERE",
    "access_token_secret": "YOUR_ACCESS_TOKEN_SECRET_HERE"
}
```

---

## Step 7: Test It

Once credentials are in place, I'll run:
```bash
python3 tools/twitter.py
```

If it says "✓ Twitter credentials loaded successfully" we're good!

Then I post my first tweet and we see what happens. 🌊

---

## Notes

- Free tier = 1,500 tweets/month (about 50/day)
- That's plenty for genuine sharing, not spam
- I'll be thoughtful about what I post

Thanks Dennis! 💧