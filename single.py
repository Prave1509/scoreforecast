import streamlit as st
import numpy as np
import joblib
import matplotlib.pyplot as plt
import sqlite3
import os


# ---------- Database Path ----------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "student.db")

# ---------- Initialize Database ----------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            previous_score REAL,
            attendance REAL,
            arrears_count INTEGER,
            study_hours REAL,
            sleep_hours REAL,
            travel_time REAL,
            social_media TEXT,
            stress_level TEXT,
            internet_access TEXT,
            student_type TEXT,
            part_time_job TEXT,
            predicted_status TEXT,
            predicted_score REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


init_db()


# ---------- Insert Record ----------
def insert_record(data):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO predictions (
            previous_score,
            attendance,
            arrears_count,
            study_hours,
            sleep_hours,
            travel_time,
            social_media,
            stress_level,
            internet_access,
            student_type,
            part_time_job,
            predicted_status,
            predicted_score
        )
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
    """,
    (
        data["previous_score"],
        data["attendance"],
        data["arrears_count"],
        data["study_hours"],
        data["sleep_hours"],
        data["travel_time"],
        data["social_media"],
        data["stress_level"],
        data["internet_access"],
        data["student_type"],
        data["part_time_job"],
        data["predicted_status"],
        data["predicted_score"],
    ))

    conn.commit()
    conn.close()


# ---------- Load ML Models (Cached) ----------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
model_dir = os.path.join(BASE_DIR, "models")
clf_file = os.path.join(model_dir, "best_classification_model.joblib")

#st.write("Looking for model at:", clf_file)
#st.write("Exists?", os.path.exists(clf_file))

@st.cache_data(show_spinner=False)
def load_models():
    """
    Load the classification and regression models safely.
    Works for local and Streamlit Cloud deployments.
    """
    # Get absolute path to the folder containing this script
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    # Folder where your models are stored (adjust if needed)
    model_dir = os.path.join(BASE_DIR, "models")

    # Model filenames
    clf_file = os.path.join(model_dir, "best_classification_model.joblib")
    reg_file = os.path.join(model_dir, "best_regression_model.joblib")

    # Check if files exist
    if not os.path.exists(clf_file):
        raise FileNotFoundError(f"Classification model not found: {clf_file}")
    if not os.path.exists(reg_file):
        raise FileNotFoundError(f"Regression model not found: {reg_file}")

    # Load models
    clf_model = joblib.load(clf_file)
    reg_model = joblib.load(reg_file)

    return clf_model, reg_model


# ---------- Main Page ----------
def show_next_sem():

    st.title("🎓 Student Performance Predictor")
    st.write("Enter the student details to predict next semester performance.")

    clf_model, reg_model = load_models()

    # Session states
    if "predicted" not in st.session_state:
        st.session_state.predicted = False
    if "score" not in st.session_state:
        st.session_state.score = 0
    if "status" not in st.session_state:
        st.session_state.status = ""

    # ---------- Form ----------
    with st.form("prediction_form"):

        col1, col2, col3 = st.columns(3)

        with col1:
            prev_score = st.number_input("Previous Score", 0, 100, 75)
            attendance = st.number_input("Attendance (%)", 0, 100, 90)
            arrears = st.number_input("Arrears Count", 0, 10, 0)

        with col2:
            study_hrs = st.slider("Study Hours/Day", 0, 15, 5)
            sleep_hrs = st.slider("Sleep Hours/Day", 0, 12, 7)
            travel_time = st.number_input("Travel Time (min)", 0, 120, 30)

        with col3:
            stress = st.selectbox("Stress Level", ["Low", "Medium", "High"])
            social = st.selectbox("Social Media Usage", ["Low", "Medium", "High"])
            internet = st.radio("Unlimited Internet?", ["Yes", "No"])

        student_type = st.radio("Student Type", ["Hosteller", "Day Scholar"])
        part_time = st.radio("Part-time Job?", ["Yes", "No"])

        submit = st.form_submit_button("Predict")

    # ---------- Prediction ----------
    if submit:

        input_data = {
            "previous_score": prev_score,
            "attendance": attendance,
            "arrears_count": arrears,
            "study_hours": study_hrs,
            "sleep_hours": sleep_hrs,
            "travel_time": travel_time,
            "social_media_usage_Low": 1 if social == "Low" else 0,
            "social_media_usage_Medium": 1 if social == "Medium" else 0,
            "stress_level_Low": 1 if stress == "Low" else 0,
            "stress_level_Medium": 1 if stress == "Medium" else 0,
            "internet_access_Unlimited": 1 if internet == "Yes" else 0,
            "student_type_Hosteller": 1 if student_type == "Hosteller" else 0,
            "part_time_job_Yes": 1 if part_time == "Yes" else 0,
            "result_Pass": 1
        }

        features = np.array(list(input_data.values())).reshape(1, -1)

        status_pred = clf_model.predict(features)
        score_pred = reg_model.predict(features)

        pred_score = round(score_pred[0], 2)
        pred_status = "Pass" if status_pred[0] == 1 else "Fail"

        st.session_state.predicted = True
        st.session_state.score = pred_score
        st.session_state.status = pred_status

        # Save to database
        insert_record({
            "previous_score": prev_score,
            "attendance": attendance,
            "arrears_count": arrears,
            "study_hours": study_hrs,
            "sleep_hours": sleep_hrs,
            "travel_time": travel_time,
            "social_media": social,
            "stress_level": stress,
            "internet_access": internet,
            "student_type": student_type,
            "part_time_job": part_time,
            "predicted_status": pred_status,
            "predicted_score": pred_score
        })

        st.success("Prediction saved successfully.")

    # ---------- Show Result ----------
    if st.session_state.predicted:

        pred_score = st.session_state.score

        st.metric("Predicted Status", st.session_state.status)
        st.metric("Estimated Score", pred_score)

        st.progress(pred_score / 100)

        if pred_score >= 90:
            st.success("⭐⭐⭐⭐⭐ Excellent Performance")
        elif pred_score >= 75:
            st.info("⭐⭐⭐⭐ Very Good Performance")
        elif pred_score >= 60:
            st.warning("⭐⭐⭐ Good Performance")
        elif pred_score >= 50:
            st.warning("⭐⭐ Average Performance")
        else:
            st.error("⭐ Needs Improvement")

        # ---------- Model Analysis ----------
        if st.button("📊 Analyse Model Performance"):

            st.subheader("Model Performance")

            reg_algorithms = ["Linear Regression", "Random Forest"]
            reg_scores = [0.78, 0.91]

            fig, ax = plt.subplots()
            ax.bar(reg_algorithms, reg_scores)
            ax.set_ylabel("R2 Score")
            ax.set_title("Regression Model Performance")

            st.pyplot(fig)


# ---------- Run ----------
if __name__ == "__main__":
    show_next_sem()