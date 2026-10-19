---
title: AI-Powered Crime Intelligence Platform
emoji: 🚨
colorFrom: red
colorTo: purple
sdk: docker
pinned: false
---

# AI-Powered Real-Time Crime Intelligence Platform

Full-stack production-ready system combining **React + Tailwind (Vite)**, **FastAPI**, **WebSockets**, **scikit-learn** risk models, **OpenCV** image heuristics, **OpenEnv** RL evaluation hooks, and **OpenAI** for grounded chat and baseline agents.

---

## 🏛️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│              Frontend: React + Vite (Vercel)                 │
│   Leaflet map · WS live alerts · voice · panic · analytics  │
└───────────────────────────┬─────────────────────────────────┘
                            │ REST (HTTPS) + WebSocket (WSS)
┌───────────────────────────▼─────────────────────────────────┐
│         Backend & WebSockets: FastAPI (Container / PaaS)    │
│   routers: auth, analytics, reports, ai, panic, chat,        │
│            notifications, realtime (/ws/live), openenv       │
│   services: predict (RF/KMeans), image (CV), nlp, chat      │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│      Database: Managed PostgreSQL (Supabase / Neon)          │
│   tables: users, otps, reports, officers, cases, suspects,   │
│           evidence, case_links, patrol_logs, beat_risks      │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│          OpenEnv RL Service: Docker / HF Space (:7860)       │
│   Gradio demo + Environment (reset, step, state, baseline)   │
└─────────────────────────────────────────────────────────────┘
```

---

## ✨ Features

- **Real-Time WebSockets**: Persistent `/ws/live?token=<JWT>` broadcasting crime alerts, emergency panic events, and report tracking.
- **AI Crime Risk Prediction**: `POST /predict-crime` & `POST /ai/predict` using RandomForest + KMeans spatial clustering.
- **Computer Vision Analysis**: `POST /ai/analyze-image` with OpenCV heuristics for weapon and vehicle detection.
- **Voice Intelligence**: Web Speech API integration with `POST /ai/nlp/extract` parsing crimes, actors, and locations.
- **Interactive Heatmap**: Leaflet map with intensity heat layers, district bounds, and live blinking alert markers.
- **Emergency Panic System**: One-tap emergency dispatch (`POST /panic/`) with GPS coordinates and optional camera snapshot.
- **Police Command Center**: Specialized views for officer auto-dispatch (Haversine nearest unit), suspect recidivism, serial crime detection, and chain of custody.
- **Dual Authentication**: Role-based access control (`citizen`, `police`, `admin`), bcrypt password hashing, and email OTP verification.

---

## 🚀 Local Development

### 1. Backend Setup

```bash
cd backend

# Create and activate virtual environment
python -m venv .venv

# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- API Base URL: `http://localhost:8000`
- Interactive Swagger UI: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

### 2. Frontend Setup

```bash
cd frontend

# Install Node dependencies
npm install

# Start Vite dev server
npm run dev
```

- Dashboard: `http://localhost:5173`

### 3. Full-Stack via Docker Compose

```bash
cd docker
docker compose up --build
```

---

## 🌐 Production Deployment Architecture

Because the backend relies on **persistent WebSockets (`/ws/live`)**, **in-memory connection hubs (`ConnectionHub`)**, and **native machine learning libraries (`scikit-learn`, `opencv-python-headless`)**, a separated multi-tier deployment ensures high reliability and zero dropped connections:

| Layer | Recommended Host | Why |
| :--- | :--- | :--- |
| **Frontend** | **Vercel** | Ultra-fast global Edge CDN for static Vite SPA assets. |
| **Backend & WebSockets** | **Render / Railway / Fly.io / Hugging Face Spaces** | Persistent container environment allowing long-lived WebSockets, shared in-memory ML model caching, and persistent socket connections. |
| **Database** | **Supabase / Neon / AWS RDS** | Managed cloud PostgreSQL with pooled connection management. |
| **OpenEnv RL** | **Hugging Face Space / Docker** | Standalone Gradio evaluation demo on port 7860. |

---

## 📦 Deployment Step-by-Step

### Step 1: Managed Database (PostgreSQL)

