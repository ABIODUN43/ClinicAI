# ClinicAI Sentinel

React frontend plus FastAPI backend for AI-powered Lassa fever early warning, analytics, and clinic decision support in Nigeria.

## What is ready

- React dashboard with `Home`, `Analytics`, and `Disease Alerts`
- FastAPI backend with:
  - `GET /api/health`
  - `POST /api/auth/google`
  - `GET /api/auth/me`
  - `GET /api/dashboard/home`
  - `GET /api/dashboard/analytics`
  - `GET /api/dashboard/alerts`
  - `GET /api/signals`
  - `POST /api/signals`
  - `GET /api/predictions`
  - `POST /api/predictions`
  - `GET /api/alerts`
  - `POST /api/alerts`
  - `GET /api/recommendations`
  - `POST /api/recommendations`
  - `GET /api/clinic-reports`
  - `POST /api/clinic-reports`
  - `GET /api/model/status`
  - `POST /api/model/train`
  - `GET /api/dataset/status`
  - `GET /api/dataset/reports`
  - `POST /api/dataset/run-auto`
  - `GET /api/model/history`
- Local demo mode for development before Google OAuth is configured
- Bearer-token auth flow between frontend and backend
- SQLAlchemy database layer with seeded local data and PostgreSQL-ready structure
- NCDC historical-data pipeline scaffold for extracting SITREPs into SQLite training labels

## Ingestion layer

The backend now supports authenticated writes for live pipeline integration:

- crawler/NLP outputs can be sent to `POST /api/signals`
- ML model outputs can be sent to `POST /api/predictions`
- decision engine alerts can be sent to `POST /api/alerts`
- clinic-facing actions can be sent to `POST /api/recommendations`
- frontline clinic symptom submissions can be sent to `POST /api/clinic-reports`

## Query filtering

The read endpoints now support simple filtering so analysts and integrations can query only what they need.

Examples:

```text
GET /api/signals?disease=Lassa%20fever&classification=Red&min_confidence=0.8
GET /api/predictions?risk_level=High&location=Ondo
GET /api/alerts?level=Red
GET /api/recommendations?priority=High
GET /api/clinic-reports?disease=Lassa%20fever&severity=High
```

## Example ingestion scripts

Example local scripts are included for quick testing:

```powershell
.venv\Scripts\python.exe backend\scripts\ingest_signal.py http://127.0.0.1:8000 demo-session
.venv\Scripts\python.exe backend\scripts\submit_clinic_report.py http://127.0.0.1:8000 demo-session
```

## Historical data pipeline

The backend now includes a first-pass historical-data layer for NCDC Lassa fever reports.

- [backend/scripts/extract_ncdc_sitrep.py](C:\Users\user\Documents\Codex\2026-04-23-can-you-design-ui-ux\backend\scripts\extract_ncdc_sitrep.py)
  extracts SITREP metadata from a PDF, writes JSON, and now also writes a state-review CSV plus optional override workflow
- [backend/scripts/load_historical_dataset.py](C:\Users\user\Documents\Codex\2026-04-23-can-you-design-ui-ux\backend\scripts\load_historical_dataset.py)
  loads extracted report labels into SQLite
- [backend/scripts/build_training_dataset.py](C:\Users\user\Documents\Codex\2026-04-23-can-you-design-ui-ux\backend\scripts\build_training_dataset.py)
  merges historical labels with available weather, symptom, and news features to produce training rows

Included sample extracted payload:

- [backend/data/ncdc_lassa_week2_2026.json](C:\Users\user\Documents\Codex\2026-04-23-can-you-design-ui-ux\backend\data\ncdc_lassa_week2_2026.json)
- [backend/data/historical_weather_week2_2026.csv](C:\Users\user\Documents\Codex\2026-04-23-can-you-design-ui-ux\backend\data\historical_weather_week2_2026.csv)
- [backend/data/historical_symptoms_week2_2026.csv](C:\Users\user\Documents\Codex\2026-04-23-can-you-design-ui-ux\backend\data\historical_symptoms_week2_2026.csv)
- [backend/data/historical_news_week2_2026.csv](C:\Users\user\Documents\Codex\2026-04-23-can-you-design-ui-ux\backend\data\historical_news_week2_2026.csv)

