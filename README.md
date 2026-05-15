# GDG on Campus UJ — AI Evaluation Automation Project

An intelligent applicant screening system built by the GDG on Campus University of Jeddah tech team. This project automates the evaluation of club membership applicants using AI-powered analysis, replacing a manual review process with a consistent, data-driven scoring pipeline.

---

## What It Does

When applicants fill out the GDG registration form, this system automatically:

1. **Fetches applicant data** from Google Sheets
2. **Checks eligibility** based on technical background and interest in AI/automation
3. **Scores each applicant** using a weighted AI evaluation model
4. **Ranks and exports** results to a structured CSV file

---

## Scoring System

Each applicant receives a total score out of 100, calculated as follows:

| Component | Weight | Description |
|-----------|--------|-------------|
| Motivation Quality | 40% | AI analysis of the applicant's motivation statement |
| GPA | 30% | Converted from a 5.0 scale to a 100-point score |
| Eligibility | 30% | Based on technical background or AI/automation interest |

**Formula:**
```
Total Score = (Motivation Score × 0.40) + (GPA Score × 0.30) + (Eligibility Score × 0.30)
```

The motivation statement is evaluated by Groq AI across four dimensions: clarity, specificity, enthusiasm, and relevance to tech/AI/automation.

---

## Project Structure

```
GDG-Automation-Project/
├── main.py               # Main pipeline runner
├── app.py                # Streamlit UI (admin panel)
├── requirements.txt      # Python dependencies
├── .gitignore
├── SCORING_GUIDE.md      # Detailed scoring criteria
├── QUICK_REFERENCE.md    # Quick setup reference
└── assets/               # Images and UI assets
```

---

## Setup & Installation

### 1. Clone the repository

```bash
git clone https://github.com/gdguj/GDG-Automation-Project.git
cd GDG-Automation-Project
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

Or manually:

```bash
pip install pandas python-dotenv groq requests
```

### 3. Configure your API key

Create a `.env` file in the project root with your Groq API key:

```
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxx
```

### 4. Run the pipeline

```bash
python main.py
```

Or launch the admin panel:

```bash
streamlit run app.py
```

---

## Output

The pipeline generates `validated_applicants_with_scores.csv` containing:

| Column | Description |
|--------|-------------|
| `GPA_Score` | GPA converted to a 0–100 score |
| `Motivation_Score` | AI-rated motivation quality (0–100) |
| `Motivation_Feedback` | AI comments on the motivation statement |
| `Eligibility_Score` | 100 if eligible, 0 if not |
| `Total_Score` | Final weighted score (0–100) |
| `Rank` | Applicant ranking (1 = highest score) |

### Example output

```
Sara Ahmed:
  GPA Score:         90.0 / 100  (GPA: 4.5 / 5.0)
  Motivation Score:  85 / 100
  Feedback:          Clear expression of AI interest with specific learning goals
  Eligibility Score: 100 / 100   (Eligible)
  → TOTAL SCORE:     88.5 / 100  |  Rank: #1
```

---

## Tech Stack

- **Python** — core pipeline
- **Groq API** — AI-powered motivation analysis (free tier)
- **Pandas** — data processing
- **Streamlit** — admin UI
- **Google Sheets** — applicant data source

---

## Team

Developed by the GDG on Campus University of Jeddah development team (2025–2026).
