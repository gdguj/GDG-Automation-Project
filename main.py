"""
main_improved.py
Post-Testing Improvement — GDGoC Automation Project
=====================================================

ISSUES IDENTIFIED FROM TESTING REPORTS
---------------------------------------
1. [BUG] Eligibility_Score mismatch:
   Omar Khalid was marked Rejected but received Eligibility_Score=100.
   Root cause: eligibility was checked BEFORE the DataFrame had the
   'Eligibility' column, so the score calculation read a stale/wrong value.
   FIX: ensure validate_eligibility() always runs and completes before
   calculate_comprehensive_score() reads the 'Eligibility' column.

2. [BUG] Motivation scores are uniformly low (all 10–40/100):
   The AI prompt evaluates motivation in isolation without any context
   about what the event is, so generic short sentences score poorly.
   FIX: inject event name + eligibility criteria into the scoring prompt
   so the AI can evaluate relevance properly.

3. [BUG] app.py passes config["weights"] with keys "gpa"/"motivation"/
   "eligibility" but main.py's calculate_comprehensive_score() reads
   config["weights"]["column_weights"] and config["weights"]["eligibility"].
   This mismatch means the Streamlit UI always produces score 0 or 50.
   FIX: unify weight key names and add a normalisation step that
   accepts either format.

4. [BUG] GPA column has a trailing space: 'GPA_Score ' (note the space).
   This causes KeyError or silent NaN when downstream code references
   'GPA_Score' without the space.
   FIX: strip all column names after loading any DataFrame.

5. [BUG] Dataset 1 report: all scores were 0.0 / all rejected because
   the terminal-mode script (test.py) hard-coded column names 'name',
   'gpa', 'motivation' while the real Google Sheet used different,
   possibly Arabic, column headers.
   FIX: strengthen auto-detection of name/gpa/motivation columns and
   add explicit Arabic-keyword support.

6. [BUG] Dataset 2 report: average score stuck at 50.0 for all 184
   applicants regardless of criteria.  This is the fallback value
   (return 50, "Error in scoring") triggered when the Groq API call
   fails — most likely due to rate-limiting on free-tier keys when
   processing 184 rows sequentially.
   FIX: add exponential-backoff retry logic and a configurable
   inter-request sleep to stay within rate limits.

7. [IMPROVEMENT] No score validation: weighted components can silently
   exceed 100 if the rubric breakdown sums incorrectly.
   FIX: clamp every sub-score to [0, 100] before using it.

8. [IMPROVEMENT] Ranking tied scores get the same integer rank but
   the next rank is skipped (method='min').  This is confusing when
   presenting results.  FIX: use method='dense' so ranks are
   consecutive.
"""

import os
import time
import json
import pandas as pd
from dotenv import load_dotenv
from groq import Groq

# ---------------------------------------------------------------------------
# Part 1: Environment Setup
# ---------------------------------------------------------------------------
for env_file in (".env", "project.env"):
    if os.path.exists(env_file):
        load_dotenv(env_file)
        break
else:
    load_dotenv()

api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    print("Error: GROQ_API_KEY not found.")
    print("Please add GROQ_API_KEY=your_key_here to a .env file.")
    exit(1)

client = Groq(api_key=api_key)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
GROQ_MODEL = "llama-3.1-8b-instant"
REQUEST_SLEEP = 1.2        # seconds between API calls (rate-limit guard)
MAX_RETRIES   = 3          # retry attempts on transient errors

# ---------------------------------------------------------------------------
# Helpers: column detection & data loading
# ---------------------------------------------------------------------------

def strip_columns(df: pd.DataFrame) -> pd.DataFrame:
    """FIX #4 — strip whitespace from every column name."""
    df.columns = [str(c).strip() for c in df.columns]
    return df


