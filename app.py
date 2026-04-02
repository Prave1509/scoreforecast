from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash

# machine learning helpers
import joblib
import numpy as np

# import database initializer
from database.init_db import init_db

# constants
STUDENT_PREFIX = "STU"
TEACHER_PREFIX = "TEC"

ADMIN_ID = "Admin"
ADMIN_PASSWORD = "admin123"

app = Flask(__name__)
app.secret_key = "scoreforecast_secret_key"
CORS(app)

# database path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE_DIR, "database", "users.db")

# ensure database folder exists
os.makedirs(os.path.dirname(DB), exist_ok=True)

# initialize database
init_db(DB)

# ---------- DATABASE HELPERS ----------


def insert_prediction(source, user_id, predicted_mark, result):
    """Log a prediction event into the central `predictions` table."""
    try:
        conn = sqlite3.connect(DB)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO predictions (source, user_id, predicted_mark, result) VALUES (?,?,?,?)",
            (source, user_id, predicted_mark, result),
        )
        conn.commit()
    except Exception:
        pass
    finally:
        conn.close()


# ---------- FRONTEND PAGE ROUTES ----------


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/learn-more")
def learn_more():
    return render_template("learn-more.html")


@app.route("/role-select")
def role_select():
    return render_template("role-select.html")


@app.route("/student_login")
def student_login_page():
    return render_template("student_login.html")


@app.route("/student_signup")
def student_signup_page():
    return render_template("student_signup.html")


@app.route("/teacher_login")
def teacher_login_page():
    return render_template("teacher_login.html")


@app.route("/teacher_signup")
def teacher_signup_page():
    return render_template("teacher_signup.html")


@app.route("/admin_login")
def admin_login_page():
    return render_template("admin_login.html")


@app.route("/student_dashboard")
def student_dashboard_page():
    return render_template("student_dashboard.html")


@app.route("/teacher_dashboard")
def teacher_dashboard_page():
    return render_template("teacher_dashboard.html")


@app.route("/admin_dashboard")
def admin_dashboard_page():
    return render_template("admin_dashboard.html")


@app.route("/admin_logout")
def admin_logout():
    return render_template("admin_login.html")


# ---------- PREDICTION HELPER ----------


def _compute_prediction(form, student_id=None, source="next_sem"):
    prev_score = float(form.get("prev_score", 0))
    attendance = float(form.get("attendance", 0))
    arrears = float(form.get("arrears", 0))
    study_hrs = float(form.get("study_hrs", 0))
    sleep_hrs = float(form.get("sleep_hrs", 0))
    travel_time = float(form.get("travel_time", 0))
    stress = form.get("stress")
    social = form.get("social")
    internet = form.get("internet")
    student_type = form.get("student_type")
    part_time = form.get("part_time")

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
        "result_Pass": 1,
    }

    features = np.array(list(input_data.values())).reshape(1, -1)
    model_dir = os.path.join(BASE_DIR, "models")
    clf = joblib.load(os.path.join(model_dir, "best_classification_model.joblib"))
    reg = joblib.load(os.path.join(model_dir, "best_regression_model.joblib"))

    status_pred = clf.predict(features)[0]
    score_pred = reg.predict(features)[0]
    status = "Pass" if status_pred == 1 else "Fail"
    score = round(score_pred, 2)

    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO predictions (source, user_id, predicted_mark, result) VALUES (?,?,?,?)",
        (source, student_id or form.get("student_id"), score, status),
    )
    conn.commit()
    conn.close()

    return {"status": status, "score": score}


@app.route("/next_sem_predict", methods=["GET", "POST"])
def next_sem_predict_page():
    prediction = None
    if request.method == "POST":
        prediction = _compute_prediction(
            request.form, student_id=request.args.get("student_id")
        )
    return render_template("next_sem_predict.html", prediction=prediction)


