function nextSem(){
    // open the standalone Streamlit prediction app (single.py)
    const id = localStorage.getItem('student_id');
    let url = "http://localhost:8501/"; // assume student runs `streamlit run single.py`
    if (id) url += `?student_id=${encodeURIComponent(id)}`;
    window.open(url, '_blank');
}

function finalSem(){
    // open the Streamlit dashboard for final semester
    const id = localStorage.getItem('student_id');
    let url = "http://localhost:8502/"; // should be `streamlit run student_dashboard.py --server.port 8502`
    if (id) url += `?student_id=${encodeURIComponent(id)}`;
    window.open(url, '_blank');
}