console.log('teacher_login.js loaded');
const teacherLogin = document.getElementById('teacherLoginForm');
if (teacherLogin) {
    teacherLogin.addEventListener('submit', async function(e) {
        e.preventDefault();
        const teacher_id = document.getElementById('teacher_id').value.trim();
        const password = document.getElementById('password').value;

        try {
            const response = await fetch('/teacher_login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ teacher_id, password })
            });
            const data = await response.json();
            console.log('teacher login response', data);
            if (data.status === 'success') {
                window.location.href = '/teacher_dashboard';
            } else if (data.status === 'invalid') {
                alert('Invalid ID or Password');
            } else {
                alert('An error occurred');
            }
        } catch (err) {
            console.error('network error during teacher login', err);
            alert('Could not reach server; is the backend running?');
        }
    });
} else {
    console.warn('teacher login form element not found');
}