# Final Year Project - Student Performance Prediction

This workspace contains a Flask application for user authentication and navigation alongside several Streamlit scripts for interactive prediction dashboards.

## Running the Application

1. **Flask backend**

   ```powershell
   cd "d:\Backup praveen\Final Year Project"
   python app.py
   ```

   This starts the Flask server (default port 5000) which serves the login pages and basic navigation.

2. **Streamlit apps**
   The buttons on the dashboard pages open separate Streamlit instances. You need to start these manually in separate terminal windows:
   - Next semester predictor (student-facing):
     ```powershell
     streamlit run single.py
     ```
     (defaults to port 8501)
   - Final semester dashboard for students:
     ```powershell
     streamlit run student_dashboard.py --server.port 8502
     ```
   - Final semester dashboard for teachers:
     ```powershell
     streamlit run teacher_dashboard.py --server.port 8503
     ```

   Each of these servers must be running for the corresponding buttons to work. They will open in a new browser tab when clicked.

## How It Works

- The Flask pages (`student_dashboard.html`, `teacher_dashboard.html`) contain JavaScript that redirects to the appropriate Streamlit URL when the user clicks a button.
- Student ID (and optionally teacher ID) are stored in `localStorage` so the Streamlit apps can read them from query parameters.

> ⚠️ If you prefer to use the Flask-based HTML forms (`next_sem_predict.html` and `final_sem_predict.html`), those remain available at `/next_sem_predict` and `/final_sem_predict` but they are separate from the Streamlit workflows.

## Notes

- Machine learning model files live in the `models/` directory (`best_classification_model.joblib`, `best_regression_model.joblib`, `next_sem_model.pkl`, `final_sem_model.pkl`). Be sure the working directory is the project root so the scripts can locate them.
- Make sure the SQLite databases (`database/*.db`) are writable and accessible to both Flask and Streamlit processes.
- Adjust port numbers if they conflict with other services.
