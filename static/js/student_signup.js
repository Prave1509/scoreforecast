console.log('student_signup.js loaded');
const signupForm = document.getElementById('studentSignupForm');
if (signupForm) {
    signupForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        const name = document.getElementById('name').value.trim();
        const password = document.getElementById('password').value;

        try {
            const response = await fetch('/student_signup', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, password })
            });
            const data = await response.json();
            console.log('signup response', data);
            if (data.status === 'success') {
                alert(`Account created. Your Student ID is ${data.student_id}. Please note it for login.`);
                window.location.href = '/student_login';
            } else {
                alert('An error occurred during signup');
            }
        } catch (err) {
            console.error('network error during signup', err);
            alert('Could not reach server; is the backend running?');
        }
    });
} else {
    console.warn('signup form element not found');
}