1. Create a free PostgreSQL database on [Supabase](https://supabase.com) or [Neon](https://neon.tech).
2. Copy your connection URI (Connection pooling string).
3. Ensure it uses `postgresql+psycopg://` or `postgresql://`. Example:
   ```
   postgresql+psycopg://postgres:your_password@db.your-host.supabase.co:5432/postgres
   ```
4. The backend will automatically create all tables and run migrations upon initial startup.

---

### Step 2: Backend & WebSocket Deployment (Render / Railway / Fly.io)

#### Deploying on Render:
1. Create a new **Web Service** on Render and link your repository.
2. Configure settings:
   - **Root Directory**: `backend`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port 10000`
3. Add Environment Variables:
   - `DATABASE_URL`: Your production PostgreSQL connection string
   - `JWT_SECRET`: A secure 32+ character random string
   - `FRONTEND_URL`: Your Vercel frontend URL (e.g. `https://your-crime-app.vercel.app`)
   - `CORS_ORIGINS`: `https://your-crime-app.vercel.app`
   - `ALLOW_OPEN_POLICE_REGISTER`: `false`
   - `POLICE_REGISTER_SECRET`: Your police department onboarding code
   - `OPENAI_API_KEY`: *(Optional)* Your OpenAI key for intelligent LLM chat
   - `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `SMTP_FROM`: *(Optional)* for email OTPs
4. Your API and WebSocket endpoint will be live at:
   - REST API: `https://your-backend.onrender.com`
   - WebSocket: `wss://your-backend.onrender.com/ws/live`

---

### Step 3: Frontend Deployment on Vercel

1. Log in to [Vercel](https://vercel.com) and click **Add New Project**.
2. Select your repository.
3. In **Project Settings**:
   - **Framework Preset**: `Vite`
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
4. In **Environment Variables**, add:
   - `VITE_API_URL`: `https://your-backend.onrender.com`
   - `VITE_WS_URL`: `wss://your-backend.onrender.com/ws/live`
5. Click **Deploy**. Vercel will build and deploy your application.

> **Note**: The repository includes `frontend/vercel.json` with SPA route rewrites to ensure direct route navigation (e.g. `/login`, `/police-dashboard`) works seamlessly.

---

### Step 4: OpenEnv Deployment (Hugging Face Spaces)

1. Create a new Space on [Hugging Face](https://huggingface.co/new-space).
2. Choose **Docker** as the SDK.
3. Push the contents of the `openenv/` directory to the Space.
4. Set the `OPENAI_API_KEY` secret in your Space settings.
5. The interactive Gradio triage benchmark will be live on port 7860.

---

## 🔑 Environment Variables Reference

### Backend (`backend/.env`)

| Variable | Required | Default / Example | Purpose |
| :--- | :---: | :--- | :--- |
| `DATABASE_URL` | **Yes** | `postgresql+psycopg://...` | Database connection DSN |
| `JWT_SECRET` | **Yes** | `min-32-chars-random-secret` | JWT signing secret |
| `JWT_EXPIRE_HOURS` | No | `168` | Token expiration time (7 days) |
| `FRONTEND_URL` | **Yes** | `https://your-app.vercel.app` | Production frontend domain for CORS |
| `CORS_ORIGINS` | No | `http://localhost:5173,...` | Comma-separated allowed origins |
| `ALLOW_OPEN_POLICE_REGISTER` | No | `false` | Allow officer signup without passphrase |
| `POLICE_REGISTER_SECRET` | If above false | `police-secure-secret` | Required passkey for police signup |
| `OPENAI_API_KEY` | Optional | `sk-proj-...` | Enables OpenAI grounded assistant |
| `OPENAI_MODEL` | Optional | `gpt-4o-mini` | Model ID for assistant completions |
| `SMTP_*` | Optional | `smtp.gmail.com` | Email delivery for verification OTPs |

### Frontend (`frontend/.env`)

| Variable | Required | Production Example | Purpose |
| :--- | :---: | :--- | :--- |
| `VITE_API_URL` | **Yes** | `https://your-backend.onrender.com` | REST API base URL |
| `VITE_WS_URL` | No | `wss://your-backend.onrender.com/ws/live` | WebSocket stream (auto-derived if omitted) |

---

## 🩺 Health Check & Verification

Once deployed, verify your setup with these simple commands:

1. **Verify Backend REST API**:
   ```bash
   curl -s https://your-backend.onrender.com/health
   # Expected response: {"status":"ok","service":"crime-intelligence-api"}
   ```

2. **Verify ML Prediction**:
   ```bash
   curl -X POST https://your-backend.onrender.com/predict-crime \
     -H "Content-Type: application/json" \
     -d '{"area":"Mumbai","hour":22,"day_of_week":5,"crime_type":"Robbery"}'
   ```

3. **Verify WebSocket Live Stream**:
   Connect via any WebSocket client or browser console:
   ```javascript
   const ws = new WebSocket("wss://your-backend.onrender.com/ws/live");
   ws.onopen = () => console.log("WebSocket connected!");
   ws.onmessage = (e) => console.log("Incoming alert:", JSON.parse(e.data));
   ```

---

## 🛠️ Troubleshooting

- **CORS Error in Browser**:
  Verify that your Vercel frontend URL is present in `FRONTEND_URL` or `CORS_ORIGINS` on the backend without trailing slashes. Wildcards (`*`) cannot be used when credentials/authorization headers are sent.
- **WebSocket Connection Failed**:
  Ensure you are using `wss://` on HTTPS pages (mixed content will be blocked by browsers if you attempt `ws://` from an `https://` Vercel site).
- **Database Stale Connection**:
  Cloud PostgreSQL connections (Supabase, Neon) can be closed by intermediate poolers after idle periods. The codebase includes `pool_pre_ping=True` and `pool_recycle=300` to automatically recover.
- **OTP Not Received**:
  If SMTP credentials are not configured, the development OTP is returned in the API response `dev_otp` field for seamless testing.

---

## 📄 License
MIT License.
