# Deployment Guide - Backend Only

This guide covers deploying the SEO Audit Agent backend on **Render**.

## Architecture

- **Backend (Python Agent)**: Deployed on Render as a Web Service

---

## 🐍 Backend Deployment (Render)

### Step 1: Prepare Repository

1. Push your code to GitHub/GitLab/Bitbucket
2. Ensure `render.yaml` is in the root directory
3. Ensure `agent/requirements.txt` exists and is up to date

### Step 2: Deploy to Render

#### Option A: Using render.yaml (Recommended)

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click "New +" → "Blueprint"
3. Connect your repository
4. Render will automatically detect `render.yaml` and create the service

#### Option B: Manual Setup

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click "New +" → "Web Service"
3. Connect your repository
4. Configure service:
   - **Name**: `seo-audit-agent`
   - **Region**: `Oregon` (or your preferred region)
   - **Branch**: `main` (or your main branch)
   - **Root Directory**: `./` (root of repo)
   - **Environment**: `Python 3`
   - **Build Command**: 
     ```bash
     python3 -m venv .venv && source .venv/bin/activate && pip install --upgrade pip && cd agent && pip install -r requirements.txt
     ```
   - **Start Command**:
     ```bash
     cd agent && ../.venv/bin/python agent.py
     ```
   - **Instance Type**: `Free` (or paid for better performance)

### Step 3: Set Environment Variables in Render

In your Render service → Environment tab, add:

#### Required Variables:

```bash
GOOGLE_API_KEY=your-google-api-key-here
```

#### Recommended Variables:

```bash
# Comma-separated list of frontend URLs (domains that will access this API)
ALLOWED_ORIGINS=https://your-frontend-domain.com,https://another-domain.com

# Firecrawl API key (if using web scraping)
FIRECRAWL_API_KEY=your-firecrawl-api-key-here
```

**Important**: 
- `PORT` is automatically set by Render - **don't set it manually**
- `ALLOWED_ORIGINS` should include all domains that will access your API
- Multiple origins should be comma-separated (no spaces after commas)
- Set these in the Render dashboard (Environment tab) for security

### Step 4: Deploy

1. Click "Save Changes"
2. Render will automatically start deploying
3. Wait for deployment to complete
4. Note your service URL (e.g., `https://seo-audit-agent.onrender.com`)

---

## ✅ Verification

### Test Backend:

```bash
curl https://your-agent-service.onrender.com/
```

Should return a JSON response (likely `{"detail":"Method Not Allowed"}` for GET, which is expected).

### Check API Documentation:

Visit your service URL in a browser:
- Swagger UI: `https://your-agent-service.onrender.com/docs`
- ReDoc: `https://your-agent-service.onrender.com/redoc`

---

## 🔧 Troubleshooting

### Backend won't start:

- ✅ Check Render logs for Python errors
- ✅ Verify `requirements.txt` is correct
- ✅ Check Python version compatibility (needs 3.10+)
- ✅ Verify `GOOGLE_API_KEY` is set correctly

### Agent not responding:

- ✅ Check `GOOGLE_API_KEY` is valid and has quota
- ✅ Check Render logs for API errors
- ✅ Verify `FIRECRAWL_API_KEY` is set if using web scraping features

### CORS errors (if accessing from frontend):

- ✅ Verify `ALLOWED_ORIGINS` in Render includes your exact frontend URL
- ✅ Make sure there are no trailing spaces in `ALLOWED_ORIGINS`
- ✅ Verify backend URL is accessible (not blocked by firewall)

### Port issues:

- ✅ Render automatically sets `PORT` - don't override it
- ✅ The agent code uses `os.getenv("PORT", "8000")` to handle this automatically

---

## 📝 Environment Variables Summary

### Render (Backend):
| Variable | Required | Auto-set | Example |
|----------|----------|----------|---------|
| `PORT` | Yes | ✅ Yes | (auto) |
| `GOOGLE_API_KEY` | Yes | ❌ No | `AIza...` |
| `ALLOWED_ORIGINS` | Recommended | ❌ No | `https://app.domain.com` |
| `FIRECRAWL_API_KEY` | Optional | ❌ No | `fc-...` |

---

## 🔄 Local Development

For local development, create `.env` in the root:

```bash
GOOGLE_API_KEY=your-api-key
FIRECRAWL_API_KEY=your-firecrawl-key  # optional
ALLOWED_ORIGINS=http://localhost:3000  # optional for local dev
```

Start the agent:
```bash
./scripts/run-agent.sh
```

Or directly:
```bash
cd agent
../.venv/bin/python agent.py
```

The agent will run on `http://localhost:8000` (or the port specified by `PORT`).

---

## 📚 Additional Resources

- [Render Documentation](https://render.com/docs)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
- [Python Virtual Environments](https://docs.python.org/3/tutorial/venv.html)