@app.route("/final_sem_predict", methods=["GET", "POST"])
def final_sem_predict_page():
    prediction = None
    if request.method == "POST":
        prediction = _compute_prediction(
            request.form, student_id=request.args.get("student_id"), source="final_sem"
        )
    return render_template("final_sem_predict.html", prediction=prediction)


# ---------- DATABASE HELPERS ----------


def get_next_student_id():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT student_id FROM students ORDER BY id DESC LIMIT 1")
    row = cur.fetchone()
    conn.close()
    if row and row[0]:
        num = int(row[0].replace(STUDENT_PREFIX, ""))
        return f"{STUDENT_PREFIX}{num+1:03d}"
    return f"{STUDENT_PREFIX}001"


def get_next_teacher_id():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT teacher_id FROM teachers ORDER BY id DESC LIMIT 1")
    row = cur.fetchone()
    conn.close()
    if row and row[0]:
        num = int(row[0].replace(TEACHER_PREFIX, ""))
        return f"{TEACHER_PREFIX}{num+1:03d}"
    return f"{TEACHER_PREFIX}001"


def insert_student(name, student_id, password):
    try:
        conn = sqlite3.connect(DB)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO students (name, student_id, password) VALUES (?,?,?)",
            (name, student_id, password),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def check_student(student_id, password):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT password FROM students WHERE student_id=?", (student_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return False
    return check_password_hash(row[0], password)


def insert_teacher(name, teacher_id, password):
    try:
        conn = sqlite3.connect(DB)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO teachers (name, teacher_id, password) VALUES (?,?,?)",
            (name, teacher_id, password),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def check_teacher(teacher_id, password):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT password FROM teachers WHERE teacher_id=?", (teacher_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return False
    return check_password_hash(row[0], password)


# ---------- ADMIN HELPERS ----------


def fetch_all_students():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT id, name, student_id FROM students")
    rows = cur.fetchall()
    conn.close()
    return rows


def fetch_all_teachers():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT id, name, teacher_id FROM teachers")
    rows = cur.fetchall()
    conn.close()
    return rows


def fetch_all_predictions():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT * FROM predictions ORDER BY timestamp DESC")
    rows = cur.fetchall()
    conn.close()
    return rows


# ---------- STUDENT AUTH ----------


@app.route("/student_signup", methods=["POST"])
def student_signup():
    data = request.get_json(force=True) or {}
    name = data.get("name")
    password = data.get("password")

    if not name or not password:
        return jsonify({"status": "error", "message": "Missing fields"}), 400

    student_id = get_next_student_id()
    hashed = generate_password_hash(password)

    if insert_student(name, student_id, hashed):
        return jsonify({"status": "success", "student_id": student_id})

    return jsonify({"status": "error"}), 500


@app.route("/student_login", methods=["POST"])
def student_login():
    data = request.get_json(force=True) or {}
    student_id = data.get("student_id")
    password = data.get("password")

    if not student_id or not password:
        return jsonify({"status": "error"}), 400

    if check_student(student_id, password):
        return jsonify({"status": "success"})

    return jsonify({"status": "invalid"})


# ---------- TEACHER AUTH ----------


@app.route("/teacher_signup", methods=["POST"])
def teacher_signup():
    data = request.get_json(force=True) or {}
    name = data.get("name")
    password = data.get("password")

    if not name or not password:
        return jsonify({"status": "error"}), 400

    teacher_id = get_next_teacher_id()
    hashed = generate_password_hash(password)

    if insert_teacher(name, teacher_id, hashed):
        return jsonify({"status": "success", "teacher_id": teacher_id})

    return jsonify({"status": "error"}), 500


@app.route("/teacher_login", methods=["POST"])
def teacher_login():
    data = request.get_json(force=True) or {}
    teacher_id = data.get("teacher_id")
    password = data.get("password")

    if not teacher_id or not password:
        return jsonify({"status": "error"}), 400

    if check_teacher(teacher_id, password):
        return jsonify({"status": "success"})

    return jsonify({"status": "invalid"})


