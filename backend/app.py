"""
SkillBridge AI v4 — Full Stack Backend
=======================================
Features:
  - JWT Auth (register/login/logout) with MongoDB
  - Resume upload + PDF text extraction
  - ATS Score generator
  - Mistake detector
  - Job Description matcher
  - AI Career recommendations   
  - Dashboard analytics (per user)
  - All endpoints protected by JWT
"""

import os, json, re, io, datetime
import pdfplumber
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from flask_jwt_extended import (
    JWTManager, create_access_token,
    jwt_required, get_jwt_identity
)
import os, json, re, io, datetime, time
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv
from google import genai
import time

load_dotenv()

# ─────────────────────────────────────────────
#  App Init
# ─────────────────────────────────────────────
app = Flask(__name__)
app.config["JWT_SECRET_KEY"]        = os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-in-prod")
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = datetime.timedelta(hours=24)

CORS(app, resources={r"/api/*": {"origins": "*"}},
     allow_headers=["Content-Type", "Authorization"],
     methods=["GET", "POST", "OPTIONS"])

bcrypt  = Bcrypt(app)
jwt     = JWTManager(app)

# ─────────────────────────────────────────────
#  MongoDB
# ─────────────────────────────────────────────
MONGO_URI = os.getenv("MONGO_URI")
mongo     = MongoClient(MONGO_URI)
db        = mongo["skillbridge"]
users_col = db["users"]
scans_col = db["scans"]

# ─────────────────────────────────────────────
#  Gemini
# ─────────────────────────────────────────────
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY", "YOUR_KEY_HERE"))
MODEL  = "gemini-1.5-flash"

def call_gemini(prompt: str) -> str:
    time.sleep(3)
    response = client.models.generate_content(model=MODEL, contents=prompt)
    return response.text

def extract_json(raw: str) -> dict:
    cleaned = re.sub(r"```(?:json)?", "", raw).strip().strip("`").strip()
    s = cleaned.find("{"); e = cleaned.rfind("}") + 1
    if s == -1 or e == 0:
        raise ValueError("No JSON in response")
    return json.loads(cleaned[s:e])

# ─────────────────────────────────────────────
#  CORS preflight
# ─────────────────────────────────────────────
@app.before_request
def handle_options():
    if request.method == "OPTIONS":
        r = jsonify({"ok": True})
        r.headers.update({
            "Access-Control-Allow-Origin":  "*",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS"
        })
        return r, 200

# ─────────────────────────────────────────────
#  Helper — serialize ObjectId
# ─────────────────────────────────────────────
def serialize(doc):
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc

# ═════════════════════════════════════════════
#  AUTH ROUTES
# ═════════════════════════════════════════════

