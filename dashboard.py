import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import plotly.graph_objects as go
import joblib
import sqlite3
import os
import warnings
warnings.filterwarnings("ignore")

# ============================================================
# PATHS
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, "database", "teacher_dashboard.db")

REG_MODEL_PATH = os.path.join(BASE_DIR, "models", "best_regression_model.joblib")
CLF_MODEL_PATH = os.path.join(BASE_DIR, "models", "best_classification_model.joblib")

# ============================================================
# MODEL FEATURE ORDER  (exactly as trained — 14 features)
# ============================================================
# previous_score, attendance, arrears_count, study_hours, sleep_hours,
# travel_time,
# social_media_usage_Low, social_media_usage_Medium,
# stress_level_Low, stress_level_Medium,
# internet_access_Unlimited,
# student_type_Hosteller,
# part_time_job_Yes,
# result_Pass          ← derived: 1 if previous_score >= 50 else 0

# ============================================================
# DATABASE
# ============================================================
def init_db():
    os.makedirs(os.path.join(BASE_DIR, "database"), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS uploads (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            filename        TEXT,
            total_students  INTEGER,
            avg_marks       REAL,
            avg_attendance  REAL,
            total_arrears   INTEGER,
            pass_count      INTEGER,
            fail_count      INTEGER,
            timestamp       DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS student_predictions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            student_index   INTEGER,
            predicted_mark  REAL,
            result          TEXT,
            timestamp       DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def log_upload(filename, total, avg_m, avg_att, total_ar, pass_cnt, fail_cnt):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        INSERT INTO uploads
        (filename,total_students,avg_marks,avg_attendance,
         total_arrears,pass_count,fail_count)
        VALUES (?,?,?,?,?,?,?)
    """, (filename, total, avg_m, avg_att, total_ar, pass_cnt, fail_cnt))
    conn.commit()
    conn.close()


def log_prediction(idx, mark, result):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        INSERT INTO student_predictions (student_index, predicted_mark, result)
        VALUES (?,?,?)
    """, (idx, mark, result))
    conn.commit()
    conn.close()


def fetch_uploads():
    if not os.path.exists(DB_PATH):
        return pd.DataFrame()
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        "SELECT * FROM uploads ORDER BY timestamp DESC", conn)
    conn.close()
    return df


def fetch_predictions():
    if not os.path.exists(DB_PATH):
        return pd.DataFrame()
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        "SELECT * FROM student_predictions ORDER BY timestamp DESC", conn)
    conn.close()
    return df


# ============================================================
# COLUMN ALIASES
# ============================================================
COLUMN_ALIASES = {
    "previous_score":      ["previous_score","prev_score","previous score",
                             "prev score","last_sem","last sem","last_score",
                             "lastscore","previous_marks"],
    "attendance":          ["attendance","attend","att",
                             "attendance_%","attendance_percent"],
    "arrears_count":       ["arrears_count","arrears","arrear",
                             "backlogs","backlog","arrears count"],
    "study_hours":         ["study_hours","study hours","studyhours",
                             "study_hr","study_time"],
    "sleep_hours":         ["sleep_hours","sleep hours","sleephours",
                             "sleep_hr","sleep_time"],
    "social_media_usage":  ["social_media_usage","social_media","social media",
                             "socialmedia","social"],
    "stress_level":        ["stress_level","stress level","stresslevel","stress"],
    "internet_access":     ["internet_access","internet access","internetaccess",
                             "internet","net_access"],
    "student_type":        ["student_type","student type","studenttype",
                             "residence","resident","day_scholar_hosteller",
                             "living","stay"],
    "travel_time":         ["travel_time","travel time","traveltime",
                             "travel_hr","commute_time","commute"],
    "part_time_job":       ["part_time_job","part time job","parttimejob",
                             "parttime","part_time","job"],
}

EXPECTED_COLUMNS = list(COLUMN_ALIASES.keys())   # 11 upload columns