@app.route("/teacher_choice")
def teacher_choice_page():
    return render_template("teacher_choice.html")


# ---------- ADMIN LOGIN ----------


@app.route("/admin_login", methods=["POST"])
def admin_login():
    data = request.get_json(force=True) or {}
    admin_id = data.get("admin_id", "").strip()
    password = data.get("password", "")

    if admin_id == ADMIN_ID and password == ADMIN_PASSWORD:
        return jsonify({"status": "success"})

    return jsonify({"status": "invalid"})


# ---------- ADMIN DASHBOARD ----------


@app.route("/admin/students")
def admin_students():
    rows = fetch_all_students()
    students = [{"db_id": r[0], "name": r[1], "student_id": r[2]} for r in rows]
    return jsonify({"students": students})


@app.route("/admin/teachers")
def admin_teachers():
    rows = fetch_all_teachers()
    teachers = [{"db_id": r[0], "name": r[1], "teacher_id": r[2]} for r in rows]
    return jsonify({"teachers": teachers})


@app.route("/admin/predictions")
def admin_predictions():
    rows = fetch_all_predictions()
    preds = []
    for r in rows:
        preds.append(
            {
                "id": r[0],
                "source": r[1],
                "user_id": r[2],
                "predicted_mark": r[3],
                "result": r[4],
                "timestamp": r[5],
            }
        )
    return jsonify({"predictions": preds})


@app.route("/admin/stats")
def admin_stats():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM students")
    student_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM teachers")
    teacher_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM predictions")
    pred_count = cur.fetchone()[0]
    conn.close()
    return jsonify(
        {
            "students": student_count,
            "teachers": teacher_count,
            "predictions": pred_count,
        }
    )


# ---------- ADMIN EDIT / DELETE ----------


@app.route("/admin/student/<student_id>", methods=["PUT"])
def admin_edit_student(student_id):
    data = request.get_json(force=True) or {}
    name = data.get("name", "").strip()
    password = data.get("password", "")

    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    if name and password:
        hashed = generate_password_hash(password)
        cur.execute(
            "UPDATE students SET name=?, password=? WHERE student_id=?",
            (name, hashed, student_id),
        )
    elif name:
        cur.execute("UPDATE students SET name=? WHERE student_id=?", (name, student_id))
    elif password:
        hashed = generate_password_hash(password)
        cur.execute(
            "UPDATE students SET password=? WHERE student_id=?", (hashed, student_id)
        )
    else:
        conn.close()
        return jsonify({"status": "error", "message": "Nothing to update"}), 400

    conn.commit()
    conn.close()
    return jsonify({"status": "success"})


@app.route("/admin/student/<student_id>", methods=["DELETE"])
def admin_delete_student(student_id):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("DELETE FROM students WHERE student_id=?", (student_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})


@app.route("/admin/teacher/<teacher_id>", methods=["PUT"])
def admin_edit_teacher(teacher_id):
    data = request.get_json(force=True) or {}
    name = data.get("name", "").strip()
    password = data.get("password", "")

    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    if name and password:
        hashed = generate_password_hash(password)
        cur.execute(
            "UPDATE teachers SET name=?, password=? WHERE teacher_id=?",
            (name, hashed, teacher_id),
        )
    elif name:
        cur.execute("UPDATE teachers SET name=? WHERE teacher_id=?", (name, teacher_id))
    elif password:
        hashed = generate_password_hash(password)
        cur.execute(
            "UPDATE teachers SET password=? WHERE teacher_id=?", (hashed, teacher_id)
        )
    else:
        conn.close()
        return jsonify({"status": "error", "message": "Nothing to update"}), 400

    conn.commit()
    conn.close()
    return jsonify({"status": "success"})


@app.route("/admin/teacher/<teacher_id>", methods=["DELETE"])
def admin_delete_teacher(teacher_id):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("DELETE FROM teachers WHERE teacher_id=?", (teacher_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})


# ---------- RUN SERVER ----------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