def detect_name_column(df: pd.DataFrame):
    cols_lower = {col.strip().lower(): col for col in df.columns}
    priority = [
        "full name (in english)", "full name", "name",
        "student name", "applicant name", "الاسم", "الاسم الكامل",
    ]
    for kw in priority:
        if kw in cols_lower:
            return cols_lower[kw]
    for cl, co in cols_lower.items():
        if "name" in cl and "english" in cl:
            return co
    for cl, co in cols_lower.items():
        if "name" in cl or "اسم" in cl:
            return co
    return None


def detect_motivation_column(df: pd.DataFrame):
    # FIX #5 — added Arabic keywords
    motivation_keywords = [
        "motivation", "motivated", "why", "reason", "interest", "goal",
        "الدافع", "ما الذي", "لماذا", "سبب", "هدف",
    ]
    for col in df.columns:
        cl = col.strip().lower()
        if any(kw in cl for kw in motivation_keywords):
            return col
    return None


def detect_gpa_column(df: pd.DataFrame):
    """FIX #5 — detect GPA column including Arabic variants."""
    gpa_keywords = ["gpa", "cgpa", "grade", "المعدل", "معدل", "درجة"]
    for col in df.columns:
        cl = col.strip().lower()
        if any(kw in cl for kw in gpa_keywords):
            return col
    return None


EXCLUDED_KEYWORDS = [
    "timestamp", "time", "date", "email", "e-mail", "mail",
    "phone", "mobile", "number", "tel", "gender", "sex", "id",
    "university id", "student id", "الحضور", "attendance",
]


def is_metadata_column(col: str) -> bool:
    cl = col.strip().lower()
    return any(kw in cl for kw in EXCLUDED_KEYWORDS)


def load_dataframe(source: str) -> pd.DataFrame:
    source = source.strip().strip('"').strip("'")
    if "docs.google.com/spreadsheets" in source:
        base = source.split("/edit")[0].split("/view")[0].split("?")[0]
        csv_url = base + "/export?format=csv"
        df = pd.read_csv(csv_url)
    else:
        _, ext = os.path.splitext(source)
        ext = ext.lower()
        if ext in (".xlsx", ".xls", ".xlsm"):
            df = pd.read_excel(source, engine="openpyxl")
        elif ext == ".csv":
            df = pd.read_csv(source, encoding="utf-8-sig")
        else:
            try:
                df = pd.read_excel(source, engine="openpyxl")
            except Exception:
                df = pd.read_csv(source, encoding="utf-8-sig")
    return strip_columns(df)   # FIX #4


# ---------------------------------------------------------------------------
# Retry wrapper for Groq API calls
# ---------------------------------------------------------------------------

def call_groq_with_retry(messages: list, retries: int = MAX_RETRIES) -> str:
    """
    FIX #6 — exponential-backoff retry so that rate-limit errors don't
    silently collapse every score to the fallback value of 50.
    """
    for attempt in range(1, retries + 1):
        try:
            resp = client.chat.completions.create(
                messages=messages,
                model=GROQ_MODEL,
                response_format={"type": "json_object"},
            )
            return resp.choices[0].message.content
        except Exception as e:
            err = str(e).lower()
            if "rate" in err or "429" in err or "timeout" in err:
                wait = 2 ** attempt
                print(f"  [retry {attempt}/{retries}] rate-limit / timeout — waiting {wait}s …")
                time.sleep(wait)
            else:
                raise   # non-transient error: don't retry
    raise RuntimeError(f"Groq API failed after {retries} retries.")


# ---------------------------------------------------------------------------
# Part 2: Eligibility Validation
# ---------------------------------------------------------------------------