def normalize(col):
    return col.strip().lower()


def map_columns(df_columns):
    norm_up  = {normalize(c): c for c in df_columns}
    mapping, matched = {}, set()
    for expected, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if normalize(alias) in norm_up:
                mapping[norm_up[normalize(alias)]] = expected
                matched.add(expected)
                break
    unmatched = [e for e in COLUMN_ALIASES if e not in matched]
    return mapping, unmatched


# ============================================================
# ENCODE ROW → 14-feature vector (matches model training)
# ============================================================
def encode_row(row):
    """
    Build the exact 14-feature input vector the models were trained on.
    raw_* columns hold the original string values before any encoding.
    """
    sm  = str(row.get("social_media_usage_raw", "")).strip()
    sl  = str(row.get("stress_level_raw",        "")).strip()
    ia  = str(row.get("internet_access_raw",     "")).strip()
    stt = str(row.get("student_type_raw",        "")).strip()
    pt  = str(row.get("part_time_job_raw",       "")).strip()

    prev = float(row["previous_score"])
    result_pass = 1 if prev >= 50 else 0   # derived feature

    return np.array([
        prev,                                        # previous_score
        float(row["attendance"]),                    # attendance
        float(row["arrears_count"]),                 # arrears_count
        float(row["study_hours"]),                   # study_hours
        float(row["sleep_hours"]),                   # sleep_hours
        float(row["travel_time"]),                   # travel_time
        1 if sm  == "Low"        else 0,             # social_media_usage_Low
        1 if sm  == "Medium"     else 0,             # social_media_usage_Medium
        1 if sl  == "Low"        else 0,             # stress_level_Low
        1 if sl  == "Medium"     else 0,             # stress_level_Medium
        1 if ia  == "Unlimited"  else 0,             # internet_access_Unlimited
        1 if stt == "Hosteller"  else 0,             # student_type_Hosteller
        1 if pt  == "Yes"        else 0,             # part_time_job_Yes
        result_pass,                                 # result_Pass (derived)
    ], dtype=float).reshape(1, -1)


# ============================================================
# SUGGESTION ENGINE
# ============================================================
def generate_suggestions(student):
    tips = []
    prev   = float(student["previous_score"])
    att    = float(student["attendance"])
    arr    = float(student["arrears_count"])
    study  = float(student["study_hours"])
    sleep  = float(student["sleep_hours"])
    travel = float(student["travel_time"])
    sm     = str(student.get("social_media_usage_raw","")).strip().lower()
    sl     = str(student.get("stress_level_raw","")).strip().lower()
    ia     = str(student.get("internet_access_raw","")).strip().lower()
    pt     = str(student.get("part_time_job_raw","")).strip().lower()

    if prev < 50:
        tips.append("📚 Previous score is below 50 — urgent remedial support needed before next semester.")
    elif prev < 60:
        tips.append("📖 Previous score is below 60 — encourage revision of weak subjects.")
    if att < 75:
        tips.append("🏫 Attendance below 75% — student risks detention; strict follow-up required.")
    elif att < 85:
        tips.append("📅 Attendance below 85% — advise student to attend more regularly.")
    if arr > 2:
        tips.append(f"⚠️ {int(arr)} arrears pending — prioritise clearing backlogs before next sem.")
    elif arr > 0:
        tips.append("📝 Has pending arrears — allocate weekly time to clear them.")
    if study < 3:
        tips.append("⏰ Study hours very low (< 3 hrs) — recommend structured daily study schedule.")
    elif study < 5:
        tips.append("📖 Study hours below 5 — encourage at least 5 focused hours daily.")
    if sleep < 6:
        tips.append("😴 Less than 6 hrs sleep — inadequate sleep hurts cognition and memory.")
    elif sleep > 9:
        tips.append("🛏️ Sleeping more than 9 hrs — excess sleep reduces productive study time.")
    if travel > 60:
        tips.append("🚌 Travel time > 60 min — suggest using commute for light revision or podcasts.")
    if sm == "high":
        tips.append("📵 High social media usage — recommend limiting screen time to under 1 hr/day.")
    if sl == "high":
        tips.append("🧘 High stress — schedule counselling session or introduce stress management activities.")
    elif sl == "medium":
        tips.append("😌 Medium stress — encourage healthy study-break balance and peer support.")
    if ia in ["none","limited"]:
        tips.append("🌐 Limited internet — direct student to college library or campus Wi-Fi for resources.")
    if pt == "yes":
        tips.append("💼 Part-time job — ensure work hours don't conflict with study or sleep time.")
    if not tips:
        tips.append("🌟 Student is performing well across all parameters — encourage them to keep it up!")
    return tips


