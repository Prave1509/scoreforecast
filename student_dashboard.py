import streamlit as st
import numpy as np
import pandas as pd
import pickle
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import sqlite3
import os
from app import insert_prediction

# ---------- SQLite for student dashboard ----------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB2_PATH = os.path.join(BASE_DIR, "database", "student_history.db")


def init_db2():
    conn = sqlite3.connect(DB2_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS student_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sem1 REAL, sem2 REAL, sem3 REAL, sem4 REAL, sem5 REAL,
            attendance REAL, arrears REAL,
            study_hours REAL, sleep_hours REAL, travel_time REAL,
            social_media TEXT, stress_level TEXT, internet_access TEXT,
            residence TEXT, part_time_job TEXT,
            predicted_status TEXT, predicted_score REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    conn.close()


def insert_record2(data):
    conn = sqlite3.connect(DB2_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO student_records (
            sem1, sem2, sem3, sem4, sem5,
            attendance, arrears,
            study_hours, sleep_hours, travel_time,
            social_media, stress_level, internet_access,
            residence, part_time_job,
            predicted_status, predicted_score
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            data["sem1"],
            data["sem2"],
            data["sem3"],
            data["sem4"],
            data["sem5"],
            data["attendance"],
            data["arrears"],
            data["study_hours"],
            data["sleep_hours"],
            data["travel_time"],
            data["social_media"],
            data["stress_level"],
            data["internet_access"],
            data["residence"],
            data["part_time_job"],
            data["predicted_status"],
            data["predicted_score"],
        ),
    )
    conn.commit()
    conn.close()


def fetch_history2():
    if not os.path.exists(DB2_PATH):
        return pd.DataFrame()
    conn = sqlite3.connect(DB2_PATH)
    df = pd.read_sql_query(
        "SELECT * FROM student_records ORDER BY timestamp DESC", conn
    )
    conn.close()
    return df


# initializer run at import
init_db2()


# encapsulated page function


def show_final_sem():
    """Render the final semester prediction dashboard."""
    # navigation header
    # if st.button("⬅️ Back to Dashboard"):
    #   st.session_state.page = "student_dashboard"
    # rerun to apply new page state
    # st.rerun()

    # ==============================
    # Page Configuration
    # ==============================
    st.set_page_config(page_title="Student Performance Dashboard", layout="wide")
    st.title("📊 Student Performance Dashboard")

    # ==============================
    # Load Model
    # ==============================
    @st.cache_resource
    def load_model():
        model_path = os.path.join(BASE_DIR, "models", "final_sem_model.pkl")
        return pickle.load(open(model_path, "rb"))

    model = load_model()

    # ==============================
    # Prediction Function
    # ==============================
    def student_prediction(input_data):
        input_array = np.array(input_data).reshape(1, -1)
        predicted_percentage = model.predict(input_array)[0]
        status = "PASS" if predicted_percentage >= 40 else "FAIL"
        return round(predicted_percentage, 2), status

    # ==============================
    # Input Form
    # ==============================
    st.header("Enter Student Details")

    with st.form("student_form"):
        st.subheader("📘 Academic Details")
        sem1 = st.number_input("Semester 1 Marks")
        sem2 = st.number_input("Semester 2 Marks")
        sem3 = st.number_input("Semester 3 Marks")
        sem4 = st.number_input("Semester 4 Marks")
        sem5 = st.number_input("Semester 5 Marks")

        attendance = st.number_input("Attendance (%)")
        arrears = st.number_input("Number of Arrears")

        st.subheader("📗 Lifestyle Details")
        study_hours = st.number_input("Study Hours per Day")
        sleep_hours = st.number_input("Sleep Hours per Day")
        travel_time = st.number_input("Travel Time (Minutes)")

        social_media = st.selectbox("Social Media Usage", ["Low", "Medium", "High"])
        stress_level = st.selectbox("Stress Level", ["Low", "Medium", "High"])
        internet_access = st.selectbox("Internet Access", ["Limited", "Unlimited"])
        residence = st.selectbox("Residence", ["Day Scholar", "Hosteller"])
        part_time_job = st.selectbox("Part-Time Job", ["No", "Yes"])

        submitted = st.form_submit_button("Analyze")

    # ==============================
    # Prediction + Analysis
    # ==============================
    if submitted:
        model_input = [
            sem1,
            sem2,
            sem3,
            sem4,
            sem5,
            attendance,
            arrears,
            study_hours,
            sleep_hours,
            travel_time,
            1 if social_media == "Low" else 0,
            1 if social_media == "Medium" else 0,
            1 if social_media == "High" else 0,
            1 if stress_level == "Low" else 0,
            1 if stress_level == "Medium" else 0,
            1 if stress_level == "High" else 0,
            1 if internet_access == "Limited" else 0,
            1 if internet_access == "Unlimited" else 0,
            1 if residence == "Day Scholar" else 0,
            1 if residence == "Hosteller" else 0,
            1 if part_time_job == "No" else 0,
            1 if part_time_job == "Yes" else 0,
        ]

        predicted_marks, status = student_prediction(model_input)

        rec = {
            "sem1": sem1,
            "sem2": sem2,
            "sem3": sem3,
            "sem4": sem4,
            "sem5": sem5,
            "attendance": attendance,
            "arrears": arrears,
            "study_hours": study_hours,
            "sleep_hours": sleep_hours,
            "travel_time": travel_time,
            "social_media": social_media,
            "stress_level": stress_level,
            "internet_access": internet_access,
            "residence": residence,
            "part_time_job": part_time_job,
            "predicted_status": status,
            "predicted_score": predicted_marks,
        }

        insert_record2(rec)
        # also insert into central predictions table (admin view)
        try:
            params = st.experimental_get_query_params()
            sid = params.get("student_id", [None])[0]
            insert_prediction("student", sid, predicted_marks, status)
        except Exception:
            pass  # if central DB not available don't crash

        st.success("Prediction saved securely in database.")

        # ==============================
        # Prediction Result
        # ==============================
        st.subheader("🎯 Predicted Final Percentage")
        st.metric("Predicted Score", f"{predicted_marks:.2f}%")

        if status == "PASS":
            st.success("Status: PASS ✅")
        else:
            st.error("Status: FAIL ❌")

        # ==============================
        # ⭐ Performance Rating
        # ==============================
        if predicted_marks >= 90:
            rating = "⭐⭐⭐⭐⭐"
            level = "Excellent"
        elif predicted_marks >= 75:
            rating = "⭐⭐⭐⭐"
            level = "Very Good"
        elif predicted_marks >= 60:
            rating = "⭐⭐⭐"
            level = "Good"
        elif predicted_marks >= 50:
            rating = "⭐⭐"
            level = "Average"
        else:
            rating = "⭐"
            level = "Needs Improvement"

        st.subheader("⭐ Student Performance Rating")

        col1, col2 = st.columns(2)

        with col1:
            st.metric("Performance Level", level)

        with col2:
            st.metric("Rating", rating)

        # ==============================
        # Progress Bar
        # ==============================
        st.subheader("📊 Performance Score")
        st.progress(predicted_marks / 100)

        # ==============================
        # Semester Chart
        # ==============================
        st.subheader("📈 Semester-wise Performance")

        semesters = ["Sem1", "Sem2", "Sem3", "Sem4", "Sem5"]
        marks = [sem1, sem2, sem3, sem4, sem5]

        fig, ax = plt.subplots()
        ax.bar(semesters, marks)
        ax.set_ylim(0, 100)

        for i, v in enumerate(marks):
            ax.text(i, v + 1, str(v), ha="center")

        st.pyplot(fig)

        # ==============================
        # Attendance Chart
        # ==============================
        st.subheader("📊 Attendance Analysis")

        fig2, ax2 = plt.subplots()
        ax2.bar(["Your Attendance", "Ideal (75%)"], [attendance, 75])
        ax2.set_ylim(0, 100)

        st.pyplot(fig2)

        # ==============================
        # Lifestyle Metrics
        # ==============================
        st.subheader("⏱ Lifestyle Metrics")

        categories = ["Study Hours", "Sleep Hours", "Travel Time"]
        values = [study_hours, sleep_hours, travel_time]

        fig3, ax3 = plt.subplots()
        ax3.bar(categories, values)

        st.pyplot(fig3)

        # ==============================
        # Radar Chart
        # ==============================
        st.subheader("📌 Strength Radar")

        avg_marks = sum(marks) / len(marks)

        radar_values = [
            avg_marks,
            attendance,
            study_hours * 10,
            sleep_hours * 10,
            max(0, 60 - travel_time),
        ]

        radar_categories = [
            "Average Marks",
            "Attendance",
            "Study Hours",
            "Sleep Hours",
            "Travel Efficiency",
        ]

        fig4 = go.Figure()

        fig4.add_trace(
            go.Scatterpolar(r=radar_values, theta=radar_categories, fill="toself")
        )

        fig4.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100])), showlegend=False
        )

        st.plotly_chart(fig4, use_container_width=True)

        # ==============================
        # Suggestions
        # ==============================
        st.subheader("💡 Suggestions to Improve")

        if avg_marks < 75:
            st.write("- Focus more on weak subjects.")

        if study_hours < 5:
            st.write("- Increase study hours daily.")

        if attendance < 85:
            st.write("- Improve attendance consistency.")

        if social_media == "High":
            st.write("- Reduce social media usage.")

        if stress_level == "High":
            st.write("- Practice stress management techniques.")

        if sleep_hours < 7 or sleep_hours > 8:
            st.write("- Maintain 7-8 hours sleep.")

        if travel_time > 60:
            st.write("- Optimize travel time if possible.")

        st.success("✅ Analysis Complete! Keep Improving!")


# allow standalone execution
if __name__ == "__main__":
    show_final_sem()
