# Vercel Deployment Setup for React App

## Error Explanation

**Error**: "No Next.js version detected..."

**Cause**: Vercel is trying to auto-detect Next.js framework, but this is a **Create React App** project (using `react-scripts`), not Next.js.

## Solution

A `vercel.json` configuration file has been created in the `frontend/` directory to tell Vercel:
- This is NOT a Next.js project
- Use Create React App build settings
- Build output goes to `build/` directory
- Configure routing for SPA (Single Page Application)

## Deployment Steps on Vercel

1. **Set Root Directory**:
   - Go to Vercel Project Settings → General
   - Set **Root Directory** to: `frontend`

2. **Build Settings** (should auto-detect with `vercel.json`):
   - **Framework Preset**: Other (or "Create React App" if available)
   - **Build Command**: `npm run build`
   - **Output Directory**: `build`
   - **Install Command**: `npm install`

3. **Environment Variables** (if needed):
   - Add any environment variables in Vercel dashboard
   - Example: `REACT_APP_API_URL=https://your-backend.onrender.com`

4. **Deploy**:
   - Push to your repository
   - Vercel will automatically detect `vercel.json` and use the correct settings

## Alternative: Manual Configuration

If Vercel still doesn't detect correctly, manually configure in Vercel dashboard:

1. **Framework Preset**: "Other" or "Create React App"
2. **Root Directory**: `frontend`
3. **Build Command**: `cd frontend && npm run build`
4. **Output Directory**: `frontend/build`
5. **Install Command**: `cd frontend && npm install`

## Notes

- The `vercel.json` file tells Vercel this is a static React app, not Next.js
- The `rewrites` rule handles client-side routing (SPA routing)
- All routes redirect to `/index.html` for React Router to handle

