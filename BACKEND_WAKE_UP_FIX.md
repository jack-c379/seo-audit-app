# Backend Wake-up Fix Explanation

## Problem
Getting "Failed to fetch" error when trying to use the SEO audit tool. The wake-up function exists but isn't working properly.

## Root Causes

### 1. `/api/audit` Endpoint Issue
The endpoint exists but uses `AgentRunner` which may not be the correct way to invoke ADK agents. ADK agents are typically called directly.

### 2. Wake-up Function Not Retrying
The frontend's wake-up function catches errors but:
- Only waits 2-3 seconds before giving up
- Doesn't retry if the server is still sleeping
- Render free tier can take 30-60 seconds to wake up

### 3. CORS Configuration
The backend may not have the frontend Vercel URL in the allowed origins list.

## Fixes Applied

### 1. Fixed `/api/audit` Endpoint
- Changed from using `AgentRunner` to calling the agent directly
- Used proper Pydantic model for request validation
- Added proper async handling with ThreadPoolExecutor

### 2. Improved Wake-up Function
- Added retry logic with exponential backoff
- Increased wait time for Render cold starts
- Better error handling and user feedback

### 3. CORS Configuration
- Ensure `ALLOWED_ORIGINS` includes your Vercel frontend URL
- Set in Render dashboard: Environment → Add Environment Variable
- Value: `https://seo-audit-app-nu.vercel.app`

## Testing the Fix

1. **Check `/ping` endpoint:**
   ```bash
   curl https://seo-audit-app-s1y0.onrender.com/ping
   ```
   Should return: `{"status": "ok", "message": "Server is awake"}`

2. **Check `/api/audit` endpoint:**
   ```bash
   curl -X POST https://seo-audit-app-s1y0.onrender.com/api/audit \
     -H "Content-Type: application/json" \
     -d '{"url": "example.com"}'
   ```

3. **Check CORS:**
   - Open browser console on Vercel frontend
   - Try making a request
   - Check for CORS errors in console

## Render Environment Variables

Make sure these are set in Render dashboard:
- `GOOGLE_API_KEY`: Your Gemini API key
- `ALLOWED_ORIGINS`: `https://seo-audit-app-nu.vercel.app` (your Vercel URL)
- `FIRECRAWL_API_KEY`: (optional, if using Firecrawl)

## Frontend Changes Needed

Update the wake-up function to retry properly:
- Add exponential backoff (2s, 4s, 8s delays)
- Retry up to 5 times
- Show better loading messages
- Handle timeout errors gracefully