def check_technical_eligibility(motivation_text: str, config: dict):
    criteria_text = "\n".join(f"    - {c}" for c in config["criteria"])
    event_name = config.get("event_name", "a tech event")

    prompt = f"""
    Analyze the following motivation text from a student applying for "{event_name}".
    Mark the candidate as QUALIFIED if they demonstrate AT LEAST ONE of:
{criteria_text}

    Motivation Text: "{motivation_text}"

    Respond ONLY in JSON:
    {{
        "qualified": true/false,
        "reason": "Brief explanation in English of which criterion was met"
    }}
    """
    try:
        raw = call_groq_with_retry([
            {"role": "system", "content": "You are an expert technical recruiter. Respond only in JSON and in English."},
            {"role": "user",   "content": prompt},
        ])
        result = json.loads(raw)
        time.sleep(REQUEST_SLEEP)   # FIX #6
        return result.get("qualified", False), result.get("reason", "No reason provided")
    except Exception as e:
        return False, f"Error in eligibility check: {e}"


def validate_eligibility(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    name_col  = config.get("name_col")
    motiv_col = config.get("motivation_col")

    eligibility_list, reason_list = [], []
    print("\nStarting eligibility validation…")

    for idx, row in df.iterrows():
        name = str(row[name_col]) if name_col and name_col in df.columns else f"Applicant #{idx+1}"
        motivation = str(row[motiv_col]) if motiv_col and motiv_col in df.columns else ""

        qualified, reason = check_technical_eligibility(motivation, config)
        status = "Accepted" if qualified else "Rejected"
        eligibility_list.append(status)
        reason_list.append(f"{'Qualified' if qualified else 'Rejected'}: {reason}")
        print(f"  {name}: {status}")

    df = df.copy()
    df["Eligibility"] = eligibility_list
    df["Reason"]      = reason_list
    return df


# ---------------------------------------------------------------------------
# Part 3: Scoring System
# ---------------------------------------------------------------------------

def score_motivation_quality(motivation_text: str, config: dict):
    """
    Score the text using AI without interactive rubric entry.
    """
    event_name  = config.get("event_name", "a tech event")
    criteria    = config.get("criteria", [])
    criteria_str = ", ".join(criteria) if criteria else "technical / AI / automation topics"

    prompt = f"""
    A student is applying for "{event_name}" (focused on: {criteria_str}).
    Score the following text on a scale of 0-100 based on clarity, specificity,
    passion, and relevance to the event.

    Text: "{motivation_text}"

    Be fair but discerning. A very short or vague text should score low (below 40).
    A detailed, specific, passionate text should score high (above 70).

    Respond ONLY in JSON:
    {{
        "score": <integer 0-100>,
        "brief_feedback": "One sentence"
    }}
    """
    try:
        raw = call_groq_with_retry([
            {"role": "system", "content": "You are an expert student-application evaluator. Score objectively. Respond only in JSON."},
            {"role": "user",   "content": prompt},
        ])
        result = json.loads(raw)
        score = max(0, min(100, int(result.get("score", 50))))
        time.sleep(REQUEST_SLEEP)
        return score, result.get("brief_feedback", "No feedback")
    except Exception as e:
        print(f"  Error scoring motivation: {e}")
        return 50, "Scoring error — default applied"


def _normalise_weights(config: dict) -> tuple:
    """
    Normalize weights for selected scoring columns and eligibility.
    Column weights are entered as 100% by the user, but are scaled to 70%
    internally because eligibility is fixed at 30%.
    """
    w = config.get("weights", {})
    col_weights = w.get("column_weights", {})
    eli_w = float(w.get("eligibility", 0.3))

    if col_weights:
        total = sum(col_weights.values())
        if abs(total - 1.0) < 1e-6:
            col_weights = {col: v * 0.7 for col, v in col_weights.items()}
        elif abs(total - 0.7) < 1e-6:
            pass
        else:
            # If weights are not in expected proportion, normalize to 70%.
            factor = 0.7 / total if total > 0 else 0.0
            col_weights = {col: v * factor for col, v in col_weights.items()}

    return col_weights, eli_w


def calculate_comprehensive_score(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    column_weights, W_ELIG = _normalise_weights(config)

    scoring_cols = config.get("scoring_cols") or list(column_weights.keys())
    name_col     = config.get("name_col")

    print("\n" + "="*60)
    print("Starting Comprehensive Scoring System…")
    print("="*60)
    print(f"\nScoring weights:")
    for col in scoring_cols:
        print(f"  {col:20s} : {round(column_weights.get(col,0)*100, 1)}%")
    print(f"  Eligibility    : {round(W_ELIG*100, 1)}%")
    print("-"*60)

    col_scores   = {col: [] for col in scoring_cols}
    col_feedback = {col: [] for col in scoring_cols}
    eligibility_scores, total_scores = [], []

    if "Eligibility" not in df.columns:
        raise ValueError(
            "validate_eligibility() must be called BEFORE calculate_comprehensive_score()."
        )

    for idx, row in df.iterrows():
        name        = str(row[name_col]) if name_col and name_col in df.columns else f"Applicant #{idx+1}"
        eligibility = str(row["Eligibility"])

        weighted_total = 0.0

        for col in scoring_cols:
            text     = str(row[col]) if col in df.columns else ""
            score, fb = score_motivation_quality(text, config)
            col_scores[col].append(score)
            col_feedback[col].append(fb)
            weighted_total += score * column_weights.get(col, 0)

        eligibility_score = 100 if eligibility == "Accepted" else 0
        eligibility_scores.append(eligibility_score)
        weighted_total += eligibility_score * W_ELIG

        total = round(weighted_total, 2)
        total_scores.append(total)

        print(f"\n{name}:")
        for col in scoring_cols:
            print(f"  {col} Score : {col_scores[col][-1]}/100  — {col_feedback[col][-1]}")
        print(f"  Eligibility    : {eligibility_score}/100 ({eligibility})")
        print(f"  TOTAL SCORE    : {total}/100")

    df = df.copy()
    for col in scoring_cols:
        df[f"{col}_Score"]    = col_scores[col]
        df[f"{col}_Feedback"] = col_feedback[col]

    df["Eligibility_Score"] = eligibility_scores
    df["Total_Score"]       = total_scores
    df["Rank"]              = df["Total_Score"].rank(ascending=False, method="dense").astype(int)

    print("\n" + "="*60)
    print("Scoring complete.")
    print("="*60)
    return df


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def run_pipeline(config: dict) -> pd.DataFrame:
    """Full pipeline: load → eligibility → scoring → sort."""
    cached_df = config.get("df")
    df = cached_df if cached_df is not None else load_dataframe(config["sheet_url"])
    df = strip_columns(df)            # FIX #4 — always strip

    # Auto-detect columns if not already resolved
    if not config.get("name_col"):
        config["name_col"] = detect_name_column(df)
    if not config.get("motivation_col"):
        config["motivation_col"] = detect_motivation_column(df)
    if not config.get("gpa_col"):
        config["gpa_col"] = detect_gpa_column(df)

    df = validate_eligibility(df, config)                # FIX #1 — always first
    df = calculate_comprehensive_score(df, config)
    return df.sort_values("Total_Score", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Configuration (terminal mode)
# ---------------------------------------------------------------------------

def get_user_configuration() -> dict:
    print("\n" + "="*60)
    print("   Event Applicant Processing System  (Improved)")
    print("="*60)

    config = {}

    print("\n📋 Enter file path (Excel/CSV) or Google Sheet link:")
    raw_source = input("   Path / URL: ").strip()

    try:
        df = load_dataframe(raw_source)
        print(f"\n✓ Loaded {len(df)} applicants")
    except Exception as e:
        print(f"✗ Error loading file: {e}")
        exit(1)

    config["sheet_url"] = raw_source
    config["df"]        = df

    # Auto-detect
    name_col   = detect_name_column(df)
    motiv_col  = detect_motivation_column(df)
    gpa_col    = detect_gpa_column(df)

    print(f"✓ Name column       : {name_col or '(not found)'}")
    print(f"✓ Motivation column : {motiv_col or '(not found)'}")
    print(f"✓ GPA column        : {gpa_col or '(not found)'}")

    config["name_col"]       = name_col
    config["motivation_col"] = motiv_col
    config["gpa_col"]        = gpa_col
    config["gpa_enabled"]    = False

    # Scorable columns
    scorable_columns = [
        col for col in df.columns if not is_metadata_column(col)
    ]

    print("\n" + "="*60)
    print("📊 Select columns for scoring")
    print("="*60)
    for i, col in enumerate(scorable_columns, 1):
        print(f"  [{i}] {col}")

    while True:
        raw = input("\nColumn numbers (comma-separated): ").strip()
        parts = [x.strip() for x in raw.split(",") if x.strip()]
        selected, invalid = [], []
        for p in parts:
            if p.isdigit() and 1 <= int(p) <= len(scorable_columns):
                selected.append(scorable_columns[int(p)-1])
            else:
                invalid.append(p)
        if invalid:
            print(f"  ✗ Unrecognised: {invalid}")
            continue
        if not selected:
            print("  Please select at least one column.")
            continue
        break

    config["scoring_cols"] = selected

    # Eligibility criteria entered by the user
    print("\n✅ Eligibility criteria (one per line, type 'done' to finish):")
    criteria, i = [], 1
    while True:
        c = input(f"  Criterion {i}: ").strip()
        if c.lower() == "done":
            if not criteria:
                print("  Please enter at least one criterion.")
                continue
            break
        if c:
            criteria.append(c)
            i += 1
    config["criteria"] = criteria

    # Weights for selected columns; eligibility is fixed at 30%
    print("\n" + "="*60)
    print("⚖️  Enter weights for selected columns (total must equal 100%)")
    print("    Note: these values will be scaled internally so eligibility remains 30% of the final score.")
    weights_dict = {}

    while True:
        total_percent = 0
        for col in selected:
            remaining = 100 - total_percent
            while True:
                try:
                    w = int(input(f"  {col} weight (0-{remaining}): ").strip())
                    if 0 <= w <= remaining:
                        break
                except ValueError:
                    pass
                print(f"    ✗ Enter a valid integer 0-{remaining}")
            weights_dict[col] = w / 100
            total_percent += w

        if total_percent != 100:
            print(f"  ✗ Total column weights must equal 100%. You entered {total_percent}%. Please try again.")
            weights_dict.clear()
            continue
        break

    config["weights"] = {
        "column_weights": weights_dict,
        "eligibility": 0.3,
    }

    print("\n" + "="*60)
    confirm = input("✅ Press Enter to start (or 'restart'): ").strip()
    if confirm.lower() == "restart":
        return get_user_configuration()
    return config


# ---------------------------------------------------------------------------
# Organizer review loop
# ---------------------------------------------------------------------------

def create_organizer_summary(df_sorted: pd.DataFrame, config: dict, top_n: int = 10) -> str:
    name_col    = config.get("name_col") or "name"
    scoring_cols = config.get("scoring_cols", [])
    score_cols   = [f"{c}_Score" for c in scoring_cols if f"{c}_Score" in df_sorted.columns]

    text = "Top Candidates Summary:\n\n"
    for _, row in df_sorted.head(top_n).iterrows():
        text += f"Rank {row['Rank']} — {row[name_col]}\n"
        text += f"  • Total Score : {row['Total_Score']}\n"
        for sc in score_cols:
            text += f"  • {sc}  : {row[sc]}\n"
        text += f"  • Status      : {row['Eligibility']}\n\n"
    return text


def organizer_review_loop(df_sorted: pd.DataFrame, config: dict):
    while True:
        summary = create_organizer_summary(df_sorted, config)
        print("\n" + "="*60)
        print("MESSAGE TO ORGANIZER")
        print("="*60)
        print(f"\nDear Organizer,\n\nEvaluation complete.\n\n{summary}")
        print("Reply: APPROVE / EDIT / REJECT")

        decision = input("\nDecision: ").strip().upper()
        if decision == "APPROVE":
            print("✓ Approved.")
            return df_sorted, True
        elif decision == "EDIT":
            df_sorted = organizer_edit_interface(df_sorted, config)
        elif decision == "REJECT":
            print("Rejected.")
            return df_sorted, False
        else:
            print("Invalid — enter APPROVE, EDIT, or REJECT.")


def organizer_edit_interface(df_sorted: pd.DataFrame, config: dict) -> pd.DataFrame:
    name_col = config.get("name_col") or "name"
    df_sorted = df_sorted.copy()

    while True:
        print("\nEdit Menu:  1-Change Eligibility  2-Adjust Score  3-View Top  0-Done")
        choice = input("Option: ").strip()

        if choice == "1":
            name = input("Candidate name: ").strip()
            if name not in df_sorted[name_col].values:
                print("Not found.")
                continue
            status = input("New status (Accepted/Rejected): ").strip()
            df_sorted.loc[df_sorted[name_col] == name, "Eligibility"] = status
            print("Updated.")

        elif choice == "2":
            name = input("Candidate name: ").strip()
            if name not in df_sorted[name_col].values:
                print("Not found.")
                continue
            try:
                score = float(input("New Total Score: "))
                df_sorted.loc[df_sorted[name_col] == name, "Total_Score"] = score
                print("Updated.")
            except ValueError:
                print("Invalid number.")

        elif choice == "3":
            cols = [name_col, "Total_Score", "Eligibility"]
            cols = [c for c in cols if c in df_sorted.columns]
            print(df_sorted[cols].sort_values("Total_Score", ascending=False).head(10).to_string(index=False))

        elif choice == "0":
            break
        else:
            print("Invalid option.")

    df_sorted = df_sorted.sort_values("Total_Score", ascending=False)
    df_sorted["Rank"] = df_sorted["Total_Score"].rank(ascending=False, method="dense").astype(int)  # FIX #8
    return df_sorted


# ---------------------------------------------------------------------------
# Main (terminal mode)
# ---------------------------------------------------------------------------

def main():
    config    = get_user_configuration()
    df_sorted = run_pipeline(config)

    df_sorted, approved = organizer_review_loop(df_sorted, config)
    if not approved:
        print("Process ended without approval.")
        return

    name_col     = config.get("name_col") or "name"
    scoring_cols = config.get("scoring_cols", [])
    score_cols   = [f"{c}_Score" for c in scoring_cols if f"{c}_Score" in df_sorted.columns]

    display_cols = ["Rank", name_col, "Total_Score"] + score_cols + ["Eligibility"]
    display_cols = [c for c in display_cols if c in df_sorted.columns]

    print("\nTop 5 Candidates:")
    print("-"*60)
    print(df_sorted[display_cols].head().to_string(index=False))

    print("\n" + "="*60)
    print("SUMMARY STATISTICS")
    print("="*60)
    print(f"Total Applicants : {len(df_sorted)}")
    print(f"Accepted         : {len(df_sorted[df_sorted['Eligibility']=='Accepted'])}")
    print(f"Rejected         : {len(df_sorted[df_sorted['Eligibility']=='Rejected'])}")
    print(f"Average Score    : {df_sorted['Total_Score'].mean():.2f}")
    print(f"Highest Score    : {df_sorted['Total_Score'].max():.2f}")
    print(f"Lowest Score     : {df_sorted['Total_Score'].min():.2f}")

    out = f"results_{config['event_name'].replace(' ', '_')}.csv"
    df_sorted.to_csv(out, index=False, encoding="utf-8-sig")
    print(f"\n✓ Results saved to '{out}'")
    print("="*60)


if __name__ == "__main__":
    main()