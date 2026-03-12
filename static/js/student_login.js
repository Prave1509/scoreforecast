console.log('student_login.js loaded');
const loginForm = document.getElementById('studentLoginForm');
if (loginForm) {
    loginForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        const student_id = document.getElementById('student_id').value.trim();
        const password = document.getElementById('password').value;

        try {
            const response = await fetch('/student_login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ student_id, password })
            });
            const data = await response.json();
            console.log('login response', data);
            if (data.status === 'success') {
                // keep id for later (e.g. passing to dashboard for logging)
                localStorage.setItem('student_id', student_id);
                window.location.href = '/student_dashboard';
            } else if (data.status === 'invalid') {
                alert('Invalid ID or Password');
            } else {
                alert('An error occurred');
            }
        } catch (err) {
            console.error('network error during login', err);
            alert('Could not reach server; is the backend running?');
        }
    });
} else {
    console.warn('login form element not found');
}