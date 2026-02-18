# ⚡ SkillBridge AI v4 — Intelligent Career Intelligence Platform

> **Hackathon Project: Intelligent Education — Dynamic Skill-Gap Mapper**
> Full-stack AI web app to bridge the gap between students and their dream jobs.

---

## 🗂️ Project Structure

```
skillbridge_v2/
│
├── backend/
│   ├── app.py              ← Flask API (all endpoints)
│   ├── requirements.txt    ← Python dependencies
│   └── .env.example        ← Environment variables template
│
└── frontend/
    ├── auth.html           ← Login / Register page
    ├── dashboard.html      ← Analytics dashboard
    ├── analyzer.html       ← Resume analysis tool
    ├── result.html         ← Full results display
    └── history.html        ← Scan history
```

---
 
## 🚀 Features

| Feature | Description |
|---|---|
| 🔐 **Auth** | JWT-secured register/login backed by MongoDB |
| 🎯 **ATS Score** | 0-100 score with 5-dimension breakdown |
| 🔍 **Mistake Detector** | Critical, warning & suggestion-level issues |
| ✨ **Improvement Plan** | Add / Remove / Rewrite suggestions |
| 📋 **JD Matcher** | Keyword match % with missing keywords |
| 💼 **Career AI** | Top 5 job recommendations with where to find |
| 🎤 **Interview Prep** | Predicted questions with answering tips |
| 📊 **Dashboard** | ATS trend chart, role distribution, scan history |
| 📄 **PDF Upload** | Extract text from uploaded resume PDFs |

---

## ⚙️ Setup — Step by Step

### Prerequisites
- Python **3.11 or 3.12** (NOT 3.14)
- MongoDB (local or Atlas)
- Gemini API Key (free at aistudio.google.com)

---

### Step 1 — Clone / Extract project

```
skillbridge_v2/
```

---

### Step 2 — Backend Setup

```cmd
cd skillbridge_v2\backend

:: Create virtual environment with Python 3.12
py -3.12 -m venv .venv
.venv\Scripts\activate

:: Install dependencies
pip install -r requirements.txt
```

---

### Step 3 — Create .env file

Copy `.env.example` to `.env` and fill in:

```env
GEMINI_API_KEY=your_gemini_api_key_here
MONGO_URI=mongodb://localhost:27017/skillbridge
JWT_SECRET_KEY=any_long_random_string_here
```

**Get Gemini API key free:** https://aistudio.google.com/app/apikey

**MongoDB options:**
- Local: Install from https://www.mongodb.com/try/download/community
- Cloud: Create free cluster at https://cloud.mongodb.com (use the connection string as MONGO_URI)

---

### Step 4 — Start Backend

```cmd
cd skillbridge_v2\backend
.venv\Scripts\activate
python app.py
```

✅ Should show: `Running on http://0.0.0.0:5000`

Test: Open http://localhost:5000/api/health

---

### Step 5 — Start Frontend

```cmd
cd skillbridge_v2\frontend
python -m http.server 8080
```

Open: **http://localhost:8080/auth.html**

---

## 🌐 API Endpoints

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/api/auth/register` | No | Create account |
| POST | `/api/auth/login` | No | Sign in, get JWT |
| GET | `/api/auth/me` | ✅ JWT | Get profile |
| POST | `/api/extract-pdf` | ✅ JWT | Extract PDF text |
| POST | `/api/analyze` | ✅ JWT | Full AI analysis |
| GET | `/api/dashboard` | ✅ JWT | Analytics data |
| GET | `/api/scans/:id` | ✅ JWT | Get scan result |
| GET | `/api/health` | No | Health check |

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Frontend | HTML5, Tailwind CSS, Vanilla JS, Chart.js |
| Backend | Python 3.12, Flask, Flask-JWT-Extended |
| Database | MongoDB (pymongo) |
| AI | Google Gemini 2.0 Flash (google-genai SDK) |
| PDF | pdfplumber |
| Auth | bcrypt + JWT tokens |
| Fonts | Syne + DM Sans (Google Fonts) |

---

## 🔧 Common Issues

| Error | Fix |
|---|---|
| `TypeError: Metaclasses...` | Use Python 3.12, not 3.14 |
| `Failed to fetch` | Ensure `python app.py` is running |
| `MongoServerError` | Start MongoDB service or use Atlas |
| `401 Unauthorized` | Token expired — log out and log in again |
| `Not Found` on browser | Use `http://localhost:8080/auth.html` (include filename) |
