# Deployment Plan

## Architecture Overview
- **Backend**: Hosted on [Railway](https://railway.app/).
- **Frontend**: Hosted on [Vercel](https://vercel.com/).
- **Database**: (Specify if using Postgres/MongoDB/etc. hosted on Railway/Supabase/Atlas, etc.)

## Backend Deployment (Railway)
1. **Repository Setup**: Ensure the backend code is in a separate repository or a clear subdirectory if using a monorepo.
2. **Environment Variables**: Configure all necessary secrets and environment variables on Railway (e.g., database URLs, API keys, JWT secrets).
3. **Database Setup**: Provision any required databases in the Railway project (or external provider) and link the environment variables.
4. **Build & Start Commands**: Set up the correct build and start commands in the Railway project settings or via a `railway.json` / `Procfile`.
5. **Continuous Integration**: Link the GitHub repository to the Railway project to enable automatic deployments on pushes to the `main` branch.

## Frontend Deployment (Vercel)
1. **Repository Setup**: Ensure the frontend code (e.g., Next.js) is pushed to GitHub. ✅ Code updated to use REST API.
2. **Project Creation**: Import the `stitch_weekly_product_pulse_dashboard/` subdirectory into Vercel (set the **Root Directory** to `stitch_weekly_product_pulse_dashboard`).
3. **Environment Variables**: Add the following in Vercel project settings:
   - `NEXT_PUBLIC_API_URL` → Railway backend URL (e.g. `https://groww-review-agent-production.up.railway.app`)
4. **Build Settings**: Vercel auto-detects Next.js. A `vercel.json` is in place. ✅
5. **Continuous Integration**: Vercel will automatically build and deploy on pushes to `main`.

## Pre-Deployment Checklist
- [ ] Configure CORS on the backend to allow requests from the Vercel frontend domain.
- [ ] Ensure API routes in the frontend are dynamically using the backend URL environment variable.
- [ ] Verify sensitive environment variables are not hardcoded in the repository.
- [ ] Test a production build locally if possible.

## Post-Deployment Verification
- [ ] Test the live frontend URL.
- [ ] Ensure frontend can successfully communicate with the backend.
- [ ] Check logs on Railway and Vercel for any runtime errors.
- [ ] Verify database connections and data persistence.
