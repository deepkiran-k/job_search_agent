# 🤖 AI Job Search Agent

An AI-powered job search and resume optimization platform. Search real jobs from multiple sources, get ATS compatibility scoring, AI-tailored resumes, and cover letters — all in one flow.

**[Live Demo →](https://jobsearchagent-sfxexdwkkhbostxjp8buvz.streamlit.app)**

![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=flat&logo=streamlit&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.11-blue?style=flat&logo=python)
![Gemini](https://img.shields.io/badge/Google_Gemini-4285F4?style=flat&logo=google&logoColor=white)

---

## ✨ Features

### 🔍 Multi-Source Job Search
- **Adzuna API** — Real-time job listings across 17 countries
- **RapidAPI JSearch** — Google Jobs aggregation
- Concurrent search with deduplication and date sorting
- Filter by title, location, country, and experience level

### 📊 Deterministic ATS Scoring
Resume scoring engine that mirrors real ATS software:

| Dimension | Weight | Rationale |
|---|---|---|
| Keywords (Hard Skills) | 35% | Still the #1 search filter for recruiters. |
| Achievements (Metrics) | 20% | The primary differentiator in 2026 ranking algorithms. |
| Sections & Structure | 15% | Essential for parsing, but less "valuable" once confirmed. |
| Formatting | 15% | High weight because "bad" formatting breaks the parser entirely. |
| Contact & Presence | 10% | LinkedIn/GitHub/Email are the "bare minimum" pass/fail. |
| Length/Density | 5% | Important for humans, but most 2026 ATS handle multi-page well. |

> **Zero API calls** — pure Python string analysis for consistent, reproducible scores.

### ✨ AI-Powered Resume Tailoring
Gemini rewrites your resume guided by ATS scan results using 5 expert strategies:
1. **Skills Gap Analysis** — Identifies gaps and reframes existing experience to fill them
2. **Tailored Bullet Points** — Action verbs, quantified impact, 4-6 bullets per role
3. **ATS Compatibility** — Keywords in context, standard formatting, employment gap handling
4. **Compelling Summary** — Unique value proposition with forward-looking statement
5. **Keyword Integration** — Natural keyword placement + relevant certification suggestions

### ✍️ Cover Letter Generation
AI-generated cover letters tailored to the specific job and your resume.

### 📄 Resume File Support
- Upload **PDF**, **DOCX**, or **TXT** resumes
- Deep file analysis: page count, font detection, image detection, table warnings
- Handles complex PDF structures (IndirectObject resolution)

### ⬇️ PDF Export
Download your tailored resume as a clean, ATS-friendly PDF with:
- Blue section headers with underlines
- Clean typography (Helvetica)
- Unicode sanitization for maximum compatibility

---

## 🏗️ Architecture

```
app.py                          # Streamlit UI — 3-step pipeline
├── config/
│   └── settings.py             # API keys, Gemini LLM configuration
├── tools/
│   ├── gemini_resume_builder.py  # AI resume tailoring (5-strategy prompt)
│   └── gemini_tools.py           # AI cover letter generation
└── utils/
    ├── ats_scanner.py           # Deterministic ATS scoring engine
    ├── gemini_ats.py            # Hybrid ATS: deterministic + Gemini qualitative
    ├── resume_parser.py         # PDF/DOCX text extraction + file analysis
    ├── pdf_generator.py         # Markdown → PDF converter (fpdf2)
    ├── adzuna_client.py         # Adzuna job search API client
    ├── rapidapi_client.py       # RapidAPI JSearch client
    └── helpers.py               # Utility functions
```

### Flow
```
Search Jobs (Adzuna + RapidAPI)
        ↓
  Select a Job
        ↓
Upload/Paste Resume
        ↓
┌─────────────────────────────────────────────┐
│  ATS Scan (deterministic, zero API calls)   │
│  → keyword, section, formatting, etc.       │
└──────────────────┬──────────────────────────┘
                   ↓
┌─────────────────────────────────────────────┐
│  Gemini Analysis (qualitative suggestions)  │
│  Cover Letter · Resume Tailoring            │
└──────────────────┬──────────────────────────┘
                   ↓
  Re-score tailored resume (deterministic)
        ↓
  Download PDF / Markdown
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- API keys (all have free tiers):
  - [Google Gemini API](https://aistudio.google.com/apikey)
  - [Adzuna API](https://developer.adzuna.com/)
  - [RapidAPI JSearch](https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch)

### Installation

```bash
# Clone the repository
git clone https://github.com/deepkiran-k/job_search_agent.git
cd job_search_agent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Create a `.env` file in the project root:

```env
# Google Gemini API
GOOGLE_API_KEY=your_gemini_api_key

# Adzuna Job Search API
ADZUNA_APP_ID=your_adzuna_app_id
ADZUNA_APP_KEY=your_adzuna_app_key

# RapidAPI - JSearch (Google Jobs)
RAPIDAPI_KEY=your_rapidapi_key
```

### Run

```bash
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## ☁️ Deploy to Streamlit Cloud

1. Push your code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your repo, set `app.py` as the main file
4. Add your API keys as **Secrets** in the Streamlit Cloud dashboard:
   ```toml
   GOOGLE_API_KEY = "your_key"
   ADZUNA_APP_ID = "your_id"
   ADZUNA_APP_KEY = "your_key"
   RAPIDAPI_KEY = "your_key"
   ```

---

## 🛠️ Tech Stack

| Component | Technology |
|---|---|
| **Frontend** | Streamlit with custom CSS (dark theme) |
| **AI/LLM** | Google Gemini 2.5 Flash Lite via LangChain |
| **ATS Engine** | Pure Python (regex, Counter — zero dependencies) |
| **PDF Generation** | fpdf2 (pure Python, no system deps) |
| **Document Parsing** | PyPDF2, python-docx |
| **Job APIs** | Adzuna REST API, RapidAPI JSearch |
| **Deployment** | Streamlit Community Cloud |

---

## 📝 License

This project is for educational and personal use.

---

Built with ❤️ by [Deepkiran Kaur](https://github.com/deepkiran-k)
