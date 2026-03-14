function nextSem(){
    // open the standalone Streamlit prediction app (single.py)
    const id = localStorage.getItem('student_id');
    let url = "https://streamlit-app-r2ld.onrender.com"; // assume student runs `streamlit run single.py`
    if (id) url += `?student_id=${encodeURIComponent(id)}`;
    window.open(url, '_blank');
}

function finalSem(){
    // open the Streamlit dashboard for final semester
    const id = localStorage.getItem('student_id');
    let url = "https://student-dashboard-6pqo.onrender.com"; // should be `streamlit run student_dashboard.py --server.port 8502`
    if (id) url += `?student_id=${encodeURIComponent(id)}`;
    window.open(url, '_blank');
}