import streamlit as st
import pandas as pd
import base64
import tempfile
import hashlib
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from main import (
    run_pipeline,
    load_dataframe,
    detect_name_column,
    detect_motivation_column,
)

# =========================
# Helpers
# =========================
def img_to_data_uri(path: str) -> str:
    p = Path(path)
    if not p.exists():
        return ""
    mime = "image/png" if p.suffix.lower() == ".png" else "image/jpeg"
    b64 = base64.b64encode(p.read_bytes()).decode("utf-8")
    return f"data:{mime};base64,{b64}"


def sheet_to_csv_url(sheet_url: str) -> str:
    u = sheet_url.strip()
    parsed = urlparse(u)
    gid = parse_qs(parsed.query).get("gid", [None])[0]

    base = u.split("/edit")[0].split("/view")[0].split("?")[0]
    csv = f"{base}/export?format=csv"
    if gid:
        csv += f"&gid={gid}"
    return csv


@st.cache_data(show_spinner=False)
def load_preview_from_google_sheet(sheet_url: str):
    csv_url = sheet_to_csv_url(sheet_url)
    return pd.read_csv(csv_url)


def save_uploaded_file(uploaded_file):
    suffix = Path(uploaded_file.name).suffix
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(uploaded_file.getbuffer())
    tmp.close()
    return tmp.name


def df_to_html_table(df, max_height=360):
    show_df = df.copy().fillna("")
    return f"""
    <div class="table-wrap" style="max-height:{max_height}px;">
      <div class="table-hint">
        Showing <b>{len(show_df)}</b> rows.
      </div>
      {show_df.to_html(index=False, escape=True)}
    </div>
    """


def build_scorable_columns(cols):
    excluded_for_scoring = [
        "timestamp", "time", "date", "email", "e-mail", "gmail", "mail",
        "phone", "mobile", "رقم الجوال", "gender", "الجنس",
        "id", "الرقم الجامعي", "university id", "student id",
        "university", "الجامعة"
    ]

    return [
        col for col in cols
        if not any(x in str(col).strip().lower() for x in excluded_for_scoring)
    ]


