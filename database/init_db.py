import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "users.db")


# constants for ID prefixes
STUDENT_PREFIX = "STU"
TEACHER_PREFIX = "TEC"


def init_db(path=None):
    """Create the SQLite database and tables if they don't exist."""
    db = path or DB_PATH
    os.makedirs(os.path.dirname(db), exist_ok=True)
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            student_id TEXT UNIQUE,
            password TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS teachers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            teacher_id TEXT UNIQUE,
            password TEXT
        )
        """
    )
    # prediction log table; data may be inserted by other modules
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT,
            user_id TEXT,
            predicted_mark REAL,
            result TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
