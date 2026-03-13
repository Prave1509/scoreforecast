import streamlit as st
import numpy as np
import joblib
import matplotlib.pyplot as plt
import sqlite3
import os

# ---------- Page Config ----------
st.set_page_config(
    page_title="Student Performance Predictor",
    page_icon="🎓",
    layout="wide"
)

# ---------- Custom CSS ----------
st.markdown("""
<style>
    html, body, [class*="css"] {
        font-family: 'Segoe UI', sans-serif;
    }

    .main { background-color: #f4f6fb; }

    .page-title {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1a1a2e;
        margin-bottom: 0.2rem;
    }

    .page-subtitle {
        font-size: 0.95rem;
        color: #666;
        margin-bottom: 1.5rem;
    }

    .result-box {
        background: white;
        border-radius: 12px;
        padding: 1.2rem 1.5rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.07);
        margin-bottom: 1rem;
    }

    .result-label {
        font-size: 0.8rem;
        color: #888;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 4px;
    }

    .result-value {
        font-size: 1.6rem;
        font-weight: 700;
        color: #1a1a2e;
    }

    .result-value.pass  { color: #276749; }
    .result-value.fail  { color: #c53030; }
    .result-value.score { color: #2b6cb0; }
    .result-value.grade { color: #744210; }

    .tip-card {
        background: #f0fff4;
        border-left: 4px solid #38a169;
        border-radius: 6px;
        padding: 0.7rem 1rem;
        margin-bottom: 0.5rem;
        font-size: 0.9rem;
        color: #2d3748;
    }

    .weakness-card {
        background: #fff5f5;
        border-left: 4px solid #e53e3e;
        border-radius: 6px;
        padding: 0.7rem 1rem;
        margin-bottom: 0.5rem;
        font-size: 0.9rem;
        color: #2d3748;
    }

    .section-title {
        font-size: 1.05rem;
        font-weight: 700;
        color: #1a1a2e;
        margin-bottom: 0.8rem;
        border-bottom: 2px solid #e2e8f0;
        padding-bottom: 0.3rem;
    }

    .model-info-box {
        background: #ebf4ff;
        border-left: 4px solid #3182ce;
        border-radius: 6px;
        padding: 0.8rem 1rem;
        margin-bottom: 0.6rem;
        font-size: 0.9rem;
        color: #2d3748;
    }

    .stButton > button {
        background: #1a1a2e;
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1.8rem;
        font-size: 0.95rem;
        font-weight: 600;
        width: 100%;
    }
    .stButton > button:hover { background: #2d2d5e; }
</style>
""", unsafe_allow_html=True)

# ---------- Database ----------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, "student.db")

def init_db():
    conn   = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            previous_score REAL, attendance REAL, arrears_count INTEGER,
            study_hours REAL, sleep_hours REAL, travel_time REAL,
            social_media TEXT, stress_level TEXT, internet_access TEXT,
            student_type TEXT, part_time_job TEXT,
            predicted_status TEXT, predicted_score REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()

def insert_record(data):
    conn   = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO predictions (
            previous_score, attendance, arrears_count, study_hours, sleep_hours,
            travel_time, social_media, stress_level, internet_access,
            student_type, part_time_job, predicted_status, predicted_score
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        data["previous_score"], data["attendance"], data["arrears_count"],
        data["study_hours"],    data["sleep_hours"], data["travel_time"],
        data["social_media"],   data["stress_level"], data["internet_access"],
        data["student_type"],   data["part_time_job"],
        data["predicted_status"], data["predicted_score"],
    ))
    conn.commit()
    conn.close()

# ---------- Load Models ----------
@st.cache_data(show_spinner=False)
def load_models():
    model_dir = os.path.join(BASE_DIR, "models")
    clf_file  = os.path.join(model_dir, "best_classification_model.joblib")
    reg_file  = os.path.join(model_dir, "best_regression_model.joblib")
    if not os.path.exists(clf_file):
        raise FileNotFoundError(f"Classification model not found: {clf_file}")
    if not os.path.exists(reg_file):
        raise FileNotFoundError(f"Regression model not found: {reg_file}")
    return joblib.load(clf_file), joblib.load(reg_file)

