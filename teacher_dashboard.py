import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import plotly.graph_objects as go
import pickle
import sqlite3
import os
from app import insert_prediction

# ---------- SQLite for teacher dashboard ----------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB3_PATH = os.path.join(BASE_DIR, "database", "teacher_dashboard.db")


def init_db3():
    conn = sqlite3.connect(DB3_PATH)
    cur = conn.cursor()
    # uploads table
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS uploads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            total_students INTEGER,
            avg_marks REAL,
            avg_attendance REAL,
            total_arrears INTEGER,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    # individual predictions table
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS student_predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_index INTEGER,
            predicted_mark REAL,
            result TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    conn.close()


def log_upload(filename, total, avg_m, avg_att, total_ar):
    conn = sqlite3.connect(DB3_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO uploads (filename, total_students, avg_marks, avg_attendance, total_arrears)
        VALUES (?,?,?,?,?)
        """,
        (filename, total, avg_m, avg_att, total_ar),
    )
    conn.commit()
    conn.close()


def log_prediction(idx, mark, result):
    conn = sqlite3.connect(DB3_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO student_predictions (student_index, predicted_mark, result)
        VALUES (?,?,?)
        """,
        (idx, mark, result),
    )
    conn.commit()
    conn.close()
    # also log to central predictions table for admin visibility
    try:
        insert_prediction("teacher", idx, mark, result)
    except Exception:
        pass


def fetch_uploads():
    if not os.path.exists(DB3_PATH):
        return pd.DataFrame()
    conn = sqlite3.connect(DB3_PATH)
    df = pd.read_sql_query("SELECT * FROM uploads ORDER BY timestamp DESC", conn)
    conn.close()
    return df


def fetch_teach_preds():
    if not os.path.exists(DB3_PATH):
        return pd.DataFrame()
    conn = sqlite3.connect(DB3_PATH)
    df = pd.read_sql_query(
        "SELECT * FROM student_predictions ORDER BY timestamp DESC", conn
    )
    conn.close()
    return df


# initialize database
init_db3()


