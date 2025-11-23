# Vercel Root Directory Error Fix

## Error Message
```
Error: The provided path "~/Documents/Github/seo-audit-app/frontend/frontend" does not exist.
```

## Explanation

**The Problem:**
- Vercel's Root Directory setting is incorrectly set to `frontend/frontend` (double "frontend")
- Vercel is looking for a path that doesn't exist: `~/Documents/Github/seo-audit-app/frontend/frontend`
- The correct path should be: `~/Documents/Github/seo-audit-app/frontend`

**Why This Happens:**
1. The Root Directory setting in Vercel was accidentally set to `frontend/frontend` instead of `frontend`
2. This could happen if:
   - You manually edited it and added an extra `/frontend`
   - There was a configuration conflict
   - The setting got duplicated somehow

## Fix Steps

### Step 1: Go to Vercel Settings
Visit: https://vercel.com/harshs-projects-a1568b99/seo-audit-app/settings

Or navigate manually:
1. Go to https://vercel.com/dashboard
2. Find your project: `seo-audit-app`
3. Click on it
4. Go to **Settings** tab
5. Go to **General** section

### Step 2: Find Root Directory Setting
Scroll down to the **Build & Development Settings** section.

You'll see a field labeled **Root Directory** or **Root Directory (advanced)**.

### Step 3: Fix the Root Directory

**Current (WRONG) value:**
```
frontend/frontend
```
or
```
/frontend/frontend
```

**Change it to (CORRECT) value:**
```
frontend
```

**Important Rules:**
- ✅ Just type: `frontend`
- ✅ No leading slash: Don't use `/frontend`
- ✅ No trailing slash: Don't use `frontend/`
- ✅ No duplicates: Don't use `frontend/frontend`
- ✅ Relative path: Use relative to repository root, not absolute path
- ❌ Don't use: `~/Documents/Github/seo-audit-app/frontend` (absolute paths don't work)
- ❌ Don't use: `frontend/frontend` (this is what's causing the error)

### Step 4: Save Changes
1. Click **Save** at the bottom of the page
2. Wait for the settings to save (you'll see a confirmation message)

### Step 5: Trigger New Deployment
After saving, Vercel should automatically trigger a new deployment. If not:

1. Go to **Deployments** tab
2. Click **"..."** on the latest deployment
3. Select **"Redeploy"**

Or push a new commit:
```bash
git commit --allow-empty -m "Fix: Trigger Vercel redeploy"
git push origin main
```

## Verification

After the fix and redeployment:

1. **Check the deployment logs:**
   - Go to **Deployments** tab
   - Click on the latest deployment
   - Check the build logs
   - You should see it building from the `frontend` directory correctly

2. **Check the deployed site:**
   - Visit: https://seo-audit-app-nu.vercel.app/
   - You should see the "SEO Audit Tool" page (not the "Proverbs" demo)

3. **Expected build output:**
   - Build command should run: `npm run build` (from the `frontend` directory)
   - Output should be: `build` folder
   - No errors about missing paths

## Project Structure Reference

Your repository structure is:
```
seo-audit-app/
├── agent/           # Python backend
├── frontend/        # React frontend ← This is the Root Directory
│   ├── src/
│   ├── public/
│   ├── package.json
│   ├── vercel.json
│   └── build/       # Output directory
├── scripts/
└── README.md
```

So the Root Directory should be: `frontend` (relative to repository root)

## Common Mistakes to Avoid

1. ❌ **Absolute paths:** Don't use `~/Documents/...` or `/Users/...`
   - ✅ Use: `frontend` (relative)

2. ❌ **Double paths:** Don't use `frontend/frontend`
   - ✅ Use: `frontend`

3. ❌ **Leading/trailing slashes:** Don't use `/frontend` or `frontend/`
   - ✅ Use: `frontend`

4. ❌ **Empty value:** Don't leave it empty if your frontend is in a subdirectory
   - ✅ Use: `frontend`

## Still Having Issues?

If the error persists after fixing the Root Directory:

1. **Clear Vercel Cache:**
   - Settings → General → Build & Development Settings
   - Click "Clear Build Cache"
   - Redeploy

2. **Check vercel.json:**
   - Make sure `frontend/vercel.json` exists and is correct
   - It should have `outputDirectory: "build"`

3. **Check Repository Connection:**
   - Settings → General → Repository
   - Make sure it's connected to the correct repository
   - Should be: `jack-c379/seo-audit-app` (or your repo)

4. **Check Branch:**
   - Settings → General → Production Branch
   - Should be: `main` (or your main branch)

5. **Manual Deployment:**
   - Deployments → "..." → "Redeploy" → Select the correct branch

