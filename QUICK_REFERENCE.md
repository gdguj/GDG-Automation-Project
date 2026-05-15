# GDSC Scoring System - Quick Reference

## 📊 Scoring Formula

```
TOTAL SCORE = (GPA × 30%) + (Motivation × 40%) + (Eligibility × 30%)
```

---

## 🎯 Component Breakdown

### 1️⃣ GPA Score (30%)
```
Score = (GPA / 5.0) × 100

Examples:
GPA 5.0 → 100 points
GPA 4.5 → 90 points
GPA 4.0 → 80 points
GPA 3.5 → 70 points
```

### 2️⃣ Motivation Quality (40%) - AI Powered 🤖
```
Evaluated by Groq AI on 4 criteria (each worth 25 points):

✓ Clarity & Coherence       (0-25 pts)
✓ Specificity & Detail      (0-25 pts)
✓ Passion & Enthusiasm      (0-25 pts)
✓ Tech/AI/Automation Focus  (0-25 pts)
                            ─────────
                    TOTAL:   0-100 pts
```

### 3️⃣ Eligibility Score (30%)
```
Accepted = 100 points
Rejected = 0 points

(Based on: Technical background OR AI interest OR Automation interest)
```

---

## 💡 Example Calculation

**Applicant: Sara Ahmed**

| Component | Raw Value | Score | Weight | Weighted |
|-----------|-----------|-------|--------|----------|
| GPA | 4.5/5.0 | 90 | 30% | 27.0 |
| Motivation | AI Analysis | 85 | 40% | 34.0 |
| Eligibility | Accepted | 100 | 30% | 30.0 |
| **TOTAL** | | | | **91.0** |

**Rank: #1** 🥇

---

## 📈 Score Interpretation

| Range | Category | Action |
|-------|----------|--------|
| 90-100 | Excellent | Top priority candidates |
| 80-89 | Very Good | Strong candidates |
| 70-79 | Good | Solid candidates |
| 60-69 | Satisfactory | Consider with reservations |
| Below 60 | Weak | Likely reject |

---

## 🔧 What the System Does

1. ✅ Fetches applicant data from Google Sheets
2. ✅ Validates eligibility (Technical/AI/Automation interest)
3. ✅ Scores GPA (normalized to 100)
4. ✅ Analyzes motivation quality using AI
5. ✅ Calculates weighted total scores
6. ✅ Ranks all applicants
7. ✅ Generates detailed CSV with feedback
8. ✅ Provides summary statistics

---

## 📁 Output File Columns

| Column | Description |
|--------|-------------|
| name | Applicant name |
| email | Contact email |
| university | University name |
| gpa | Original GPA (out of 5.0) |
| motivation | Motivation text |
| Eligibility | Accepted/Rejected |
| Reason | Why accepted/rejected |
| **GPA_Score** | 🆕 GPA normalized (0-100) |
| **Motivation_Score** | 🆕 AI quality score (0-100) |
| **Motivation_Feedback** | 🆕 AI feedback text |
| **Eligibility_Score** | 🆕 Bonus points (0/100) |
| **Total_Score** | 🆕 Final weighted score |
| **Rank** | 🆕 Overall ranking |

---

## 🎨 Why This Weight Distribution?

```
40% Motivation  ← Highest (shows genuine interest & fit)
30% Eligibility ← Medium (validates technical relevance)
30% GPA         ← Medium (academic indicator)
```

**Rationale:**
- Motivation is most predictive of success
- GPA alone doesn't guarantee fit
- Eligibility ensures baseline technical alignment

---

## 🚀 Running the System

```bash
# 1. Install dependencies
pip install pandas python-dotenv groq

# 2. Set up API key in .env file
GROQ_API_KEY=your_key_here

# 3. Run the script
python main.py
```

**Output:** `validated_applicants_with_scores.csv`

---

## ⚙️ Customization

Want to adjust weights? Edit these lines in `main.py`:

```python
WEIGHT_GPA = 0.30         # Change to adjust GPA importance
WEIGHT_MOTIVATION = 0.40  # Change to adjust Motivation importance
WEIGHT_ELIGIBILITY = 0.30 # Change to adjust Eligibility importance

# Weights must sum to 1.0
```

---

## 🎯 Key Features

✨ **AI-Powered**: Objective motivation analysis
✨ **Transparent**: Clear scoring criteria
✨ **Balanced**: No single factor dominates
✨ **Actionable**: Provides improvement feedback
✨ **Scalable**: Handles hundreds of applicants
✨ **Free**: Uses free Groq API

---

**Questions?** Check SCORING_GUIDE.md for detailed documentation!