# ============================================================
# MAIN DASHBOARD
# ============================================================
init_db()


def show_teacher_dashboard():
    st.set_page_config(page_title="SMART Teacher Dashboard", layout="wide")
    st.title("👩‍🏫  Teacher Dashboard — Next Semester Prediction")

    # ── Load Models ─────────────────────────────────────────────────
    @st.cache_resource
    def load_models():
        reg_model = joblib.load(REG_MODEL_PATH)
        clf_model = joblib.load(CLF_MODEL_PATH)
        return reg_model, clf_model

    reg_model, clf_model = load_models()

    # ── Expected Format Preview ──────────────────────────────────────
    st.subheader("📤 Upload Student Dataset")
    with st.expander("📋 Expected Dataset Format (click to view)"):
        st.info("Your CSV/Excel must contain these 11 columns (any accepted alias works):")
        preview = pd.DataFrame({
            "Column #": range(1, 12),
            "Expected Column Name": EXPECTED_COLUMNS,
            "Example Aliases Accepted": [
                "prev_score, last_sem, previous score",
                "attend, att",
                "arrears, backlogs",
                "study hours, studyhours",
                "sleep hours, sleephours",
                "social_media, social media, social",
                "stress level, stresslevel",
                "internet, net_access",
                "residence, student type, day_scholar_hosteller",
                "travel time, commute",
                "part time job, parttime",
            ],
        })
        st.dataframe(preview, use_container_width=True)

    uploaded_file = st.file_uploader(
        "Upload CSV or Excel file", type=["csv", "xlsx"])
    if not uploaded_file:
        st.info("👆 Please upload a student dataset to begin analysis.")
        return

    # ── Read File ────────────────────────────────────────────────────
    try:
        df = (pd.read_csv(uploaded_file)
              if uploaded_file.name.endswith(".csv")
              else pd.read_excel(uploaded_file))
    except Exception as e:
        st.error(f"Error reading file: {e}")
        return

    # ── Column Mapping ───────────────────────────────────────────────
    mapping, unmatched = map_columns(df.columns.tolist())

    if unmatched:
        st.error("❌ Some required columns could not be recognised.")
        for col in unmatched:
            accepted = " / ".join([f"`{a}`" for a in COLUMN_ALIASES[col]])
            st.markdown(f"**Missing:** `{col}` — accepted names: {accepted}")
        with st.expander("📋 Full accepted names list"):
            rows = [{"Required Column": k,
                     "Accepted Names": " / ".join(v)}
                    for k, v in COLUMN_ALIASES.items()]
            st.dataframe(pd.DataFrame(rows), use_container_width=True)
        return

    df = df.rename(columns=mapping)

    # Save raw categoricals before any encoding
    for cat in ["social_media_usage", "stress_level", "internet_access",
                "student_type", "part_time_job"]:
        df[cat + "_raw"] = df[cat].astype(str).str.strip()

    auto_mapped = {o: e for o, e in mapping.items() if o != e}
    if auto_mapped:
        st.success("✅ All columns recognised! Some were auto-mapped.")
        with st.expander("🔄 View auto-mapped columns"):
            st.table(pd.DataFrame(
                [{"Your Column": o, "Mapped To": e}
                 for o, e in auto_mapped.items()]))
    else:
        st.success("✅ Perfect! All column names matched exactly.")

    st.dataframe(df[EXPECTED_COLUMNS].head(), use_container_width=True)

    # ── Sidebar Filters ──────────────────────────────────────────────
    st.sidebar.header("🔎 Filter Students")
    min_att = st.sidebar.slider("Minimum Attendance",  0, 100,  0)
    max_arr = st.sidebar.slider("Maximum Arrears",     0,  20, 20)

    fdf = df[
        (df["attendance"]   >= min_att) &
        (df["arrears_count"] <= max_arr)
    ].copy().reset_index(drop=True)

    if fdf.empty:
        st.warning("No students match the current filter settings.")
        return

    # ── Run Predictions for ALL Students ────────────────────────────
    pred_scores, pred_results = [], []
    for _, row in fdf.iterrows():
        try:
            vec   = encode_row(row)
            score = round(float(reg_model.predict(vec)[0]), 2)
            label = clf_model.predict(vec)[0]          # 0 or 1
            res   = "PASS" if label == 1 else "FAIL"
        except Exception:
            score, res = 0.0, "FAIL"
        pred_scores.append(score)
        pred_results.append(res)

    fdf["predicted_next_sem"] = pred_scores
    fdf["predicted_result"]   = pred_results

    # ── Class Overview Metrics ───────────────────────────────────────
    st.header("📊 Class Overview Metrics")

    total_students = len(fdf)
    avg_prev       = fdf["previous_score"].mean()
    avg_pred       = fdf["predicted_next_sem"].mean()
    avg_att        = fdf["attendance"].mean()
    total_arr      = int(fdf["arrears_count"].sum())
    pass_cnt       = int((fdf["predicted_result"] == "PASS").sum())
    fail_cnt       = int((fdf["predicted_result"] == "FAIL").sum())

    log_upload(uploaded_file.name, total_students,
               avg_pred, avg_att, total_arr, pass_cnt, fail_cnt)

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("👥 Total Students",      total_students)
    c2.metric("📝 Avg Previous Score",  f"{avg_prev:.2f}")
    c3.metric("🔮 Avg Predicted Score", f"{avg_pred:.2f}")
    c4.metric("📅 Avg Attendance (%)",  f"{avg_att:.2f}")
    c5.metric("✅ Predicted Pass",       pass_cnt)
    c6.metric("❌ Predicted Fail",       fail_cnt)

    # ── Pass vs Fail Bar Chart ───────────────────────────────────────
    st.subheader("🎓 Predicted Pass vs Fail Distribution")
    st.bar_chart(fdf["predicted_result"].value_counts())

    # ── Predicted Score Distribution ─────────────────────────────────
    st.subheader("📈 Predicted Next Semester Score Distribution")
    fig1, ax1 = plt.subplots()
    ax1.hist(fdf["predicted_next_sem"], bins=10,
             color="#4C72B0", edgecolor="white")
    ax1.set_xlabel("Predicted Score")
    ax1.set_ylabel("Number of Students")
    ax1.set_xlim(0, 100)
    st.pyplot(fig1)

    # ── Attendance Distribution ──────────────────────────────────────
    st.subheader("📊 Attendance Distribution")
    fig2, ax2 = plt.subplots()
    ax2.hist(fdf["attendance"], bins=10,
             color="#55A868", edgecolor="white")
    ax2.set_xlabel("Attendance (%)")
    ax2.set_ylabel("Number of Students")
    st.pyplot(fig2)


    # ── Class-Level Suggestions ──────────────────────────────────────
    st.subheader("💡 Class-Level Improvement Suggestions")
    class_tips = []
    if avg_att < 75:
        class_tips.append(
            f"🏫 Class average attendance is **{avg_att:.1f}%** — below 75%. "
            f"Conduct attendance awareness sessions.")
    if avg_prev < 60:
        class_tips.append(
            f"📚 Average previous score is **{avg_prev:.1f}** — consider "
            f"extra coaching or remedial classes.")
    if total_arr > total_students:
        class_tips.append(
            f"⚠️ High total arrears (**{total_arr}**) — organise arrear coaching camps.")
    high_stress = (fdf["stress_level_raw"].str.lower() == "high").sum()
    if high_stress > total_students * 0.3:
        class_tips.append(
            f"🧘 **{high_stress}** students report high stress — "
            f"schedule counselling sessions.")
    high_social = (fdf["social_media_usage_raw"].str.lower() == "high").sum()
    if high_social > total_students * 0.4:
        class_tips.append(
            f"📵 **{high_social}** students have high social media usage — "
            f"run a digital wellness workshop.")
    if fail_cnt > 0:
        class_tips.append(
            f"❌ **{fail_cnt}** students predicted to fail — "
            f"schedule one-on-one mentor meetings.")
    if not class_tips:
        class_tips.append(
            "🌟 The class is performing well overall! "
            "Encourage students to maintain their momentum.")
    for tip in class_tips:
        st.markdown(f"- {tip}")

    # ── Top 5 Performers ─────────────────────────────────────────────
    st.subheader("🏆 Top 5 Performers (by Predicted Score)")
    top5 = fdf.nlargest(5, "predicted_next_sem")[
        ["previous_score", "attendance", "arrears_count",
         "predicted_next_sem", "predicted_result"]]
    st.dataframe(top5, use_container_width=True)

    # ── At-Risk Students ─────────────────────────────────────────────
    st.subheader("⚠️ Students in Danger Zone")
    danger = fdf[
        (fdf["predicted_next_sem"] < 50) |
        (fdf["attendance"]          < 75) |
        (fdf["arrears_count"]       >  2)
    ][["previous_score", "attendance", "arrears_count",
       "predicted_next_sem", "predicted_result"]]

    if danger.empty:
        st.success("🎉 No students in danger zone!")
    else:
        st.error(f"⚠️ {len(danger)} student(s) need immediate attention!")
        st.dataframe(danger, use_container_width=True)

    # ── Upload History ───────────────────────────────────────────────
    with st.expander("📁 Upload History"):
        uploads_df = fetch_uploads()
        if uploads_df.empty:
            st.write("No upload records yet.")
        else:
            st.dataframe(uploads_df, use_container_width=True)

    # ════════════════════════════════════════════════════════════════
    # INDIVIDUAL STUDENT ANALYSIS
    # ════════════════════════════════════════════════════════════════
    st.header("🔍 Individual Student Analysis")

    selected_idx = st.selectbox(
        "Select Student by Row Number", fdf.index.tolist())

    student = fdf.loc[selected_idx]

    st.subheader(f"Student #{selected_idx} — Detailed Profile")

    # ── Info Cards ───────────────────────────────────────────────────
    i1, i2, i3, i4 = st.columns(4)
    i1.metric("Previous Score",  f"{student['previous_score']:.2f}")
    i2.metric("Attendance",      f"{student['attendance']:.1f}%")
    i3.metric("Arrears",         int(student['arrears_count']))
    i4.metric("Study Hrs/Day",   f"{student['study_hours']:.1f}")

    i5, i6, i7, i8 = st.columns(4)
    i5.metric("Sleep Hrs/Day",   f"{student['sleep_hours']:.1f}")
    i6.metric("Travel Time",     f"{student['travel_time']:.0f} min")
    i7.metric("Stress Level",    student['stress_level_raw'])
    i8.metric("Social Media",    student['social_media_usage_raw'])

    # ── Radar Chart ──────────────────────────────────────────────────
    st.subheader("📌 Student Strength Radar")
    radar_vals = [
        min(float(student["previous_score"]), 100),
        min(float(student["attendance"]),     100),
        min(float(student["study_hours"]) * 8.33, 100),
        min(float(student["sleep_hours"]) * 12.5, 100),
        max(0.0, 100 - float(student["travel_time"])),
    ]
    radar_cats = ["Prev Score", "Attendance", "Study Hours",
                  "Sleep Hours", "Travel Efficiency"]
    fig4 = go.Figure()
    fig4.add_trace(go.Scatterpolar(
        r=radar_vals, theta=radar_cats,
        fill="toself", line_color="#4C72B0"))
    fig4.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        showlegend=False, margin=dict(t=30, b=30))
    st.plotly_chart(fig4, use_container_width=True)

    # ── Predict Button ───────────────────────────────────────────────
    st.subheader("🤖 Next Semester Prediction")

    if st.button("🔮 Predict Next Semester Mark for This Student"):

        vec   = encode_row(student)
        pred  = round(float(reg_model.predict(vec)[0]), 2)
        label = clf_model.predict(vec)[0]     # 0 or 1
        res   = "PASS" if label == 1 else "FAIL"
        prob  = clf_model.predict_proba(vec)[0]
        conf  = round(float(max(prob)) * 100, 1)

        log_prediction(selected_idx, pred, res)

        col_a, col_b, col_c = st.columns(3)
        col_a.metric("🎯 Predicted Next Sem Mark", f"{pred:.2f}")
        col_b.metric("📋 Result",                  res)
        col_c.metric("📊 Model Confidence",        f"{conf}%")

        if res == "PASS":
            st.success(
                f"✅ Student #{selected_idx} is predicted to PASS "
                f"next semester with a score of {pred}.")
        else:
            st.error(
                f"❌ Student #{selected_idx} is at risk of FAILING "
                f"next semester (predicted score: {pred}).")

        # ── Previous vs Predicted Bar ────────────────────────────────
        st.subheader("📊 Previous Score vs Predicted Next Sem Score")
        fig5, ax5 = plt.subplots()
        bars = ax5.bar(
            ["Previous Score", "Predicted Next Sem"],
            [float(student["previous_score"]), pred],
            color=["#4C72B0", "#55A868" if res == "PASS" else "#C44E52"])
        ax5.set_ylim(0, 100)
        ax5.set_ylabel("Score")
        ax5.axhline(y=50, color="red", linestyle="--",
                    linewidth=1, label="Pass threshold (50)")
        ax5.legend()
        for bar, val in zip(bars,
                            [float(student["previous_score"]), pred]):
            ax5.text(bar.get_x() + bar.get_width() / 2,
                     bar.get_height() + 1,
                     f"{val:.1f}", ha="center",
                     fontsize=11, fontweight="bold")
        st.pyplot(fig5)

        # ── Personalised Suggestions ─────────────────────────────────
        st.subheader(
            f"💡 Personalised Suggestions for Student #{selected_idx}")
        tips = generate_suggestions(student)
        for tip in tips:
            st.markdown(f"- {tip}")

        # ── Prediction History ───────────────────────────────────────
        with st.expander("📝 Prediction History (Database)"):
            preds_df = fetch_predictions()
            if preds_df.empty:
                st.write("No predictions logged yet.")
            else:
                st.dataframe(preds_df, use_container_width=True)

    else:
        # Pre-computed prediction shown before button press
        pre_pred = round(float(student["predicted_next_sem"]), 2)
        pre_res  = student["predicted_result"]
        if pre_res == "PASS":
            st.success(
                f"🔮 Pre-computed: **{pre_pred}** — **{pre_res}**  "
                f"_(Click the button above to log and see full analysis)_")
        else:
            st.warning(
                f"🔮 Pre-computed: **{pre_pred}** — **{pre_res}**  "
                f"_(Click the button above to log and see full analysis)_")


# ── Run ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    show_teacher_dashboard()