Improved SITREP extraction workflow:

```powershell
.venv\Scripts\python.exe backend\scripts\extract_ncdc_sitrep.py "C:\path\to\report.pdf"
```

That now creates:

- extracted JSON payload
- `*_state_review.csv` with the inferred state metrics
- optional `*_state_overrides.csv` path you can create and rerun to merge corrections automatically

If you need to correct low-confidence state rows, fill the override CSV and rerun:

```powershell
.venv\Scripts\python.exe backend\scripts\extract_ncdc_sitrep.py "C:\path\to\report.pdf" "C:\path\to\output.json" "C:\path\to\output_state_overrides.csv"
```

Historical weather import:

- [backend/scripts/load_historical_weather.py](C:\Users\user\Documents\Codex\2026-04-23-can-you-design-ui-ux\backend\scripts\load_historical_weather.py)
  loads `state + epi week` weather features into SQLite for model training
- [backend/scripts/backfill_historical_weather_openmeteo.py](C:\Users\user\Documents\Codex\2026-04-23-can-you-design-ui-ux\backend\scripts\backfill_historical_weather_openmeteo.py)
  pulls real historical weekly weather from Open-Meteo archive data and writes CSVs into `backend/data/historical/weather`
- [backend/scripts/load_historical_symptoms.py](C:\Users\user\Documents\Codex\2026-04-23-can-you-design-ui-ux\backend\scripts\load_historical_symptoms.py)
  loads historical symptom aggregates by `state + epi week`
- [backend/scripts/import_symptom_line_list.py](C:\Users\user\Documents\Codex\2026-04-23-can-you-design-ui-ux\backend\scripts\import_symptom_line_list.py)
  imports clinic-style line-list symptom CSVs into the app database as structured `symptom_reports`
- [backend/scripts/backfill_historical_symptoms_from_db.py](C:\Users\user\Documents\Codex\2026-04-23-can-you-design-ui-ux\backend\scripts\backfill_historical_symptoms_from_db.py)
  aggregates stored `symptom_reports` into weekly state-level historical symptom CSVs for model training
- [backend/scripts/load_historical_news.py](C:\Users\user\Documents\Codex\2026-04-23-can-you-design-ui-ux\backend\scripts\load_historical_news.py)
  loads historical NLP/news aggregates by `state + epi week`
- [backend/scripts/import_historical_news_articles.py](C:\Users\user\Documents\Codex\2026-04-23-can-you-design-ui-ux\backend\scripts\import_historical_news_articles.py)
  imports curated historical article CSVs into the app database as `news_records`
- [backend/scripts/backfill_historical_news_from_db.py](C:\Users\user\Documents\Codex\2026-04-23-can-you-design-ui-ux\backend\scripts\backfill_historical_news_from_db.py)
  aggregates stored `news_records` into weekly state-level historical news CSVs using the NLP layer
- [backend/scripts/run_historical_batch.py](C:\Users\user\Documents\Codex\2026-04-23-can-you-design-ui-ux\backend\scripts\run_historical_batch.py)
  loads a manifest of report/weather/symptom/news files, rebuilds the training dataset, and retrains the baseline model in one pass
- [backend/data/historical_batch_manifest.json](C:\Users\user\Documents\Codex\2026-04-23-can-you-design-ui-ux\backend\data\historical_batch_manifest.json)
  sample batch manifest for repeatable multi-week ingestion

Auto-discovery folders for drop-in historical files:

