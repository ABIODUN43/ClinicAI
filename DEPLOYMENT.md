# ClinicAI Sentinel Deployment Guide

This guide is the quickest path from the GitHub repository to a live Render deployment.

## What is already prepared

- frontend static deployment configuration in `render.yaml`
- backend web service configuration in `render.yaml`
- Docker deployment files for local container testing
- GitHub Actions CI for backend compile checks and frontend builds

## Recommended first deployment target

Use `Render Blueprint` deployment from GitHub.

Why:

- easiest setup for this repository
- supports both frontend and backend from one repo
- works well for prototype-to-demo deployment

## Before you deploy

Prepare these values:

- Google OAuth client ID
- strong JWT secret
- frontend public URL
- backend public URL
- optional SMTP/SMS/WhatsApp provider credentials

Use:

- `.env.render.example`

as your environment checklist.

## Render deployment steps

1. Sign in to Render.
2. Click `New`.
3. Choose `Blueprint`.
4. Connect your GitHub repository:
   - `ABIODUN43/ClinicAI`
5. Render will detect `render.yaml`.
6. Create the services.
7. Open the backend service and set environment variables from `.env.render.example`.
8. Open the frontend service and set:
   - `VITE_API_URL`
   - `VITE_GOOGLE_CLIENT_ID`
9. Redeploy both services after setting the variables.

## Important Google OAuth update

After Render gives you the frontend URL, add it in Google Cloud Console under:

- `Authorized JavaScript origins`

Example:

```text
https://clinicai-sentinel-frontend.onrender.com
```

## Recommended production improvements after first deploy

1. Switch from SQLite to PostgreSQL
2. Add real SMTP credentials
3. Add real SMS provider credentials
4. Add real WhatsApp provider credentials
5. Tighten role and admin account management

## First live checks after deployment

Backend health:

```text
https://your-backend-domain.onrender.com/api/health
```

Frontend:

```text
https://your-frontend-domain.onrender.com
```

## If something fails

- check Render build logs
- confirm `VITE_API_URL` points to the deployed backend
- confirm Google OAuth origin matches the deployed frontend URL
- confirm `APP_JWT_SECRET` is set
- confirm CORS values match the deployed frontend URL
