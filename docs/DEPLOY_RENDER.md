# Deploy BESS Pipeline on Render – Step-by-step

This guide walks you through deploying the BESS Pipeline web app on [Render](https://render.com). The repo is already set up with a `Procfile` and optional `render.yaml` for one-click deploy.

---

## Prerequisites

- The repo is on **GitHub** (e.g. `https://github.com/hmelementsgreen/BESS_Projects_Web_Scraper`).
- A **Render** account (free at [render.com](https://render.com)).

---

## Option A: Deploy with the dashboard (recommended first time)

### Step 1: Sign in and create a Web Service

1. Go to [dashboard.render.com](https://dashboard.render.com) and sign in (or create an account with GitHub).
2. Click **New +** → **Web Service**.

### Step 2: Connect the GitHub repo

1. Under **Connect a repository**, click **Connect account** if you haven’t linked GitHub yet, and authorize Render.
2. Find **BESS_Projects_Web_Scraper** in the list and click **Connect** next to it.
3. If the repo doesn’t appear, click **Configure account** and ensure Render has access to the right GitHub account or organization.

### Step 3: Configure the service

1. **Name:** e.g. `bess-pipeline` (or any name; this becomes part of the URL).
2. **Region:** Choose the closest to you (e.g. Frankfurt, Oregon).
3. **Branch:** `main` (or the branch you push to).
4. **Runtime:** **Python 3**.
5. **Build Command:**  
   ```text
   pip install -r requirements.txt
   ```
6. **Start Command:**  
   ```text
   gunicorn -w 1 -b 0.0.0.0:$PORT --timeout 300 app:app
   ```  
   The `--timeout 300` is important so long scrapes (1–2 minutes) don’t get cut off.
7. **Plan:** Free (or choose a paid plan if you prefer).

### Step 4: (Optional) Environment variables

- Render sets **PORT** for you; no need to add it.
- If you add any env vars later (e.g. for the bot), use the **Environment** tab.

### Step 5: Deploy

1. Click **Create Web Service**.
2. Render will clone the repo, run the build command, then start the app. The first deploy can take a few minutes.
3. When the status is **Live**, open the URL shown (e.g. `https://bess-pipeline.onrender.com`).

### Step 6: Test the app

1. Open the app URL.
2. You should see the BESS Pipeline page (logo, “Refresh data”, “Bot last run”, “Summary”).
3. Click **Start scrape** and wait 1–2 minutes. When it finishes, the Summary and Bot last run should update and you can use the download links.

---

## Option B: Deploy with Blueprint (render.yaml)

If you prefer one-click from the repo:

1. In the Render dashboard, click **New +** → **Blueprint**.
2. Connect the same GitHub account/repo and select **BESS_Projects_Web_Scraper**.
3. Render will read `render.yaml` in the repo and create the web service with the settings defined there (build command, start command, plan).
4. Click **Apply** and wait for the service to be created and deployed.
5. Open the generated URL to use the app.

---

## After deploy

- **URL:** Your app will be at `https://<your-service-name>.onrender.com` (or a custom domain if you add one).
- **Free tier:** The service may **spin down** after ~15 minutes of no traffic. The first request after spin-down can take 30–60 seconds; scrapes themselves still run for 1–2 minutes once the request is accepted.
- **Logs:** In the Render dashboard, open your service → **Logs** to see build and runtime output (including scrape progress if you trigger one).
- **Bot:** The **scheduled bot** (`python bot.py --schedule`) does **not** run on the web service. To run scrapes on a schedule you’d need a separate **Background Worker** on Render (or an external cron) that runs `python bot.py --schedule` or `python bot.py --once` on a schedule.

---

## Troubleshooting

| Issue | What to do |
|--------|------------|
| Build fails | Check **Logs** for the build step. Ensure `requirements.txt` is in the repo and has no typos. |
| App crashes or “Application failed to respond” | Check **Logs** for Python errors. Ensure **Start Command** is exactly `gunicorn -w 1 -b 0.0.0.0:$PORT --timeout 300 app:app`. |
| Scrape times out | Start command must include `--timeout 300` (or higher). Re-deploy after changing it. |
| 502 / 503 after long idle | Normal on free tier (spin-down). Wait for the service to wake up on the first request. |

---

## Quick reference

| Setting | Value |
|--------|--------|
| Build Command | `pip install -r requirements.txt` |
| Start Command | `gunicorn -w 1 -b 0.0.0.0:$PORT --timeout 300 app:app` |
| Branch | `main` |
| Plan | Free (or paid) |

Your repo’s **Procfile** contains the same start command, so if you leave **Start Command** blank, Render can use the Procfile instead.