- [backend/data/historical/reports](C:\Users\user\Documents\Codex\2026-04-23-can-you-design-ui-ux\backend\data\historical\reports)
- [backend/data/historical/weather](C:\Users\user\Documents\Codex\2026-04-23-can-you-design-ui-ux\backend\data\historical\weather)
- [backend/data/historical/symptoms](C:\Users\user\Documents\Codex\2026-04-23-can-you-design-ui-ux\backend\data\historical\symptoms)
- [backend/data/historical/news](C:\Users\user\Documents\Codex\2026-04-23-can-you-design-ui-ux\backend\data\historical\news)

You can now run:

```powershell
.venv\Scripts\python.exe backend\scripts\run_historical_batch.py --auto
```

That command scans the four folders above, loads every matching file, rebuilds the training dataset, and retrains the baseline model automatically.

To create a new week pack quickly:

```powershell
.venv\Scripts\python.exe backend\scripts\generate_historical_week_pack.py 2026 3 "12th January" "18th January 2026"
```

That generator creates all four files for the requested week directly inside the auto-discovery folders:

- report JSON in `backend/data/historical/reports`
- weather CSV in `backend/data/historical/weather`
- symptoms CSV in `backend/data/historical/symptoms`
- news CSV in `backend/data/historical/news`

After filling the generated files with real values, run:

```powershell
.venv\Scripts\python.exe backend\scripts\run_historical_batch.py --auto
```

To replace proxy weather with real historical weather backfill from Open-Meteo:

```powershell
.venv\Scripts\python.exe backend\scripts\backfill_historical_weather_openmeteo.py backend\data\historical\reports\ncdc_lassa_week7_2026.json backend\data\historical\reports\ncdc_lassa_week8_2026.json
```

That command reads the report week dates, fetches historical weather for the states found in the report file, and writes richer CSV rows back into `backend/data/historical/weather`.

To move symptom history from proxy values toward real clinic aggregates:

```powershell
.venv\Scripts\python.exe backend\scripts\import_symptom_line_list.py backend\data\templates\clinic_symptom_line_list_template.csv
.venv\Scripts\python.exe backend\scripts\backfill_historical_symptoms_from_db.py
```

That flow turns clinic-style symptom rows into real `symptom_reports`, then rolls them up into week-level CSVs under `backend/data/historical/symptoms`.

To move news history from proxy counts toward article-driven NLP aggregates:

```powershell
.venv\Scripts\python.exe backend\scripts\import_historical_news_articles.py backend\data\templates\historical_news_articles_template.csv
.venv\Scripts\python.exe backend\scripts\backfill_historical_news_from_db.py
```

That flow imports verified article records and aggregates them into week-level historical news CSVs under `backend/data/historical/news`.

## Baseline model layer

The backend now supports a no-extra-dependency baseline training flow built on the SQLite training dataset.

- [backend/scripts/train_baseline_model.py](C:\Users\user\Documents\Codex\2026-04-23-can-you-design-ui-ux\backend\scripts\train_baseline_model.py)
  trains and saves a reusable model artifact
- [backend/app/ml.py](C:\Users\user\Documents\Codex\2026-04-23-can-you-design-ui-ux\backend\app\ml.py)
  provides artifact load/save, evaluation, and inference helpers

Once a model artifact exists, the live surveillance pipeline will use it automatically during `POST /api/pipeline/run-analysis`. If no artifact exists yet, the platform falls back to the rule-based fusion baseline.

Additional training-status endpoints:

- `GET /api/dataset/status`
- `GET /api/dataset/reports`
- `POST /api/dataset/run-auto`
- `GET /api/model/status`
- `GET /api/model/history`
- `POST /api/model/train`

## Project overview

ClinicAI Sentinel is built to detect Lassa fever risk earlier and help clinics respond better.

Core flow:

- Collect epidemiological, weather, symptom, and verified text data
- Clean and structure the incoming signals
- Use NLP to convert unstructured text into risk features
- Use ML to predict low, medium, or high outbreak risk
- Turn the result into alerts and clinic-ready recommendations

## Local run

Frontend:

```powershell
npm.cmd run dev
```