# =========================
# Page Config
# =========================
st.set_page_config(
    page_title="GDGoC Applicant Evaluation System",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =========================
# Assets
# =========================
LOGO_IMG = img_to_data_uri("assets/Logo.png")
TOP_LOGO_IMG = img_to_data_uri("assets/top-corner.png")
BOTTOM_LOGO_IMG = img_to_data_uri("assets/bottom-corner.png")
UPLOAD_ICON = img_to_data_uri("assets/upload_icon.png")

# =========================
# CSS
# =========================
css = f"""
<style>
/* =========================
GENERAL PAGE + SCROLL
========================= */
html, body, .stApp {{
    background: #ffffff !important;
    color: #000000 !important;
    overflow-y: auto !important;
    height: auto !important;
}}

header[data-testid="stHeader"] {{
    background: #ffffff !important;
}}

header[data-testid="stHeader"] * {{
    color: #000000 !important;
}}

[data-testid="stAppViewContainer"] {{
    background: #ffffff !important;
    overflow-y: auto !important;
    height: auto !important;
    position: relative;
    z-index: 1;
}}

.block-container {{
    padding-top: 70px !important;
    padding-bottom: 60px !important;
}}

/* =========================
SIDEBAR FIX
========================= */
[data-testid="stSidebar"] {{
    background: #f3f4f6 !important;
    min-height: 100vh !important;
    height: auto !important;
}}

[data-testid="stSidebar"] > div {{
    background: #f3f4f6 !important;
    min-height: 100vh !important;
    height: auto !important;
}}

[data-testid="stSidebarContent"] {{
    background: #f3f4f6 !important;
    min-height: 100vh !important;
    height: auto !important;
    overflow-y: auto !important;
    padding-top: 35px !important;
    padding-bottom: 80px !important;
}}

[data-testid="stSidebar"] * {{
    color: #000000 !important;
}}

/* =========================
INPUTS
========================= */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stTextArea"] textarea {{
    background: #ffffff !important;
    color: #000000 !important;
    border: 2px solid #1a73e8 !important;
    border-radius: 10px !important;
    box-shadow: none !important;
}}

[data-testid="stTextInput"] input:focus,
[data-testid="stNumberInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {{
    border: 2px solid #1a73e8 !important;
    box-shadow: 0 0 0 1px #1a73e8 !important;
}}

/* =========================
SELECTBOX + MULTISELECT WHITE THEME
========================= */
[data-testid="stSelectbox"] > div,
[data-testid="stMultiSelect"] > div {{
    background: #ffffff !important;
    border: 2px solid #1a73e8 !important;
    border-radius: 10px !important;
    color: #000000 !important;
}}

[data-testid="stSelectbox"] div,
[data-testid="stMultiSelect"] div,
[data-testid="stSelectbox"] span,
[data-testid="stMultiSelect"] span {{
    color: #000000 !important;
}}

div[data-baseweb="select"],
div[data-baseweb="select"] > div {{
    background: #ffffff !important;
    color: #000000 !important;
    border-color: #1a73e8 !important;
}}

div[data-baseweb="popover"],
div[data-baseweb="popover"] > div {{
    background: #ffffff !important;
    color: #000000 !important;
}}

ul[data-baseweb="menu"],
div[role="listbox"] {{
    background: #ffffff !important;
    border: 2px solid #1a73e8 !important;
    border-radius: 12px !important;
    color: #000000 !important;
}}

ul[data-baseweb="menu"] li,
div[role="option"] {{
    background: #ffffff !important;
    color: #000000 !important;
}}

ul[data-baseweb="menu"] li *,
div[role="option"] * {{
    color: #000000 !important;
}}

ul[data-baseweb="menu"] li:hover,
div[role="option"]:hover {{
    background: #eef5ff !important;
    color: #000000 !important;
}}

[data-baseweb="tag"] {{
    background: #fff3f3 !important;
    border: 1px solid #1a73e8 !important;
    color: #000000 !important;
}}

[data-baseweb="tag"] * {{
    color: #000000 !important;
}}

/* =========================
RADIO
========================= */
[data-testid="stRadio"] > label {{
    background: transparent !important;
    border: none !important;
    padding: 0 !important;
    margin-bottom: 8px !important;
    color: #000000 !important;
    font-weight: 700 !important;
}}

[data-testid="stRadio"] div[role="radiogroup"] label {{
    background: #ffffff !important;
    border: 2px solid #1a73e8 !important;
    border-radius: 10px !important;
    padding: 7px 12px !important;
    margin-bottom: 7px !important;
    color: #000000 !important;
}}

/* =========================
BUTTONS
========================= */
div[data-testid="stButton"] button,
div[data-testid="stDownloadButton"] button {{
    width: 100%;
    border-radius: 12px !important;
    font-weight: 800 !important;
    background: #ffffff !important;
    color: #000000 !important;
    border: 2px solid #1a73e8 !important;
}}

div[data-testid="stButton"] button:hover,
div[data-testid="stDownloadButton"] button:hover {{
    background: #eef5ff !important;
    color: #000000 !important;
}}

/* =========================
CORNER IMAGES
========================= */
.corner-logo {{
    position: fixed;
    right: 0 !important;
    width: 360px;
    height: 360px;
    z-index: 0;
    pointer-events: none;
    background-repeat: no-repeat;
    background-size: contain;
    background-position: center;
    margin: 0 !important;
    padding: 0 !important;
}}

.top-logo {{
    top: 0 !important;
    {"background-image: url('" + TOP_LOGO_IMG + "');" if TOP_LOGO_IMG else ""}
}}

.bottom-logo {{
    bottom: 0 !important;
    {"background-image: url('" + BOTTOM_LOGO_IMG + "');" if BOTTOM_LOGO_IMG else ""}
}}
/* =========================
HEADER
========================= */
.header-wrap {{
    display: flex;
    align-items: center;
    gap: 14px;
    margin: 15px 5px 40px 5px;
}}

.logo-img {{
    width: 85px;
    height: 85px;
    border-radius: 14px;
    {"background: url('" + LOGO_IMG + "') no-repeat center/cover;" if LOGO_IMG else "background:#f3f4f6;"}
}}

.title {{
    font-size: 26px;
    font-weight: 900;
    color: #111827;
}}

.subtitle {{
    font-size: 14px;
    color: #000000;
}}

.card {{
    background: #ffffff;
    border: 1px solid #dbeafe;
    border-radius: 16px;
    padding: 18px;
    margin-bottom: 14px;
}}

.metric-box {{
    background:#f8fbff;
    border:1px solid #dbeafe;
    border-radius:14px;
    padding:14px;
    text-align:center;
}}

.metric-value {{
    font-size:24px;
    font-weight:900;
    color:#1a73e8;
}}

.metric-label {{
    color:#000000;
    font-size:13px;
}}

/* =========================
TABLE STYLE
========================= */
.table-wrap {{
    background: #ffffff !important;
    border: 1.5px solid #1a73e8 !important;
    border-radius: 12px !important;
    padding: 0 !important;
    overflow: auto !important;
    max-height: 360px !important;
}}

.table-hint {{
    color: #374151 !important;
    font-size: 12px !important;
    padding: 8px 10px !important;
    margin: 0 !important;
    border-bottom: 1px solid #e5e7eb !important;
}}

.table-wrap table {{
    width: max-content !important;
    min-width: 100% !important;
    border-collapse: collapse !important;
    background: #ffffff !important;
    color: #000000 !important;
    font-size: 13px !important;
    table-layout: auto !important;
}}

.table-wrap th {{
    background: #f8fbff !important;
    color: #000000 !important;
    font-weight: 800 !important;
    border: 1px solid #e5e7eb !important;
    padding: 8px 10px !important;
    text-align: left !important;
    white-space: nowrap !important;
    vertical-align: middle !important;
    height: 38px !important;
    max-height: 38px !important;
    line-height: 1.2 !important;
}}

.table-wrap td {{
    background: #ffffff !important;
    color: #000000 !important;
    border: 1px solid #e5e7eb !important;
    padding: 7px 10px !important;
    vertical-align: middle !important;
    white-space: nowrap !important;
    height: 34px !important;
    max-height: 34px !important;
    line-height: 1.2 !important;
}}

/* =========================
SPINNER
========================= */
[data-testid="stSpinner"] * {{
    color: #000000 !important;
    font-weight: 700 !important;
}}

/* =========================
FILE UPLOADER
========================= */

/* =========================
FILE UPLOADER
========================= */

[data-testid="stFileUploader"] label {{
    display: none !important;
}}

[data-testid="stFileUploader"] {{
    background: transparent !important;
    margin-top: 8px !important;
}}

/* الصندوق الأساسي */
[data-testid="stFileUploader"] section {{
    background: #ffffff !important;
    border: 2px dashed #1a73e8 !important;
    border-radius: 18px !important;
    padding: 22px 14px !important;
    min-height: 215px !important;
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
    justify-content: center !important;
    gap: 10px !important;
}}

/* إخفاء جملة Drag and drop */
[data-testid="stFileUploaderDropzoneInstructions"] {{
    display: none !important;
}}

[data-testid="stFileUploader"] section > div > div > span {{
    display: none !important;
}}

/* إخفاء أيقونة Streamlit الافتراضية */
[data-testid="stFileUploader"] section svg {{
    display: none !important;
}}

/* الأيقونة المخصصة */
[data-testid="stFileUploader"] section::before {{
    content: "";
    display: block;
    width: 70px;
    height: 70px;
    margin: 0 auto 4px auto;
    background-image: url('{UPLOAD_ICON}');
    background-size: contain;
    background-repeat: no-repeat;
    background-position: center;
}}

/* النصوص */
[data-testid="stFileUploader"] div,
[data-testid="stFileUploader"] span,
[data-testid="stFileUploader"] small,
[data-testid="stFileUploader"] p {{
    background: transparent !important;
    color: #000000 !important;
    text-align: center !important;
}}

/* الترتيب الداخلي */
[data-testid="stFileUploader"] section > div {{
    width: 100% !important;
    border: none !important;
    background: transparent !important;
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
    justify-content: center !important;
}}

/* زر Browse files */
[data-testid="stFileUploader"] button {{
    background: #ffffff !important;
    color: #000000 !important;
    border: 2px solid #1a73e8 !important;
    border-radius: 12px !important;
    font-weight: 800 !important;
    padding: 8px 18px !important;
    margin-top: 8px !important;
}}

[data-testid="stFileUploader"] button:hover {{
    background: #eef5ff !important;
    color: #000000 !important;
}}
/* =========================
INFO / SUCCESS / ERROR TEXT
========================= */

/* info message */
[data-testid="stAlert"] {{
    color: #000000 !important;
}}

[data-testid="stAlert"] * {{
    color: #000000 !important;
}}

/* success */
.element-container .stSuccess {{
    color: #000000 !important;
}}

.element-container .stSuccess * {{
    color: #000000 !important;
}}

/* info */
.element-container .stInfo {{
    color: #000000 !important;
}}

.element-container .stInfo * {{
    color: #000000 !important;
}}
</style>
"""
st.markdown(css, unsafe_allow_html=True)

# =========================
# Header
# =========================
st.markdown(
    """
    <div class="header-wrap">
      <div class="logo-img"></div>
      <div>
        <div class="title">GDGoC Applicant Evaluation System</div>
        <div class="subtitle">
          Evaluate applicants using eligibility criteria, selected scoring columns, AI feedback, and ranking.
        </div>
      </div>
    </div>
    """,
    unsafe_allow_html=True
)
st.markdown('<div class="corner-logo top-logo"></div>', unsafe_allow_html=True)
st.markdown('<div class="corner-logo bottom-logo"></div>', unsafe_allow_html=True)

# =========================
# Session State
# =========================
if "df_preview" not in st.session_state:
    st.session_state.df_preview = None

if "source_path" not in st.session_state:
    st.session_state.source_path = ""

if "df_results" not in st.session_state:
    st.session_state.df_results = None

if "config_used" not in st.session_state:
    st.session_state.config_used = None

# =========================
# Sidebar - Data Source
# =========================
st.sidebar.title("Configuration")

event_name = st.sidebar.text_input("Event Name", value="GDGoC Event", key="event_name_input")

source_type = st.sidebar.radio(
    "Data Source",
    ["Google Sheet URL", "Upload Excel/CSV"],
    key="source_type_radio"
)

uploaded_file = None
sheet_url = ""

if source_type == "Google Sheet URL":
    sheet_url = st.sidebar.text_input("Google Sheet URL", key="sheet_url_input")
    load_clicked = st.sidebar.button("Load Sheet Columns", key="load_sheet_button")

    if load_clicked and sheet_url.strip():
        try:
            df_preview = load_preview_from_google_sheet(sheet_url)
            df_preview.columns = [str(c).strip() for c in df_preview.columns]
            st.session_state.df_preview = df_preview
            st.session_state.source_path = sheet_url.strip()
            st.sidebar.success("Sheet loaded.")
        except Exception as e:
            st.sidebar.error(f"Could not load sheet: {e}")

else:
    uploaded_file = st.sidebar.file_uploader(
        "Upload file",
        type=["xlsx", "xls", "xlsm", "csv"],
        key="uploaded_file_input"
    )
    if uploaded_file is not None:
        try:
            tmp_path = save_uploaded_file(uploaded_file)
            df_preview = load_dataframe(tmp_path)
            df_preview.columns = [str(c).strip() for c in df_preview.columns]
            st.session_state.df_preview = df_preview
            st.session_state.source_path = tmp_path
            st.sidebar.success("File loaded.")
        except Exception as e:
            st.sidebar.error(f"Could not load file: {e}")

df_preview = st.session_state.df_preview

# =========================
# Main Body Before Loading
# =========================
if df_preview is None:
    st.info("Load a Google Sheet or upload an Excel/CSV file first.")
    st.stop()

# =========================
# Column Detection
# =========================
all_cols = list(df_preview.columns)

auto_name = detect_name_column(df_preview)
auto_motivation = detect_motivation_column(df_preview)

name_index = all_cols.index(auto_name) if auto_name in all_cols else 0
motivation_index = all_cols.index(auto_motivation) if auto_motivation in all_cols else 0

scorable_columns = build_scorable_columns(all_cols)

if not scorable_columns:
    scorable_columns = all_cols

# =========================
# Sidebar - Evaluation Settings
# بدون form عشان اختيار أكثر من عمود يحدث الـ weights مباشرة
# =========================
st.sidebar.markdown("### Columns")

name_col = st.sidebar.selectbox(
    "Name Column",
    all_cols,
    index=name_index,
    key="name_col_select"
)

motivation_col = st.sidebar.selectbox(
    "Motivation / Eligibility Column",
    all_cols,
    index=motivation_index,
    key="motivation_col_select"
)

st.sidebar.markdown("### Columns to Score")

default_score_cols = []
if auto_motivation in scorable_columns:
    default_score_cols.append(auto_motivation)

scoring_cols = st.sidebar.multiselect(
    "Choose columns that AI should score",
    options=scorable_columns,
    default=default_score_cols,
    key="scoring_cols_select"
)

st.sidebar.markdown("### Eligibility Criteria")

criteria_text = st.sidebar.text_area(
    "One criterion per line",
    value="Technical background\nAI interest\nAutomation interest",
    key="criteria_text_area"
)

criteria = [
    c.strip()
    for c in criteria_text.splitlines()
    if c.strip()
]

st.sidebar.markdown("### Weights")
st.sidebar.caption(
    "Eligibility is fixed at 30%. The selected scoring columns share the remaining 70%."
)

weight_inputs = {}

if len(scoring_cols) > 0:
    # Default weights are distributed so their total is exactly 100%.
    # Example: 3 columns => 34, 33, 33 instead of 33, 33, 33.
    base_weight = 100 // len(scoring_cols)
    remainder = 100 % len(scoring_cols)

    for i, col in enumerate(scoring_cols):
        default_weight = base_weight + (1 if i < remainder else 0)
        safe_key = "weight_" + hashlib.md5(str(col).encode("utf-8")).hexdigest()

        weight_inputs[col] = st.sidebar.number_input(
            label=f"{col} weight %",
            min_value=0,
            max_value=100,
            value=default_weight,
            step=1,
            key=safe_key
        )

total_weight_percent = sum(weight_inputs.values())
weights_are_valid = bool(scoring_cols) and total_weight_percent == 100

if scoring_cols:
    if weights_are_valid:
        st.sidebar.success("Current total weight: 100%")
    else:
        st.sidebar.error(f"Current total weight: {total_weight_percent}%. It must equal 100% before running.")

run_now = st.sidebar.button(
    "Run Evaluation",
    key="run_evaluation_button",
    disabled=not weights_are_valid
)

# =========================
# Preview
# =========================
st.markdown('<div class="card">', unsafe_allow_html=True)
st.subheader("Loaded Data Preview")
st.write(f"Rows: **{len(df_preview)}** | Columns: **{len(df_preview.columns)}**")
st.markdown(
    df_to_html_table(df_preview, max_height=360),
    unsafe_allow_html=True
)
st.markdown('</div>', unsafe_allow_html=True)

# =========================
# Run Pipeline
# =========================
if run_now:

    if not scoring_cols:
        st.error("Please select at least one scoring column.")

    elif not criteria:
        st.error("Please enter at least one eligibility criterion.")

    elif total_weight_percent != 100:
        st.error("Total weights must equal 100%. Please adjust the weights before running.")

    else:
        normalized_column_weights = {
            col: weight_inputs[col] / 100
            for col in scoring_cols
        }

        config = {
            "event_name": event_name.strip() or "GDGoC Event",
            "sheet_url": st.session_state.source_path,
            "df": df_preview.copy(),

            "name_col": name_col,
            "motivation_col": motivation_col,

            "scoring_cols": scoring_cols,

            "criteria": criteria,

            "weights": {
                "column_weights": normalized_column_weights,
                "eligibility": 0.3
            }
        }

        with st.spinner("Running evaluation... This may take time because AI is scoring each applicant."):
            try:
                results = run_pipeline(config)

                st.session_state.df_results = results
                st.session_state.config_used = config

                st.success("Evaluation completed successfully.")

            except Exception as e:
                st.session_state.df_results = None
                st.error(f"Pipeline error: {e}")

# =========================
# Results
# =========================
if st.session_state.df_results is not None:

    df_results = st.session_state.df_results
    config_used = st.session_state.config_used or {}
    name_col_used = config_used.get("name_col", name_col)
    scoring_cols_used = config_used.get("scoring_cols", scoring_cols)

    accepted_count = len(df_results[df_results["Eligibility"] == "Accepted"]) if "Eligibility" in df_results.columns else 0
    rejected_count = len(df_results[df_results["Eligibility"] == "Rejected"]) if "Eligibility" in df_results.columns else 0
    avg_score = df_results["Total_Score"].mean() if "Total_Score" in df_results.columns else 0

    st.subheader("Summary")

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.markdown(
            f"""
            <div class="metric-box">
              <div class="metric-value">{len(df_results)}</div>
              <div class="metric-label">Total Applicants</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with c2:
        st.markdown(
            f"""
            <div class="metric-box">
              <div class="metric-value">{accepted_count}</div>
              <div class="metric-label">Accepted</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with c3:
        st.markdown(
            f"""
            <div class="metric-box">
              <div class="metric-value">{rejected_count}</div>
              <div class="metric-label">Rejected</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with c4:
        st.markdown(
            f"""
            <div class="metric-box">
              <div class="metric-value">{avg_score:.2f}</div>
              <div class="metric-label">Average Score</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.subheader("Top Candidates")

    score_cols = [
        f"{col}_Score"
        for col in scoring_cols_used
        if f"{col}_Score" in df_results.columns
    ]

    display_cols = [
        "Rank",
        name_col_used,
        "Total_Score",
        *score_cols,
        "Eligibility",
        "Eligibility_Score",
        "Reason"
    ]

    display_cols = [
        col for col in display_cols
        if col in df_results.columns
    ]

    st.markdown(
        df_to_html_table(df_results[display_cols], max_height=500),
        unsafe_allow_html=True
    )

    st.subheader("Full Results")
    st.markdown(
        df_to_html_table(df_results, max_height=600),
        unsafe_allow_html=True
    )

    csv_bytes = df_results.to_csv(index=False).encode("utf-8-sig")

    safe_event_name = event_name.replace(" ", "_") if event_name else "GDGoC_Event"

    st.download_button(
        "Download Results CSV",
        data=csv_bytes,
        file_name=f"results_{safe_event_name}.csv",
        mime="text/csv"
    )
