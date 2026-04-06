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
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS uploads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            total_students INTEGER,
            avg_marks REAL,
            avg_attendance REAL,
            total_arrears INTEGER,
            pass_count INTEGER,
            fail_count INTEGER,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
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


def log_upload(filename, total, avg_m, avg_att, total_ar, pass_count, fail_count):
    conn = sqlite3.connect(DB3_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO uploads (filename, total_students, avg_marks, avg_attendance, total_arrears, pass_count, fail_count)
        VALUES (?,?,?,?,?,?,?)
        """,
        (filename, total, avg_m, avg_att, total_ar, pass_count, fail_count),
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


# ======================================
# Column Mapping Logic (Background)
# ======================================

# All known aliases for each expected feature
COLUMN_ALIASES = {
    "sem1": ["sem1", "semester1", "semester 1", "s1", "mark1", "m1", "marks1", "sem_1", "semester_1"],
    "sem2": ["sem2", "semester2", "semester 2", "s2", "mark2", "m2", "marks2", "sem_2", "semester_2"],
    "sem3": ["sem3", "semester3", "semester 3", "s3", "mark3", "m3", "marks3", "sem_3", "semester_3"],
    "sem4": ["sem4", "semester4", "semester 4", "s4", "mark4", "m4", "marks4", "sem_4", "semester_4"],
    "sem5": ["sem5", "semester5", "semester 5", "s5", "mark5", "m5", "marks5", "sem_5", "semester_5"],
    "attendance": ["attendance", "attend", "att", "attendance_%", "attendance_percent"],
    "arrears_count": ["arrears_count", "arrears", "arrear", "backlogs", "backlog", "arrears count"],
    "study_hours": ["study_hours", "study hours", "studyhours", "study_hr", "study_time"],
    "sleep_hours": ["sleep_hours", "sleep hours", "sleephours", "sleep_hr", "sleep_time"],
    "social_media": ["social_media", "social media", "socialmedia", "social_media_usage", "social"],
    "stress_level": ["stress_level", "stress level", "stresslevel", "stress"],
    "internet_access": ["internet_access", "internet access", "internetaccess", "internet", "net_access"],
    "residence": ["residence", "resident", "day_scholar_hosteller", "living", "stay"],
    "travel_time": ["travel_time", "travel time", "traveltime", "travel_hr", "commute_time", "commute"],
    "part_time_job": ["part_time_job", "part time job", "parttimejob", "parttime", "part_time", "job"],
    
}


def normalize(col):
    """Lowercase and strip a column name for comparison."""
    return col.strip().lower()


def map_columns(df_columns):
    """
    Try to map uploaded column names to expected feature names.
    Returns:
        mapping: dict {original_col: expected_col} for matched columns
        unmapped: list of original columns that couldn't be matched
        unmatched_expected: list of expected columns not found
    """
    normalized_uploaded = {normalize(c): c for c in df_columns}
    mapping = {}
    matched_expected = set()

    for expected, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if normalize(alias) in normalized_uploaded:
                original_col = normalized_uploaded[normalize(alias)]
                mapping[original_col] = expected
                matched_expected.add(expected)
                break

    unmapped = [c for c in df_columns if c not in mapping]
    unmatched_expected = [e for e in COLUMN_ALIASES.keys() if e not in matched_expected]

    return mapping, unmapped, unmatched_expected


def check_column_order(df, expected_columns):
    """
    After mapping, check if the columns are in the correct expected order.
    Returns True if order is correct, False otherwise.
    """
    mapped_cols = [df.columns.tolist()[i] for i in range(len(df.columns)) if df.columns[i] in expected_columns]
    actual_order = [c for c in df.columns if c in expected_columns]
    return actual_order == expected_columns


# initialize database
init_db3()


def show_teacher_dashboard():
    """Render the teacher dashboard including upload and predictions."""
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
    # Expected column order
    # ======================================
    expected_columns = [
        "sem1", "sem2", "sem3", "sem4", "sem5",
        "attendance", "arrears_count", "study_hours", "sleep_hours",
        "social_media", "stress_level", "internet_access",
        "residence", "travel_time", "part_time_job", 
    ]

    st.title("📤 Upload Student Dataset")

    # Show expected format to teacher before upload
    with st.expander("📋 Expected Dataset Format (click to view)"):
        st.info("Your dataset columns should be in this exact order:")
        order_df = pd.DataFrame(
            {
                "Column #": list(range(1, len(expected_columns) + 1)),
                "Expected Column Name": expected_columns,
                "Example Aliases Accepted": [
                    "s1, semester1, mark1, m1",
                    "s2, semester2, mark2, m2",
                    "s3, semester3, mark3, m3",
                    "s4, semester4, mark4, m4",
                    "s5, semester5, mark5, m5",
                    "attend, att",
                    "arrears, backlogs",
                    "study hours, studyhours",
                    "sleep hours, sleephours",
                    "social media, socialmedia",
                    "stress level, stresslevel",
                    "internet, net_access",
                    "resident, living",
                    "travel time, commute",
                    "part time job, parttime",
                    
                ],
            }
        )
        st.dataframe(order_df, use_container_width=True)

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

        uploaded_columns = list(df.columns)

        # ======================================
        # Step 1: Background Column Mapping
        # ======================================
        mapping, unmapped, unmatched_expected = map_columns(uploaded_columns)

        # If there are columns we couldn't map at all
        if unmatched_expected:
            st.error("❌ We could not recognize some required columns in your dataset.")
            st.markdown(
                "Please **rename the unrecognized columns** in your file to one of the accepted names below, then re-upload."
            )

            for col in unmatched_expected:
                aliases = COLUMN_ALIASES[col]
                # Find which uploaded columns were unrecognized (raw names not in any alias list)
                unrecognized_raw = [c for c in unmapped if c not in [a for aliases_list in COLUMN_ALIASES.values() for a in aliases_list]]
                accepted_str = " / ".join([f"`{a}`" for a in aliases])
                st.markdown(f"**Missing:** `{col}` — accepted column names: {accepted_str}")

            st.info(
                "💡 For example, if your file has a column named `travel time` "
                "it will be automatically recognized. But if it says `commute_hours` "
                "we cannot match it — please rename it to one of the accepted names shown above."
            )

            with st.expander("📋 View full accepted column names list"):
                alias_rows = []
                for exp_col, aliases in COLUMN_ALIASES.items():
                    alias_rows.append({
                        "Required Column": exp_col,
                        "Accepted Names (any of these)": " / ".join(aliases),
                    })
                st.dataframe(pd.DataFrame(alias_rows), use_container_width=True)

            st.stop()

        # Rename columns to expected names using the mapping
        df = df.rename(columns=mapping)

        # ======================================
        # Step 2: Check Column ORDER
        # ======================================
        # Get the order of expected columns as they appear in the renamed df
        present_expected = [c for c in df.columns if c in expected_columns]
        correct_order = expected_columns  # only the 16 expected ones

        if present_expected != correct_order:
            st.error("❌ Your dataset columns are not in the correct order!")
            st.markdown(
                "**Please rearrange your dataset columns in the following order before uploading:**"
            )
            order_table = pd.DataFrame(
                {
                    "Position": list(range(1, len(expected_columns) + 1)),
                    "Required Column": expected_columns,
                }
            )
            st.table(order_table)

            # Show what was detected vs what was expected
            st.markdown("**Your current column order (after mapping):**")
            current_order_display = pd.DataFrame(
                {
                    "Your Position": list(range(1, len(present_expected) + 1)),
                    "Your Column (mapped)": present_expected,
                    "Expected at this position": expected_columns[:len(present_expected)],
                    "Match ✅/❌": [
                        "✅" if present_expected[i] == expected_columns[i] else "❌"
                        for i in range(len(present_expected))
                    ],
                }
            )
            st.dataframe(current_order_display, use_container_width=True)
            st.stop()

        # All good — distinguish exact match vs alias match
        auto_mapped = {orig: exp for orig, exp in mapping.items() if orig != exp}

        if not auto_mapped:
            st.success("✅ Perfect! All column names match exactly. Your dataset is ready for analysis.")
        else:
            st.success("✅ All columns recognized! Some column names were automatically mapped.")
            with st.expander("🔄 View auto-mapped columns (click to expand)"):
                st.info(
                    "The following columns were recognized by their alternate names and mapped "
                    "automatically — no action needed from you:"
                )
                mapped_rows = [{"Your Column Name": orig, "Mapped To": exp} for orig, exp in auto_mapped.items()]
                st.table(pd.DataFrame(mapped_rows))

        st.dataframe(df.head())

        # ======================================
        # Required Columns Check
        # ======================================
        required_columns = [
            "sem1", "sem2", "sem3", "sem4", "sem5",
            "attendance", "arrears_count", "study_hours", "sleep_hours",
            "travel_time", "social_media", "stress_level",
            "internet_access", "residence", "part_time_job",
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
        # Encode Categorical Columns
        # ======================================
        categorical_columns = [
            "social_media", "stress_level", "internet_access", "residence", "part_time_job",
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
        # Class Overview Metrics
        # ======================================
        st.header("📊 Class Overview Metrics")

        total_students = filtered_df.shape[0]
        avg_marks = filtered_df["avg_marks"].mean()
        avg_attendance = filtered_df["attendance"].mean()
        total_arrears = int(filtered_df["arrears_count"].sum())
        pass_count = int((filtered_df["result"] == "PASS").sum())
        fail_count = int((filtered_df["result"] == "FAIL").sum())

        # Log upload with pass/fail counts
        log_upload(
            uploaded_file.name if hasattr(uploaded_file, "name") else "uploaded_csv",
            total_students,
            avg_marks,
            avg_attendance,
            total_arrears,
            pass_count,
            fail_count,
        )

        # Display metrics in order: Total Students | Avg Marks | Avg Attendance | Arrears | Pass | Fail
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        col1.metric("👥 Total Students", total_students)
        col2.metric("📝 Average Marks", f"{avg_marks:.2f}")
        col3.metric("📅 Avg Attendance (%)", f"{avg_attendance:.2f}")
        col4.metric("⚠ Total Arrears", total_arrears)
        col5.metric("✅ Pass Count", pass_count)
        col6.metric("❌ Fail Count", fail_count)

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

        marks = [
            student["sem1"], student["sem2"], student["sem3"],
            student["sem4"], student["sem5"],
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
            "Average Marks", "Attendance", "Study Hours",
            "Sleep Hours", "Travel Efficiency",
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
        st.header("🤖  Final Mark Prediction")

        if st.button("Predict Final Mark for Selected Student"):

            model_input = [
                student["sem1"], student["sem2"], student["sem3"],
                student["sem4"], student["sem5"],
                student["attendance"], student["arrears_count"],
                student["study_hours"], student["sleep_hours"],
                student["travel_time"],
                1 if student["social_media"] == "Low" else 0,
                1 if student["social_media"] == "Medium" else 0,
                1 if student["social_media"] == "High" else 0,
                1 if student["stress_level"] == "Low" else 0,
                1 if student["stress_level"] == "Medium" else 0,
                1 if student["stress_level"] == "High" else 0,
                1 if student["internet_access"] == "Limited" else 0,
                1 if student["internet_access"] == "Unlimited" else 0,
                1 if student["residence"] == "Day Scholar" else 0,
                1 if student["residence"] == "Hosteller" else 0,
                1 if student["part_time_job"] == "No" else 0,
                1 if student["part_time_job"] == "Yes" else 0,
            ]

            input_array = np.array(model_input).reshape(1, -1)
            prediction = model.predict(input_array)
            predicted_mark = round(prediction[0], 2)

            log_prediction(
                selected_idx, predicted_mark, "PASS" if predicted_mark >= 40 else "FAIL"
            )

            st.success(f"🎯 Predicted Final Mark: {predicted_mark}")

            if predicted_mark >= 40:
                st.success("✅ Predicted Result: PASS")
            else:
                st.error("❌ Predicted Result: FAIL")

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