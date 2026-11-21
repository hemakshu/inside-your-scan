# Inside Your Scan: YouTube Shorts autopilot

One radiology explainer Short a day, written, checked and made automatically.
**Nothing is uploaded until you tap ✅ on Telegram.**

## How a day works

1. **From 6 am IST**, the system picks a topic from `content/topics.yaml`, for example:
   - *What "hypoechoic" means*
   - *Why MRI is loud*
   - *Gallbladder stones on ultrasound*
2. **Claude writes the script**: the slides, the voiceover, the YouTube title, description and tags.
3. **Three safety layers:**
   - **Fixed rules:** nothing about the baby's sex, no clinic promotion, prices or cures, no clickbait, no diagnosing the viewer.
   - **An independent "senior radiologist" review by Claude.**
   - **Your tap** on Telegram.
4. **The video is made** in a reading-room style:
   - drawn ultrasound, CT, MRI and X-ray looks with calipers and arrows;
   - three layouts and three colour sets that rotate;
   - an AI voice and a soft ambient pad in a different key each time.

   Every frame says *"Drawn illustration · Not a real patient"*.
5. **You get the preview on Telegram** with the title and description, plus two buttons:
   - **✅ Publish**: it goes live from **5:30 pm IST** (morning in the US, afternoon in the UK).
   - **❌ Remake**: a new video comes at the next check.
     - Reply with a note (e.g. *"simpler, fewer numbers"*) and it redoes the same topic following your note.
     - Send `/topic Why MRI is loud` to choose the next subject yourself.
     - Send `/status` to see recent videos.
6. **It uploads to YouTube Shorts** and sends you the link.

The robot checks every 2 hours, so your tap takes effect at the next check. If you approve after 5:30 pm, it publishes at the next check, up until 11:30 pm.

---

## One-time setup (about 40 minutes)

### 1. YouTube channel
1. On YouTube, logged in with your Google account, open **profile picture → Settings → Add or manage your channels → Create a channel**.
2. Name it **Inside Your Scan**. This creates a separate brand channel, so your personal one stays untouched.
3. Add a profile picture, a banner and a short "About" text.
4. Verify your phone at **youtube.com/verify**.

### 2. Google Cloud (lets the robot upload)
1. Go to **console.cloud.google.com** and create a **New project** called "Inside Your Scan".
2. Open **APIs & Services → Library**, search **YouTube Data API v3** and click **Enable**.
3. Open **APIs & Services → OAuth consent screen**:
   - Choose **External**.
   - Enter an app name and your email, then **Save**.
   - Under **Audience**, add your Gmail as a test user.
   - Under **Branding**, set the home page to `https://hemakshu.github.io/`, the privacy policy to `https://hemakshu.github.io/privacy.html` and the authorised domain to `hemakshu.github.io`. Google won't let you publish without these.
   - **Important:** click **Publish app → In production**. While the app stays in "Testing", Google expires the sign-in after 7 days.
4. Open **APIs & Services → Credentials → Create credentials → OAuth client ID**:
   - Type: **Web application**.
   - Authorised redirect URI: `https://developers.google.com/oauthplayground`
   - Copy the **Client ID** (→ `YT_CLIENT_ID`) and the **Client secret** (→ `YT_CLIENT_SECRET`).

### 3. Get the YouTube refresh token (no software needed)
1. Open **developers.google.com/oauthplayground**.
2. Click the **⚙ gear** (top right), tick **Use your own OAuth credentials**, and paste the Client ID and secret.
3. In **Step 1**, type this into the box and click **Authorize APIs**:
   `https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.readonly`
4. Choose your Google account, then **pick the "Inside Your Scan" channel**, not your personal one.
   - Google will warn that the app isn't verified. Click **Advanced → Go to … (unsafe)**. It's your own app.
5. In **Step 2**, click **Exchange authorization code for tokens** and copy the **Refresh token** (→ `YT_REFRESH_TOKEN`).

### 4. Telegram bot
1. In Telegram, message **@BotFather**, send `/newbot`, and give it a name such as "Inside Your Scan Desk".
2. Copy the **token** (→ `TELEGRAM_BOT_TOKEN`).
3. Open your new bot and send it **hi**, so the bot knows where to message you.

### 5. GitHub
1. Create a **private repository** called `inside-your-scan` and upload everything in this folder, including `.github`.
2. Go to **Settings → Secrets and variables → Actions** and add:
   - `ANTHROPIC_API_KEY` (you can reuse the clinic's key)
   - `TELEGRAM_BOT_TOKEN`
   - `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN`
   - `TELEGRAM_CHAT_ID`: leave this out for now. Step 6 will tell you the number.

### 6. Test (Actions → Inside Your Scan → Run workflow)
1. **check-setup**: shows your Telegram chat number. Add it as `TELEGRAM_CHAT_ID` and run check-setup again until all three lines show ✅.
2. **test-preview**: sends a sample Short (fatty liver) to your Telegram so you can see the look. It's never uploaded.
3. **make-now**: makes a real video now, so you can try ✅. It publishes at the next check after 5:30 pm.

---

## Good to know
- **Upload visibility:** Google's documentation used to say that uploads from new, unaudited API projects are locked to *private*. The current documentation says they aren't. If your first upload comes out private, the bot tells you. The fix is YouTube's free API audit form: `support.google.com/youtube/contact/yt_api_form`.
- **Health label:** once the channel is established, apply for YouTube's **health source information** label for registered doctors in India. It adds credibility and can earn a place on YouTube's health shelf.
- **AI label:** not needed. The visuals are drawn and non-realistic, and the upload declares that.
- **Monetisation:** full monetisation needs 1,000 subscribers plus 10M Shorts views in 90 days, rising to 20M views from 1 Feb 2027. Adding your own recorded voice later, plus a weekly longer video, are the biggest helps.
- **GitHub minutes:** each check takes about 15 seconds and each video about 4 minutes. That's well within the free allowance. To make it unlimited, make the repo **public**; your keys stay secret either way.

## Changing things
| You want to… | Edit |
|---|---|
| Change the publish time | `config.yaml → schedule.publish_at` |
| Change the voice | `config.yaml → reel.voice` (e.g. `en-GB-RyanNeural`, `en-US-EmmaNeural`) |
| Add topics | `content/topics.yaml` |
| Pause | `config.yaml → paused: true` |