Backend:

```powershell
npm.cmd run dev:backend
```

Frontend URL:

```text
http://localhost:5173
```

Backend URL:

```text
http://127.0.0.1:8000
```

## Deployment readiness

ClinicAI Sentinel now includes container-ready packaging for both the frontend and backend.

Deployment files:

- [backend/Dockerfile](C:\Users\user\Documents\Codex\2026-04-23-can-you-design-ui-ux\backend\Dockerfile)
- [Dockerfile.frontend](C:\Users\user\Documents\Codex\2026-04-23-can-you-design-ui-ux\Dockerfile.frontend)
- [docker-compose.yml](C:\Users\user\Documents\Codex\2026-04-23-can-you-design-ui-ux\docker-compose.yml)
- [render.yaml](C:\Users\user\Documents\Codex\2026-04-23-can-you-design-ui-ux\render.yaml)
- [nginx.conf](C:\Users\user\Documents\Codex\2026-04-23-can-you-design-ui-ux\nginx.conf)
- [.dockerignore](C:\Users\user\Documents\Codex\2026-04-23-can-you-design-ui-ux\.dockerignore)

What this gives you:

- backend served by `uvicorn` inside a Python container
- frontend built with Vite and served by `nginx`
- SPA route fallback for the React dashboard
- persistent Docker volumes for:
  - SQLite database
  - reports
  - notification outboxes
  - model artifacts

### Docker compose run

If Docker Desktop is installed, run:

```powershell
docker compose up --build
```

Frontend:

```text
http://localhost:8080
```

Backend:

```text
http://localhost:8000/api/health
```

### Notes for production

- replace SQLite with PostgreSQL when you move beyond single-node demo deployment
- set real SMTP, SMS, and WhatsApp provider credentials in `.env`
- set a strong production `APP_JWT_SECRET`
- use a real Google OAuth production origin instead of `localhost`
- keep `VITE_API_URL` pointed at your deployed backend URL during frontend image build

## GitHub Actions

The repository now includes CI at:

- [.github/workflows/ci.yml](C:\Users\user\Documents\Codex\2026-04-23-can-you-design-ui-ux\.github\workflows\ci.yml)

What it checks on every push and pull request:

- backend dependency install
- backend Python compile validation
- frontend dependency install
- frontend production build

This gives you a quick health signal directly inside GitHub before you deploy.

## Render deployment hookup

The repository now also includes:

- [render.yaml](C:\Users\user\Documents\Codex\2026-04-23-can-you-design-ui-ux\render.yaml)

That file defines:

- one Python web service for the FastAPI backend
- one static frontend service for the React app

If you use Render:

1. connect your GitHub repository
2. choose `Blueprint` deployment
3. select this repo
4. set the missing secret environment variables in Render

Important production note:

- the current Render file keeps SQLite for easier prototype deployment
- for stronger production reliability, switch `DATABASE_URL` to PostgreSQL before launch

## Environment setup

Create a `.env` file in the project root and copy values from `.env.example`.

Required for real Google login:

```env
VITE_GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
APP_JWT_SECRET=replace-this-with-a-long-random-secret
FRONTEND_ORIGIN=http://localhost:5173
FRONTEND_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
VITE_API_URL=http://127.0.0.1:8000
```

## Google OAuth setup

1. Open Google Cloud Console.
2. Create or select a project.
3. Configure the OAuth consent screen.
4. Create an `OAuth Client ID` for a `Web application`.
5. Add these authorized JavaScript origins:

```text
http://localhost:5173
http://127.0.0.1:5173
```

6. Use the generated client ID for both:
   - `VITE_GOOGLE_CLIENT_ID`
   - `GOOGLE_CLIENT_ID`

This app uses Google Identity Services on the frontend and backend ID-token verification in FastAPI.

## Current development fallback

If Google login is not configured yet, the login screen still includes a `Continue to dashboard demo` button so you can keep building and testing the rest of the app.
