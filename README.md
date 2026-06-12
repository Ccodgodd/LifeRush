<div align="center">

# 🩸 LifeRush AI

**An AI-Powered Emergency Blood Donation Platform**

*Connecting donors to patients in critical moments — fast, smart, and reliably.*

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/Frontend-React%2018-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://reactjs.org/)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org/)
[![Vite](https://img.shields.io/badge/Build-Vite-646CFF?style=for-the-badge&logo=vite&logoColor=white)](https://vitejs.dev/)
[![TailwindCSS](https://img.shields.io/badge/Styles-Tailwind%20CSS-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white)](https://tailwindcss.com/)
[![Deploy on Render](https://img.shields.io/badge/Backend-Render-46E3B7?style=for-the-badge&logo=render&logoColor=black)](https://render.com/)
[![Deploy on Vercel](https://img.shields.io/badge/Frontend-Vercel-000000?style=for-the-badge&logo=vercel&logoColor=white)](https://vercel.com/)

</div>

---

## 📖 Overview

**LifeRush AI** is a full-stack web application that bridges the gap between blood donors and patients in urgent need. Using AI-powered donor matching, OCR-based medical report analysis, an intelligent chatbot, and toll-free telephony integration, LifeRush ensures that the right donor reaches the right patient — at the right time.

Whether a request is raised through the web interface or a phone call, the system automatically identifies compatible, nearby donors, ranks them using a multi-factor AI scoring engine, and dispatches real-time notifications.

---

## ✨ Features

### 🤖 AI-Powered Donor Matching
- Multi-factor scoring engine that ranks donors by **blood compatibility**, **proximity** (Haversine distance), **last donation date**, and **medical eligibility**.
- Full blood group compatibility matrix (e.g., O- as universal donor).
- Geocoded location lookup using Nominatim / OpenStreetMap.

### 🔬 OCR Medical Report Analysis
- Upload blood test reports (image/PDF); the system extracts key health metrics automatically:
  - Blood group, Hemoglobin, Platelets, WBC count.
- Automatically determines **donor eligibility** and calculates the **next eligible donation date**.
- Supports EasyOCR, Tesseract, and a regex-based rule fallback.

### 💬 AI Chatbot
- Answers blood donation FAQs with a curated offline knowledge base.
- Falls back to OpenAI GPT for complex or unknown queries.
- Topics covered: eligibility, donation frequency, diet tips, nearby centers, safety, and more.

### 📞 Telephony / IVR Integration
- Toll-free number support via **Twilio**.
- DTMF-based IVR menu for callers to select blood group and register requests without internet access.
- Automatically triggers the AI matching pipeline from phone calls.

### 🗺️ Nearby Blood Banks Map
- Interactive map powered by **OpenStreetMap / Nominatim**.
- Locates hospitals, blood banks, and donation camps near the user's city.
- Displays real locations with labels and distances.

### 👥 Role-Based Access Control
- Three roles: **Donor**, **Patient**, **Admin**.
- JWT-based authentication with bcrypt password hashing.
- Role-specific dashboards and API access.

### 📊 Dashboards
- **Donor Dashboard**: View matches, blood requests, donation history, notifications, nearby map, and chatbot.
- **Landing Page**: Quick eligibility check via medical report upload + blood request form.

### 🔔 Real-Time Notifications
- In-app notification system for matched donors, request updates, and system alerts.
- Supports `emergency`, `reminder`, and `system` notification types.

---

## 🏗️ Architecture

```
liferush-ai/
├── backend/
│   └── app/
│       ├── main.py          # FastAPI app, all route definitions
│       ├── models.py        # SQLAlchemy ORM models
│       ├── schemas.py       # Pydantic request/response schemas
│       ├── auth.py          # JWT auth, password hashing
│       ├── ai_engine.py     # Donor ranking, compatibility, distance scoring
│       ├── ocr.py           # Medical report parsing (EasyOCR / Tesseract / regex)
│       ├── chatbot.py       # FAQ engine + OpenAI GPT fallback
│       ├── telephony.py     # Twilio IVR / toll-free call handler
│       ├── database.py      # SQLAlchemy engine & session setup
│       └── config.py        # Pydantic settings from .env
├── frontend/
│   └── src/
│       ├── App.jsx          # Root component + routing logic
│       ├── api.js           # Axios base URL config
│       ├── index.css        # Global styles
│       └── pages/
│           ├── LandingPage.jsx      # Public landing, request form, report upload
│           └── DonorDashboard.jsx   # Authenticated donor/patient/admin dashboard
├── .env.example             # Environment variable template
├── render.yaml              # Render deployment config
├── requirements.txt         # Root Python dependencies
└── DEPLOY.md                # Full deployment guide
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | React 18, Vite, Tailwind CSS, Lucide Icons, Chart.js |
| **Backend** | Python, FastAPI, SQLAlchemy, Pydantic |
| **Database** | SQLite (development) / PostgreSQL (production) |
| **Auth** | JWT (python-jose), bcrypt (passlib) |
| **OCR** | EasyOCR, Pytesseract, regex fallback |
| **AI/ML** | NumPy, Pandas, Haversine distance scoring |
| **Chatbot** | OpenAI GPT API + offline FAQ engine |
| **Telephony** | Twilio (IVR / toll-free calls) |
| **Maps** | OpenStreetMap / Nominatim, Google Maps API (optional) |
| **Email** | SendGrid |
| **Deployment** | Render (backend) + Vercel (frontend) |

---

## 🚀 Getting Started

### Prerequisites

- **Python** 3.10+
- **Node.js** 18+ and **npm**
- (Optional for OCR) Tesseract installed and in PATH

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/liferush-ai.git
cd liferush-ai
```

### 2. Backend Setup

```bash
# Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -r backend/requirements.txt

# Copy and configure environment variables
copy .env.example .env
# Edit .env and fill in your API keys
```

### 3. Frontend Setup

```bash
cd frontend
npm install
```

### 4. Configure Environment Variables

Edit the `.env` file in the project root:

```env
JWT_SECRET_KEY=your-strong-secret-key
DATABASE_URL=sqlite:///./lifrush.db

# CORS — set to your frontend origin
BACKEND_CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

# Optional integrations
GOOGLE_MAPS_API_KEY=YOUR_KEY
OPENAI_API_KEY=YOUR_KEY
SENDGRID_API_KEY=YOUR_KEY
TWILIO_ACCOUNT_SID=YOUR_SID
TWILIO_AUTH_TOKEN=YOUR_TOKEN
TWILIO_PHONE_NUMBER=+1234567890
```

For the frontend, create `frontend/.env`:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

### 5. Run the Application

**Start the backend** (from project root):
```bash
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

**Start the frontend** (in a separate terminal):
```bash
cd frontend
npm run dev
```

Open your browser at **http://localhost:5173**

The interactive API docs are available at **http://localhost:8000/docs**

---

## 🌐 Deployment

LifeRush AI is configured for one-click deployment:

| Service | Target |
|---|---|
| **Backend** | [Render](https://render.com/) (Web Service) |
| **Frontend** | [Vercel](https://vercel.com/) |
| **Database** | Render PostgreSQL |

See [DEPLOY.md](./DEPLOY.md) for the full step-by-step deployment guide.

---

## 📡 API Overview

The FastAPI backend exposes a RESTful API under `/api/v1`. Key endpoint groups:

| Endpoint Group | Description |
|---|---|
| `POST /api/v1/register` | Register a new user (donor / patient) |
| `POST /api/v1/token` | Login and get a JWT access token |
| `GET /api/v1/users/me` | Get current authenticated user profile |
| `POST /api/v1/blood-requests` | Create an emergency blood request |
| `GET /api/v1/blood-requests` | List all active blood requests |
| `POST /api/v1/medical-reports/upload` | Upload a medical report for OCR analysis |
| `GET /api/v1/matches/me` | Get donor's current matches |
| `POST /api/v1/matches/{id}/respond` | Accept or decline a match |
| `GET /api/v1/notifications` | Get all user notifications |
| `POST /api/v1/chatbot` | Query the AI chatbot |
| `POST /api/v1/telephony/call` | Simulate a toll-free blood request call |
| `GET /api/v1/nearby-places` | Find nearby hospitals / blood banks |

Full interactive documentation: `http://localhost:8000/docs`

---

## 🔐 Environment Variables Reference

| Variable | Description | Required |
|---|---|---|
| `JWT_SECRET_KEY` | Secret key for signing JWT tokens | ✅ |
| `DATABASE_URL` | SQLAlchemy database connection string | ✅ |
| `BACKEND_CORS_ORIGINS` | Comma-separated list of allowed origins | ✅ |
| `OPENAI_API_KEY` | OpenAI API key for chatbot GPT fallback | Optional |
| `GOOGLE_MAPS_API_KEY` | Google Maps API key for hospital search | Optional |
| `SENDGRID_API_KEY` | SendGrid key for email notifications | Optional |
| `TWILIO_ACCOUNT_SID` | Twilio Account SID for telephony | Optional |
| `TWILIO_AUTH_TOKEN` | Twilio Auth Token | Optional |
| `TWILIO_PHONE_NUMBER` | Twilio phone number for outbound calls | Optional |
| `VITE_API_BASE_URL` | Backend base URL for the frontend | ✅ (frontend) |

---

## 🩺 Blood Group Compatibility Reference

| Donor | Can Donate To |
|---|---|
| **O−** | O−, O+, A−, A+, B−, B+, AB−, AB+ |
| **O+** | O+, A+, B+, AB+ |
| **A−** | A−, A+, AB−, AB+ |
| **A+** | A+, AB+ |
| **B−** | B−, B+, AB−, AB+ |
| **B+** | B+, AB+ |
| **AB−** | AB−, AB+ |
| **AB+** | AB+ |

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. **Fork** the repository.
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. **Commit** your changes with clear messages.
4. Push to your fork and open a **Pull Request**.

Please ensure your code follows the existing patterns and that new API endpoints are documented in the FastAPI schema.

---

## 📄 License

This project is licensed under the **MIT License**. See the [LICENSE](./LICENSE) file for details.

---

<div align="center">

Made with ❤️ to save lives.

**Every donation counts. Every second matters.**

</div>