@app.route("/api/auth/register", methods=["POST"])
def register():
    """POST { name, email, password }"""
    try:
        d = request.get_json(force=True, silent=True) or {}
        name     = d.get("name","").strip()
        email    = d.get("email","").strip().lower()
        password = d.get("password","")

        if not all([name, email, password]):
            return jsonify({"error": "Name, email and password are required."}), 400
        if len(password) < 6:
            return jsonify({"error": "Password must be at least 6 characters."}), 400
        if users_col.find_one({"email": email}):
            return jsonify({"error": "Email already registered."}), 409

        hashed = bcrypt.generate_password_hash(password).decode("utf-8")
        user_id = users_col.insert_one({
            "name":       name,
            "email":      email,
            "password":   hashed,
            "created_at": datetime.datetime.utcnow(),
            "total_scans": 0,
            "avg_ats_score": 0
        }).inserted_id

        token = create_access_token(identity=str(user_id))
        return jsonify({"token": token, "name": name, "email": email}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/auth/login", methods=["POST"])
def login():
    """POST { email, password }"""
    try:
        d = request.get_json(force=True, silent=True) or {}
        email    = d.get("email","").strip().lower()
        password = d.get("password","")

        if not email or not password:
            return jsonify({"error": "Email and password are required."}), 400

        user = users_col.find_one({"email": email})
        if not user or not bcrypt.check_password_hash(user["password"], password):
            return jsonify({"error": "Invalid email or password."}), 401

        token = create_access_token(identity=str(user["_id"]))
        return jsonify({
            "token": token,
            "name":  user["name"],
            "email": user["email"]
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/auth/me", methods=["GET"])
@jwt_required()
def me():
    """GET current user profile"""
    try:
        uid  = get_jwt_identity()
        user = users_col.find_one({"_id": ObjectId(uid)}, {"password": 0})
        return jsonify(serialize(user)), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ═════════════════════════════════════════════
#  PDF EXTRACTION
# ═════════════════════════════════════════════

@app.route("/api/extract-pdf", methods=["POST"])
@jwt_required()
def extract_pdf():
    """POST multipart/form-data { file: PDF }"""
    try:
        if "file" not in request.files:
            return jsonify({"error": "No file uploaded."}), 400
        f = request.files["file"]
        if not f.filename.lower().endswith(".pdf"):
            return jsonify({"error": "Only PDF files supported."}), 400

        raw = f.read()
        if len(raw) > 5 * 1024 * 1024:
            return jsonify({"error": "File too large (max 5 MB)."}), 400

        pages = []
        with pdfplumber.open(io.BytesIO(raw)) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t: pages.append(t.strip())

        text = "\n\n".join(pages).strip()
        if len(text) < 30:
            return jsonify({"error": "Could not extract text — PDF may be image-based."}), 422

        return jsonify({"text": text, "pages": len(pages)}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ═════════════════════════════════════════════
#  CORE ANALYSIS ENGINE
# ═════════════════════════════════════════════

def build_full_analysis_prompt(resume: str, job_role: str, jd: str = "") -> str:
    jd_section = f"\nJob Description:\n{jd}" if jd else ""
    return f"""You are an elite AI career coach, ATS expert, and hiring manager.
Analyze the resume below comprehensively for the target job role.
Return ONLY a single valid JSON object. No markdown. No explanation. No extra text.

Resume:
{resume}

Target Job Role: {job_role}{jd_section}

Return this exact JSON:
{{
  "ats_score": <integer 0-100>,
  "ats_breakdown": {{
    "keyword_match":      <0-100>,
    "format_compatibility": <0-100>,
    "section_completeness": <0-100>,
    "quantified_impact":  <0-100>,
    "readability":        <0-100>
  }},
  "resume_mistakes": [
    {{"type": "critical|warning|suggestion", "issue": "Describe the problem", "fix": "How to fix it"}},
    {{"type": "critical|warning|suggestion", "issue": "...", "fix": "..."}}
  ],
  "improvement_suggestions": {{
    "add_these":    ["concrete item to add", "another item"],
    "remove_these": ["item to remove"],
    "rewrite_these": ["phrase → better version"]
  }},
  "jd_match": {{
    "match_percentage": <0-100>,
    "matched_keywords":  ["kw1", "kw2"],
    "missing_keywords":  ["kw1", "kw2"],
    "gap_summary": "One paragraph summary of the gap"
  }},
  "career_recommendations": [
    {{
      "title": "Job Title",
      "match": <0-100>,
      "reason": "Why this fits",
      "growth": "Career growth path",
      "find_at": ["LinkedIn", "Indeed"],
      "search": "exact search phrase"
    }}
  ],
  "existing_skills":      ["skill1", "skill2"],
  "missing_skills":       ["skill1", "skill2"],
  "interview_questions":  [
    {{"category": "Technical",   "question": "Q?", "tip": "Tip"}},
    {{"category": "Behavioral",  "question": "Q?", "tip": "Tip"}},
    {{"category": "Situational", "question": "Q?", "tip": "Tip"}},
    {{"category": "Technical",   "question": "Q?", "tip": "Tip"}},
    {{"category": "Culture Fit", "question": "Q?", "tip": "Tip"}}
  ],
  "strengths": ["strength 1", "strength 2", "strength 3"],
  "one_line_verdict": "One sentence overall assessment of this resume"
}}"""


@app.route("/api/analyze", methods=["POST"])
@jwt_required()
def analyze():
    """
    POST { resume: str, job_role: str, job_description?: str }
    Returns full AI analysis and saves to MongoDB
    """
    try:
        uid = get_jwt_identity()
        d   = request.get_json(force=True, silent=True) or {}
        resume   = d.get("resume",   "").strip()
        job_role = d.get("job_role", "").strip()
        jd       = d.get("job_description", "").strip()

        if not resume:   return jsonify({"error": "Resume text required."}), 400
        if not job_role: return jsonify({"error": "Job role required."}), 400
        if len(resume) < 50: return jsonify({"error": "Resume too short."}), 400

        raw    = call_gemini(build_full_analysis_prompt(resume, job_role, jd))
        result = extract_json(raw)

        # Clamp scores
        result["ats_score"] = max(0, min(100, int(result.get("ats_score", 0))))
        for k in result.get("ats_breakdown", {}):
            result["ats_breakdown"][k] = max(0, min(100, int(result["ats_breakdown"][k])))
        if "jd_match" in result:
            result["jd_match"]["match_percentage"] = max(0, min(100, int(result["jd_match"].get("match_percentage", 0))))

        # Save scan to MongoDB
        scan_doc = {
            "user_id":   uid,
            "job_role":  job_role,
            "ats_score": result["ats_score"],
            "jd_match":  result.get("jd_match", {}).get("match_percentage", 0),
            "scanned_at": datetime.datetime.utcnow(),
            "result":    result
        }
        scan_id = scans_col.insert_one(scan_doc).inserted_id

        # Update user stats
        user_scans = list(scans_col.find({"user_id": uid}))
        avg_ats = int(sum(s["ats_score"] for s in user_scans) / len(user_scans))
        users_col.update_one(
            {"_id": ObjectId(uid)},
            {"$set": {"total_scans": len(user_scans), "avg_ats_score": avg_ats}}
        )

        result["scan_id"] = str(scan_id)
        return jsonify(result), 200

    except json.JSONDecodeError as e:
        return jsonify({"error": f"AI parse error: {e}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ═════════════════════════════════════════════
#  DASHBOARD ANALYTICS
# ═════════════════════════════════════════════

@app.route("/api/dashboard", methods=["GET"])
@jwt_required()
def dashboard():
    """GET — returns user's scan history and analytics"""
    try:
        uid  = get_jwt_identity()
        user = users_col.find_one({"_id": ObjectId(uid)}, {"password": 0})

        # Last 10 scans
        scans = list(scans_col.find(
            {"user_id": uid},
            {"result": 0}           # exclude heavy result object
        ).sort("scanned_at", -1).limit(10))

        for s in scans:
            s["_id"]        = str(s["_id"])
            s["scanned_at"] = s["scanned_at"].isoformat()

        # ATS score trend (last 7)
        trend = [{"role": s["job_role"], "score": s["ats_score"], "date": s["scanned_at"]} for s in scans[:7]]

        # Role distribution
        roles = {}
        for s in scans:
            roles[s["job_role"]] = roles.get(s["job_role"], 0) + 1

        return jsonify({
            "user":        serialize(user),
            "total_scans": user.get("total_scans", 0),
            "avg_ats":     user.get("avg_ats_score", 0),
            "recent_scans": scans,
            "ats_trend":   trend,
            "role_distribution": [{"role": k, "count": v} for k, v in roles.items()]
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/scans/<scan_id>", methods=["GET"])
@jwt_required()
def get_scan(scan_id):
    """GET a specific scan result"""
    try:
        uid  = get_jwt_identity()
        scan = scans_col.find_one({"_id": ObjectId(scan_id), "user_id": uid})
        if not scan:
            return jsonify({"error": "Scan not found."}), 404
        scan["_id"]        = str(scan["_id"])
        scan["scanned_at"] = scan["scanned_at"].isoformat()
        return jsonify(scan), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ═════════════════════════════════════════════
#  HEALTH
# ═════════════════════════════════════════════

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status":  "ok",
        "service": "SkillBridge AI v4",
        "db":      "MongoDB connected" if mongo else "disconnected"
    }), 200


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
