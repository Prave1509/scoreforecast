console.log('teacher_signup.js loaded');

// ─── Validation Helpers ───────────────────────────────────────────────────────

/**
 * Name rules:
 *  - 3 to 50 characters
 *  - Letters and spaces ONLY (any language)
 *  - NO digits, NO email symbols (@, .), NO special characters
 */
function validateName(name) {
    const trimmed = name.trim();

    if (trimmed.length === 0) {
        return { ok: false, msg: 'Name is required.' };
    }
    if (trimmed.length < 3) {
        return { ok: false, msg: 'Name must be at least 3 characters.' };
    }
    if (trimmed.length > 50) {
        return { ok: false, msg: 'Name must be under 50 characters.' };
    }
    if (trimmed.includes('@') || /\.\w{2,}$/.test(trimmed)) {
        return { ok: false, msg: 'Enter your real name, not an email address.' };
    }
    if (/\d/.test(trimmed)) {
        return { ok: false, msg: 'Name must not contain numbers.' };
    }
    if (!/^[\p{L}\s]+$/u.test(trimmed)) {
        return { ok: false, msg: 'Name must contain letters and spaces only — no symbols.' };
    }

    return { ok: true };
}

/**
 * Password rules:
 *  - At least 6 characters
 *  - At least 1 letter
 *  - At least 1 number
 *  - Not blank/whitespace
 */
function validatePassword(password) {
    if (!password || password.trim().length === 0) {
        return { ok: false, msg: 'Password is required.' };
    }
    if (password.length < 8) {
        return { ok: false, msg: 'Password must be at least 8 characters.' };
    }
    if (!/[0-9]/.test(password)) {
        return { ok: false, msg: 'Password must contain at least one number.' };
    }
    if (!/[!@#$%^&*]/.test(password)) {
        return { ok: false, msg: 'Password must contain at least one special character (!@#$%^&*).' };
    }
    return { ok: true };
}

/**
 * Confirm password rules:
 *  - Must match password
 */
function validateConfirmPassword(password, confirmPassword) {
    if (!confirmPassword || confirmPassword.trim().length === 0) {
        return { ok: false, msg: 'Please confirm your password.' };
    }
    if (password !== confirmPassword) {
        return { ok: false, msg: 'Passwords do not match.' };
    }
    return { ok: true };
}

// ─── UI Helpers ───────────────────────────────────────────────────────────────

function showFieldError(inputId, msgId, message) {
    const input = document.getElementById(inputId);
    const msg   = document.getElementById(msgId);
    if (input) input.classList.add('error');
    if (msg)   { msg.textContent = message; msg.classList.add('show'); }
}

function clearFieldError(inputId, msgId) {
    const input = document.getElementById(inputId);
    const msg   = document.getElementById(msgId);
    if (input) input.classList.remove('error');
    if (msg)   msg.classList.remove('show');
}

function showAlert(message, type = 'error') {
    const box = document.getElementById('alertBox');
    if (box) {
        box.textContent = message;
        box.className = `alert-box show show-${type}`;
    }
}

function clearAlert() {
    const box = document.getElementById('alertBox');
    if (box) box.classList.remove('show');
}

// ─── Live Validation ──────────────────────────────────────────────────────────

const nameInput    = document.getElementById('name');
const passInput    = document.getElementById('password');
const confirmInput = document.getElementById('confirm_password');

if (nameInput) {
    nameInput.addEventListener('input', () => {
        const result = validateName(nameInput.value);
        if (!result.ok) showFieldError('name', 'nameError', result.msg);
        else            clearFieldError('name', 'nameError');
    });
}

if (passInput) {
    passInput.addEventListener('input', () => {
        const result = validatePassword(passInput.value);
        if (!result.ok) showFieldError('password', 'passError', result.msg);
        else            clearFieldError('password', 'passError');

        // re-validate confirm if already typed
        if (confirmInput && confirmInput.value) {
            const cResult = validateConfirmPassword(passInput.value, confirmInput.value);
            if (!cResult.ok) showFieldError('confirm_password', 'confirmError', cResult.msg);
            else             clearFieldError('confirm_password', 'confirmError');
        }
    });
}

if (confirmInput) {
    confirmInput.addEventListener('input', () => {
        const result = validateConfirmPassword(passInput.value, confirmInput.value);
        if (!result.ok) showFieldError('confirm_password', 'confirmError', result.msg);
        else            clearFieldError('confirm_password', 'confirmError');
    });
}

// ─── Form Submit ──────────────────────────────────────────────────────────────

const teacherForm = document.getElementById('teacherSignupForm');
const submitBtn   = document.getElementById('signupBtn');

if (teacherForm) {
    teacherForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        clearAlert();

        const name            = nameInput    ? nameInput.value    : '';
        const password        = passInput    ? passInput.value    : '';
        const confirmPassword = confirmInput ? confirmInput.value : '';

        // Run all validations
        const nameResult    = validateName(name);
        const passResult    = validatePassword(password);
        const confirmResult = validateConfirmPassword(password, confirmPassword);

        let hasError = false;

        if (!nameResult.ok) {
            showFieldError('name', 'nameError', nameResult.msg);
            hasError = true;
        } else {
            clearFieldError('name', 'nameError');
        }

        if (!passResult.ok) {
            showFieldError('password', 'passError', passResult.msg);
            hasError = true;
        } else {
            clearFieldError('password', 'passError');
        }

        if (!confirmResult.ok) {
            showFieldError('confirm_password', 'confirmError', confirmResult.msg);
            hasError = true;
        } else {
            clearFieldError('confirm_password', 'confirmError');
        }

        if (hasError) return;

        // Send to server
        if (submitBtn) { submitBtn.disabled = true; submitBtn.textContent = 'Creating Account...'; }

        try {
            const response = await fetch('/teacher_signup', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: name.trim(), password })
            });
            const data = await response.json();
            console.log('teacher signup response', data);

            if (data.status === 'success') {
                showAlert(`✅ Account created! Your Teacher ID is: ${data.teacher_id} — Please note it down for login.`, 'success');
                setTimeout(() => { window.location.href = '/teacher_login'; }, 4000);
            } else {
                showAlert('An error occurred during signup. Please try again.', 'error');
                if (submitBtn) { submitBtn.disabled = false; submitBtn.textContent = 'Sign Up'; }
            }
        } catch (err) {
            console.error('Network error during teacher signup', err);
            showAlert('Could not reach server. Is the backend running?');
            if (submitBtn) { submitBtn.disabled = false; submitBtn.textContent = 'Create Account'; }
        }
    });
} else {
    console.warn('Teacher signup form element not found');
}