def show_teacher_dashboard():
    """Render the teacher dashboard including upload and predictions."""
    # ======================================
    # Page Config
    # ======================================
    st.set_page_config(page_title="SMART Teacher Dashboard", layout="wide")
    st.title("👩‍🏫  Teacher Dashboard: Class Performance + Prediction")

    # ======================================
    # Load ML Model
    # ======================================
    @st.cache_resource
    def load_model():
        model_path = os.path.join(BASE_DIR, "models", "final_sem_model.pkl")
        with open(model_path, "rb") as file:
            model = pickle.load(file)
        return model

    model = load_model()

    # ======================================
    # Upload Dataset
    # ======================================
    # Expected column order
    expected_columns = [
        "sem1",
        "sem2",
        "sem3",
        "sem4",
        "sem5",
        "attendance",
        "arrears_count",
        "study_hours",
        "sleep_hours",
        "social_media",
        "stress_level",
        "internet_access",
        "residence",
        "travel_time",
        "part_time_job",
        "final_percentage",
    ]

    st.title("📤 Upload Student Dataset")

    uploaded_file = st.file_uploader("Upload CSV or Excel file", type=["csv", "xlsx"])

    if uploaded_file:

        # Read file
        try:
            if uploaded_file.name.endswith(".csv"):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
        except Exception as e:
            st.error(f"Error reading file: {e}")
            st.stop()

        # Check columns
        uploaded_columns = list(df.columns)

        if uploaded_columns == expected_columns:
            st.success("✅ Dataset columns are correct and in proper order.")
            st.dataframe(df.head())
        else:
            st.warning("⚠ Dataset columns are incorrect or out of order!")
            st.write("Expected columns (in order):")
            st.write(expected_columns)
            st.write("Your dataset columns:")
            st.write(uploaded_columns)
            missing_cols = [
                col for col in expected_columns if col not in uploaded_columns
            ]
            if missing_cols:
                st.error(f"Missing columns: {missing_cols}")

        # ======================================
        # Required Columns
        # ======================================
        required_columns = [
            "sem1",
            "sem2",
            "sem3",
            "sem4",
            "sem5",
            "attendance",
            "arrears_count",
            "study_hours",
            "sleep_hours",
            "travel_time",
            "social_media",
            "stress_level",
            "internet_access",
            "residence",
            "part_time_job",
        ]

        missing_cols = [col for col in required_columns if col not in df.columns]

        if missing_cols:
            st.error(f"Missing columns in dataset: {missing_cols}")
            st.stop()

        # ======================================
        # Sidebar Filters
        # ======================================
        st.sidebar.header("🔎 Filter Students")
        min_attendance = st.sidebar.slider("Minimum Attendance", 0, 100, 0)
        max_arrears = st.sidebar.slider("Maximum Arrears", 0, 20, 20)

        filtered_df = df[
            (df["attendance"] >= min_attendance) & (df["arrears_count"] <= max_arrears)
        ].copy()

        # ======================================
        # Encode Categorical Columns (Fix ML Error)
        # ======================================
        categorical_columns = [
            "social_media",
            "stress_level",
            "internet_access",
            "residence",
            "part_time_job",
        ]

        for col in categorical_columns:
            filtered_df[col] = filtered_df[col].astype("category").cat.codes

        # ======================================
        # Derived Columns
        # ======================================
        filtered_df["avg_marks"] = filtered_df[
            ["sem1", "sem2", "sem3", "sem4", "sem5"]
        ].mean(axis=1)
        filtered_df["result"] = filtered_df["avg_marks"].apply(
            lambda x: "PASS" if x >= 40 else "FAIL"
        )

        # ======================================
        # Class Overview
        # ======================================
        st.header("📊 Class Overview Metrics")

        total_students = filtered_df.shape[0]
        avg_marks = filtered_df["avg_marks"].mean()
        avg_attendance = filtered_df["attendance"].mean()
        total_arrears = filtered_df["arrears_count"].sum()

        # log upload to database
        log_upload(
            uploaded_file.name if hasattr(uploaded_file, "name") else "uploaded_csv",
            total_students,
            avg_marks,
            avg_attendance,
            total_arrears,
        )

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Students", total_students)
        col2.metric("Average Marks", f"{avg_marks:.2f}")
        col3.metric("Average Attendance (%)", f"{avg_attendance:.2f}")
        col4.metric("Total Arrears", total_arrears)

        # ======================================
        # Pass vs Fail
        # ======================================
        st.subheader("🎓 Pass vs Fail Distribution")
        st.bar_chart(filtered_df["result"].value_counts())

        # ======================================
        # Semester Average
        # ======================================
        st.subheader("📈 Average Marks per Semester")
        semesters = ["sem1", "sem2", "sem3", "sem4", "sem5"]
        avg_sem_marks = filtered_df[semesters].mean()

        fig1, ax1 = plt.subplots()
        ax1.bar(semesters, avg_sem_marks)
        ax1.set_ylim(0, 100)
        ax1.set_ylabel("Average Marks")
        st.pyplot(fig1)

        # ======================================
        # Attendance Distribution
        # ======================================
        st.subheader("📊 Attendance Distribution")
        fig2, ax2 = plt.subplots()
        ax2.hist(filtered_df["attendance"], bins=10)
        ax2.set_xlabel("Attendance (%)")
        ax2.set_ylabel("Number of Students")
        st.pyplot(fig2)

        # ======================================
        # Top Performers
        # ======================================
        st.subheader("🏆 Top 5 Performers")
        top_students = filtered_df.sort_values("avg_marks", ascending=False).head(5)
        st.dataframe(top_students)

        # show upload history
        with st.expander("📁 Upload History"):
            uploads_df = fetch_uploads()
            if uploads_df.empty:
                st.write("No upload records yet.")
            else:
                st.dataframe(uploads_df)

        # ======================================
        # At-Risk / Danger Students
        # ======================================
        st.subheader("⚠ Students in Danger Zone")

    if uploaded_file:
        danger_students = filtered_df[
            (filtered_df["avg_marks"] < 50)
            | (filtered_df["attendance"] < 75)
            | (filtered_df["arrears_count"] > 2)
        ]

        if danger_students.empty:
            st.success("🎉 No students in danger zone!")
        else:
            st.error(f"{danger_students.shape[0]} Students Need Attention")
            st.dataframe(danger_students)

        # ======================================
        # Individual Student Analysis
        # ======================================
        st.header("🔍 Individual Student Analysis")

        student_ids = filtered_df.index.tolist()
        selected_idx = st.selectbox("Select Student by Row Number", student_ids)

        student = filtered_df.loc[selected_idx]

        st.subheader(f"Student #{selected_idx} Performance")

        # Semester Chart
        marks = [
            student["sem1"],
            student["sem2"],
            student["sem3"],
            student["sem4"],
            student["sem5"],
        ]

        fig3, ax3 = plt.subplots()
        ax3.bar(["Sem1", "Sem2", "Sem3", "Sem4", "Sem5"], marks)
        ax3.set_ylim(0, 100)
        ax3.set_ylabel("Marks")
        st.pyplot(fig3)

        # ======================================
        # Radar Chart
        # ======================================
        st.subheader("📌 Student Strength Radar")

        radar_values = [
            student["avg_marks"],
            student["attendance"],
            student["study_hours"] * 10,
            student["sleep_hours"] * 10,
            max(0, 60 - student["travel_time"]),
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

        # ======================================
        # AI Prediction Section
        # ======================================
        # ======================================
        # AI Prediction Section (FIXED - 22 FEATURES)
        # ======================================
        st.header("🤖  Final Mark Prediction")

        if st.button("Predict Final Mark for Selected Student"):

            model_input = [
                # 10 Numeric
                student["sem1"],
                student["sem2"],
                student["sem3"],
                student["sem4"],
                student["sem5"],
                student["attendance"],
                student["arrears_count"],
                student["study_hours"],
                student["sleep_hours"],
                student["travel_time"],
                # Social Media (3)
                1 if student["social_media"] == "Low" else 0,
                1 if student["social_media"] == "Medium" else 0,
                1 if student["social_media"] == "High" else 0,
                # Stress Level (3)
                1 if student["stress_level"] == "Low" else 0,
                1 if student["stress_level"] == "Medium" else 0,
                1 if student["stress_level"] == "High" else 0,
                # Internet (2)
                1 if student["internet_access"] == "Limited" else 0,
                1 if student["internet_access"] == "Unlimited" else 0,
                # Residence (2)
                1 if student["residence"] == "Day Scholar" else 0,
                1 if student["residence"] == "Hosteller" else 0,
                # Part Time Job (2)
                1 if student["part_time_job"] == "No" else 0,
                1 if student["part_time_job"] == "Yes" else 0,
            ]

            input_array = np.array(model_input).reshape(1, -1)

            prediction = model.predict(input_array)
            predicted_mark = round(prediction[0], 2)

            # update prediction record with actual values
            # (using simple strategy: update previous row) - SQLite doesn't allow easy returning id, so we'll insert fresh instead
            log_prediction(
                selected_idx, predicted_mark, "PASS" if predicted_mark >= 40 else "FAIL"
            )

            st.success(f"🎯 Predicted Final Mark: {predicted_mark}")

            if predicted_mark >= 40:
                st.success("✅ Predicted Result: PASS")
            else:
                st.error("❌ Predicted Result: FAIL")

            # show prediction log
            with st.expander("📝 Prediction History"):
                preds_df = fetch_teach_preds()
                if preds_df.empty:
                    st.write("No predictions logged yet.")
                else:
                    st.dataframe(preds_df)

            # ======================================
            # Suggestions
            # ======================================
            st.subheader("💡 Suggestions")

            if student["avg_marks"] < 75:
                st.write("- Focus on weaker subjects.")
            if student["study_hours"] < 5:
                st.write("- Increase daily study hours.")
            if student["attendance"] < 85:
                st.write("- Improve attendance.")
            if student["sleep_hours"] < 7 or student["sleep_hours"] > 8:
                st.write("- Maintain proper sleep hours.")
            if student["travel_time"] > 60:
                st.write("- Optimize travel time.")


# standalone
if __name__ == "__main__":
    show_teacher_dashboard()
