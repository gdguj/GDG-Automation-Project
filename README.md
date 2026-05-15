# GDGoC Applicant Evaluation System

An AI-powered applicant screening tool built by the GDG on Campus University of Jeddah tech team. This system automates the evaluation and ranking of club membership applicants using configurable scoring criteria and AI analysis — replacing manual review with a consistent, data-driven pipeline.

---

## How It Works

The system processes applicant data from a Google Sheet or uploaded Excel/CSV file through three stages:

1. **Eligibility Check** — AI reads each applicant's motivation text and checks it against custom criteria defined by the organizer (e.g. "technical background", "AI interest"). Each applicant is marked Accepted or Rejected.

2. **Column Scoring** — The organizer selects which columns to score (e.g. motivation statement, project experience) and assigns a weight to each. The AI scores every selected field from 0–100 based on clarity, specificity, passion, and relevance to the event.

3. **Final Ranking** — A weighted total score is calculated for each applicant and they are ranked from highest to lowest.

---

## Scoring System

Eligibility is always fixed at **30%** of the total score. The remaining **70%** is distributed across the columns the organizer selects, with custom weights that must sum to 100%.

| Component | Weight |
|-----------|--------|
| Eligibility (Accepted = 100, Rejected = 0) | Fixed at 30% |
| Organizer-selected columns (AI-scored 0–100) | 70% total, split by custom weights |

**Formula:**
```
Total Score = (Column Scores × their weights × 0.70) + (Eligibility Score × 0.30)
```

---

## Project Structure

```
GDG-Automation-Project/
├── main.py               # Core pipeline: data loading, eligibility, scoring
├── app.py                # Streamlit admin UI
├── requirements.txt      # Python dependencies
├── .gitignore
├── SCORING_GUIDE.md      # Detailed scoring criteria reference
├── QUICK_REFERENCE.md    # Quick setup cheat sheet
└── assets/               # UI images and logos
```

---

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/gdguj/GDG-Automation-Project.git
cd GDG-Automation-Project
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Add your API key

Create a `.env` file in the project root:

```
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxx
```

### 4. Run

**Terminal mode (interactive):**
```bash
python main.py
```

**Streamlit admin panel:**
```bash
streamlit run app.py
```

---

## Using the Admin Panel

1. Enter the event name
2. Load data via Google Sheet URL or upload an Excel/CSV file
3. Select which column contains the motivation/eligibility text
4. Choose which columns the AI should score
5. Set weights for each scoring column (must total 100%)
6. Enter eligibility criteria (one per line)
7. Click **Run Evaluation**

Results are displayed in a ranked table and can be downloaded as a CSV.

---

## Output

The pipeline produces a results CSV with:

| Column | Description |
|--------|-------------|
| `[Column]_Score` | AI score for each selected column (0–100) |
| `[Column]_Feedback` | AI feedback for each scored column |
| `Eligibility` | Accepted or Rejected |
| `Eligibility_Score` | 100 if Accepted, 0 if Rejected |
| `Total_Score` | Final weighted score (0–100) |
| `Rank` | Applicant ranking (1 = best) |

---

## Tech Stack

- **Python** — core pipeline
- **Groq API (LLaMA 3.1)** — AI scoring and eligibility analysis
- **Pandas** — data processing
- **Streamlit** — admin UI
- **Google Sheets / Excel / CSV** — applicant data sources

---

## Team

Developed by the GDG on Campus University of Jeddah development team — 2025/2026.