# ---------- Weakness Analysis ----------
def analyse_weaknesses(prev_score, attendance, arrears, study_hrs, sleep_hrs,
                        travel_time, stress, social, internet, student_type, part_time):
    weaknesses = []
    tips       = []

    if attendance < 75:
        weaknesses.append(f"⚠️ Low attendance ({attendance}%) — Minimum 75% required to appear for exams!")
        tips.append("📅 Plan your schedule and prioritize attending all classes, especially labs.")

    if arrears > 0:
        weaknesses.append(f"📚 You have {arrears} arrear(s) — This significantly impacts your overall score.")
        tips.append("🔁 Focus on clearing arrears first. Dedicate at least 1 hour/day to backlog subjects.")

    if study_hrs < 4:
        weaknesses.append(f"⏱️ Low study hours ({study_hrs} hrs/day) — Not enough for exam preparation.")
        tips.append("📖 Try the Pomodoro technique: 25 min study + 5 min break. Aim for at least 4–6 hrs/day.")

    if sleep_hrs < 6:
        weaknesses.append(f"😴 Insufficient sleep ({sleep_hrs} hrs) — Affects memory and concentration.")
        tips.append("🌙 Maintain 7–8 hours of sleep. Avoid studying late nights before exams.")

    if sleep_hrs > 9:
        weaknesses.append(f"😴 Oversleeping ({sleep_hrs} hrs) — Too much sleep reduces productive hours.")
        tips.append("⏰ Set a consistent wake-up time. 7–8 hours is the sweet spot for students.")

    if stress == "High":
        weaknesses.append("😰 High stress level — Can negatively affect exam performance.")
        tips.append("🧘 Practice 10 min of meditation or deep breathing daily. Take short breaks between studies.")

    if social == "High":
        weaknesses.append("📱 High social media usage — Major distraction from studies.")
        tips.append("📵 Use app timers to limit social media to 30–45 min/day during exam season.")

    if travel_time > 60:
        weaknesses.append(f"🚌 High travel time ({travel_time} min) — Reduces available study time.")
        tips.append("📚 Use travel time productively — listen to recorded lectures or review notes on phone.")

    if part_time == "Yes":
        weaknesses.append("💼 Part-time job — Reduces energy and time available for studies.")
        tips.append("📆 Create a strict timetable balancing work and study. Consider reducing work hours near exams.")

    if internet == "No":
        weaknesses.append("🌐 No unlimited internet — Limits access to online resources.")
        tips.append("💾 Download study materials and YouTube lectures offline when you have WiFi access.")

    if prev_score < 60:
        weaknesses.append(f"📉 Low previous score ({prev_score}) — Indicates need for a stronger foundation.")
        tips.append("🔍 Identify weak subjects and spend extra time on fundamentals. Seek help from faculty.")

    if not weaknesses:
        weaknesses.append("✅ No major weaknesses found! You're on the right track.")
        tips.append("🚀 Keep maintaining your current habits. Focus on revision and practice tests.")

    return weaknesses, tips

# ---------- Factor Chart ----------
def draw_factor_chart(prev_score, attendance, study_hrs, sleep_hrs, arrears):
    factors = ['Prev Score', 'Attendance', 'Study Hrs\n(×10)', 'Sleep Hrs\n(×10)', 'Arrears\n(penalty)']
    values  = [
        min(prev_score, 100),
        min(attendance, 100),
        min(study_hrs * 10, 100),
        min(sleep_hrs * 10, 100),
        max(0, 100 - arrears * 20)
    ]
    colors = ['#667eea', '#11998e', '#f6d365', '#84fab0', '#fc5c7d']

    fig, ax = plt.subplots(figsize=(7, 3.5))
    fig.patch.set_facecolor('#f4f6fb')
    ax.set_facecolor('#f4f6fb')

    bars = ax.barh(factors, values, color=colors, height=0.5, edgecolor='none')
    for bar, val in zip(bars, values):
        ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height() / 2,
                f'{val:.0f}', va='center', fontsize=9, color='#2d3748', fontweight='600')

    ax.set_xlim(0, 115)
    ax.set_xlabel('Score (normalized to 100)', fontsize=9, color='#718096')
    ax.set_title('Key Factor Analysis', fontsize=12, fontweight='700', color='#1a1a2e', pad=10)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_color('#e2e8f0')
    ax.spines['left'].set_color('#e2e8f0')
    ax.tick_params(colors='#718096', labelsize=9)
    plt.tight_layout()
    return fig

