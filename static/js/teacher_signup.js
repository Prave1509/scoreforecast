console.log('teacher_signup.js loaded');
const teacherForm = document.getElementById('teacherSignupForm');
if (teacherForm) {
    teacherForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        const name = document.getElementById('name').value.trim();
        const password = document.getElementById('password').value;

        try {
            const response = await fetch('/teacher_signup', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, password })
            });
            const data = await response.json();
            console.log('teacher signup response', data);
            if (data.status === 'success') {
                alert(`Account created. Your Teacher ID is ${data.teacher_id}. Please note it for login.`);
                window.location.href = '/teacher_login';
            } else {
                alert('An error occurred during signup');
            }
        } catch (err) {
            console.error('network error during teacher signup', err);
            alert('Could not reach server; is the backend running?');
        }
    });
} else {
    console.warn('teacher signup form element not found');
}