# ---------- Grade Helper ----------
def get_grade(score):
    if score >= 90:   return "O",  "#276749", "Outstanding"
    elif score >= 80: return "A+", "#2b6cb0", "Excellent"
    elif score >= 70: return "A",  "#2b6cb0", "Very Good"
    elif score >= 60: return "B+", "#d69e2e", "Good"
    elif score >= 50: return "B",  "#d69e2e", "Average"
    else:             return "F",  "#c53030", "Needs Improvement"

# ---------- Main App ----------
def show_next_sem():

    st.markdown('<div class="page-title">🎓 Student Performance Predictor</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Fill in your details below to predict your next semester performance.</div>', unsafe_allow_html=True)

    clf_model, reg_model = load_models()

    if "predicted"  not in st.session_state: st.session_state.predicted = False
    if "score"      not in st.session_state: st.session_state.score     = 0
    if "status"     not in st.session_state: st.session_state.status    = ""
    if "inputs"     not in st.session_state: st.session_state.inputs    = {}

    # ---------- Form ----------
    st.markdown('<div class="section-title">📋 Student Details</div>', unsafe_allow_html=True)

    with st.form("prediction_form"):
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("**📊 Academic Info**")
            prev_score  = st.number_input("Previous Score",   0, 100, 75)
            attendance  = st.number_input("Attendance (%)",   0, 100, 90)
            arrears     = st.number_input("Arrears Count",    0,  10,  0)

        with col2:
            st.markdown("**⏰ Daily Habits**")
            study_hrs   = st.slider("Study Hours/Day",   0, 15, 5)
            sleep_hrs   = st.slider("Sleep Hours/Day",   0, 12, 7)
            travel_time = st.number_input("Travel Time (min)", 0, 120, 30)

        with col3:
            st.markdown("**🧠 Lifestyle**")
            stress       = st.selectbox("Stress Level",          ["Low", "Medium", "High"])
            social       = st.selectbox("Social Media Usage",    ["Low", "Medium", "High"])
            internet     = st.radio("Unlimited Internet?",       ["Yes", "No"])

        col4, col5 = st.columns(2)
        with col4:
            student_type = st.radio("Student Type",   ["Hosteller", "Day Scholar"])
        with col5:
            part_time    = st.radio("Part-time Job?", ["Yes", "No"])

        submit = st.form_submit_button("🔮 Predict My Performance")

    # ---------- Prediction ----------
    if submit:
        input_data = {
            "previous_score":            prev_score,
            "attendance":                attendance,
            "arrears_count":             arrears,
            "study_hours":               study_hrs,
            "sleep_hours":               sleep_hrs,
            "travel_time":               travel_time,
            "social_media_usage_Low":    1 if social == "Low"        else 0,
            "social_media_usage_Medium": 1 if social == "Medium"     else 0,
            "stress_level_Low":          1 if stress == "Low"        else 0,
            "stress_level_Medium":       1 if stress == "Medium"     else 0,
            "internet_access_Unlimited": 1 if internet == "Yes"      else 0,
            "student_type_Hosteller":    1 if student_type == "Hosteller" else 0,
            "part_time_job_Yes":         1 if part_time == "Yes"     else 0,
            "result_Pass":               1,
        }

        features    = np.array(list(input_data.values())).reshape(1, -1)
        status_pred = clf_model.predict(features)
        score_pred  = reg_model.predict(features)

        pred_score  = round(score_pred[0], 2)
        pred_status = "Pass" if status_pred[0] == 1 else "Fail"

        st.session_state.predicted = True
        st.session_state.score     = pred_score
        st.session_state.status    = pred_status
        st.session_state.inputs    = {
            "prev_score": prev_score, "attendance": attendance, "arrears": arrears,
            "study_hrs":  study_hrs,  "sleep_hrs":  sleep_hrs,  "travel_time": travel_time,
            "stress":     stress,     "social":     social,     "internet":    internet,
            "student_type": student_type, "part_time": part_time
        }

        insert_record({
            "previous_score": prev_score, "attendance":    attendance,  "arrears_count": arrears,
            "study_hours":    study_hrs,  "sleep_hours":   sleep_hrs,   "travel_time":   travel_time,
            "social_media":   social,     "stress_level":  stress,      "internet_access": internet,
            "student_type":   student_type, "part_time_job": part_time,
            "predicted_status": pred_status, "predicted_score": pred_score,
        })

    # ---------- Results ----------
    if st.session_state.predicted:
        pred_score  = st.session_state.score
        pred_status = st.session_state.status
        inp         = st.session_state.inputs
        grade, grade_color, grade_label = get_grade(pred_score)

        st.markdown("---")
        st.markdown('<div class="section-title">🎯 Prediction Results</div>', unsafe_allow_html=True)

        # Result boxes
        col1, col2, col3 = st.columns(3)
        with col1:
            status_class = "pass" if pred_status == "Pass" else "fail"
            status_icon  = "✅ Pass" if pred_status == "Pass" else "❌ Fail"
            st.markdown(f"""
            <div class="result-box">
                <div class="result-label">Predicted Status</div>
                <div class="result-value {status_class}">{status_icon}</div>
            </div>""", unsafe_allow_html=True)

        with col2:
            st.markdown(f"""
            <div class="result-box">
                <div class="result-label">Estimated Score</div>
                <div class="result-value score">{pred_score} / 100</div>
            </div>""", unsafe_allow_html=True)

        with col3:
            st.markdown(f"""
            <div class="result-box">
                <div class="result-label">Grade — {grade_label}</div>
                <div class="result-value grade">{grade}</div>
            </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Factor Chart
        st.markdown('<div class="section-title">📈 Key Factor Analysis</div>', unsafe_allow_html=True)
        fig_factors = draw_factor_chart(
            inp["prev_score"], inp["attendance"],
            inp["study_hrs"],  inp["sleep_hrs"], inp["arrears"]
        )
        st.pyplot(fig_factors)

        st.markdown("<br>", unsafe_allow_html=True)

        # Weakness + Tips
        weaknesses, tips = analyse_weaknesses(
            inp["prev_score"], inp["attendance"], inp["arrears"],
            inp["study_hrs"],  inp["sleep_hrs"],  inp["travel_time"],
            inp["stress"],     inp["social"],     inp["internet"],
            inp["student_type"], inp["part_time"]
        )

        col_w, col_t = st.columns(2)

        with col_w:
            st.markdown('<div class="section-title">⚠️ Weakness Analysis</div>', unsafe_allow_html=True)
            for w in weaknesses:
                st.markdown(f'<div class="weakness-card">{w}</div>', unsafe_allow_html=True)

        with col_t:
            st.markdown('<div class="section-title">💡 Personalized Study Tips</div>', unsafe_allow_html=True)
            for tip in tips:
                st.markdown(f'<div class="tip-card">{tip}</div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Model Performance
        if st.button("📊 View Model Performance"):
            st.markdown('<div class="section-title">🤖 About the Prediction Models</div>', unsafe_allow_html=True)

            st.markdown("""
            <div class="model-info-box">
                <b>How does the prediction work?</b><br>
                This system uses two separate Machine Learning models trained on real student data.
                One model predicts whether a student will <b>Pass or Fail</b> (Classification),
                and the other predicts the <b>estimated next semester mark</b> (Regression).
                Multiple algorithms were trained, evaluated, and compared — and the best performing
                one was selected for each task.
            </div>
            """, unsafe_allow_html=True)

            st.markdown("""
            <div class="model-info-box">
                <b>Regression Model — Predicts the next semester mark</b><br>
                Two regression algorithms were tested: <b>Linear Regression</b> and <b>Random Forest Regressor</b>.
                Both models achieved an R² score of <b>0.96</b>, meaning they explain 96% of the variation
                in student marks. However, <b>Linear Regression</b> achieved a slightly lower MAE of <b>5.07</b>
                compared to Random Forest's MAE of 5.20, meaning its predictions were on average closer to
                the actual marks. Lower MAE indicates better accuracy, so <b>Linear Regression</b> was
                selected as the final regression model.
            </div>
            """, unsafe_allow_html=True)

            st.markdown("""
            <div class="model-info-box">
                <b>Classification Model — Predicts Pass or Fail</b><br>
                Two classification algorithms were tested: <b>Logistic Regression</b> and <b>Random Forest Classifier</b>.
                Both models achieved identical results — an Accuracy of <b>0.95</b>, Precision of <b>0.94</b>,
                Recall of <b>0.96</b>, and F1-Score of <b>0.95</b>. Since both models perform equally well,
                either can be used. This confirms the dataset is well-structured and both algorithms
                are well-suited for this Pass/Fail prediction task.
            </div>
            """, unsafe_allow_html=True)

            col_m1, col_m2 = st.columns(2)

            # ── Regression Chart: MAE + R² grouped bar ──
            with col_m1:
                fig, ax = plt.subplots(figsize=(6, 4))
                fig.patch.set_facecolor('#f4f6fb')
                ax.set_facecolor('#f4f6fb')

                models   = ["Linear Regression", "Random Forest"]
                mae_vals = [5.07, 5.20]
                r2_vals  = [0.96, 0.96]

                x      = np.arange(len(models))
                width  = 0.35

                bars1 = ax.bar(x - width/2, mae_vals, width, label='MAE (lower is better)',
                               color=['#667eea', '#11998e'], edgecolor='none')
                bars2 = ax.bar(x + width/2, r2_vals,  width, label='R² Score (higher is better)',
                               color=['#a78bfa', '#6ee7b7'], edgecolor='none')

                for bar, val in zip(bars1, mae_vals):
                    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05,
                            f'{val}', ha='center', fontsize=9, fontweight='600', color='#2d3748')

                for bar, val in zip(bars2, r2_vals):
                    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05,
                            f'{val}', ha='center', fontsize=9, fontweight='600', color='#2d3748')

                ax.set_xticks(x)
                ax.set_xticklabels(models, fontsize=9, color='#444')
                ax.set_ylim(0, 7)
                ax.set_title("Regression Model Comparison\n(MAE & R² Score)",
                             fontweight='700', color='#1a1a2e', fontsize=10)
                ax.legend(fontsize=8)
                ax.spines['top'].set_visible(False)
                ax.spines['right'].set_visible(False)
                ax.tick_params(colors='#718096')
                plt.tight_layout()
                st.pyplot(fig)
                st.caption("Both models achieve R²=0.96. Linear Regression wins with lower MAE (5.07 vs 5.20) — selected as final model.")

            # ── Classification Chart: Accuracy, Precision, Recall, F1 grouped bar ──
            with col_m2:
                fig2, ax2 = plt.subplots(figsize=(6, 4))
                fig2.patch.set_facecolor('#f4f6fb')
                ax2.set_facecolor('#f4f6fb')

                metrics      = ['Accuracy', 'Precision', 'Recall', 'F1-Score']
                logistic_vals  = [0.95, 0.94, 0.96, 0.95]
                rf_vals        = [0.95, 0.94, 0.96, 0.95]

                x2     = np.arange(len(metrics))
                width2 = 0.35

                bars3 = ax2.bar(x2 - width2/2, logistic_vals, width2,
                                label='Logistic Regression', color='#f6d365', edgecolor='none')
                bars4 = ax2.bar(x2 + width2/2, rf_vals,       width2,
                                label='Random Forest',       color='#fc5c7d', edgecolor='none')

                for bar, val in zip(bars3, logistic_vals):
                    ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.003,
                             f'{val}', ha='center', fontsize=9, fontweight='600', color='#2d3748')

                for bar, val in zip(bars4, rf_vals):
                    ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.003,
                             f'{val}', ha='center', fontsize=9, fontweight='600', color='#2d3748')

                ax2.set_xticks(x2)
                ax2.set_xticklabels(metrics, fontsize=9, color='#444')
                ax2.set_ylim(0, 1.12)
                ax2.set_title("Classification Model Comparison\n(Accuracy, Precision, Recall, F1)",
                              fontweight='700', color='#1a1a2e', fontsize=10)
                ax2.legend(fontsize=8)
                ax2.spines['top'].set_visible(False)
                ax2.spines['right'].set_visible(False)
                ax2.tick_params(colors='#718096')
                plt.tight_layout()
                st.pyplot(fig2)
                st.caption("Both classifiers achieve identical scores across all metrics — both are equally reliable for Pass/Fail prediction.")

if __name__ == "__main__":
    show_next_sem()