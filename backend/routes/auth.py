from flask import Blueprint, render_template, request, redirect, session, jsonify
from supabase import create_client
import os, hashlib, secrets, time
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

auth_bp = Blueprint('auth', __name__)

supabase = create_client(
    os.environ.get("SUPABASE_URL"),
    os.environ.get("SUPABASE_KEY")
)

FLASK_MAIL_SERVER   = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
FLASK_MAIL_PORT     = int(os.environ.get("MAIL_PORT", 587))
FLASK_MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")
FLASK_MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "")
MAIL_FROM           = os.environ.get("MAIL_FROM", FLASK_MAIL_USERNAME)

def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def send_email(to, subject, body):
    """Send a plain-text email via SMTP. Never raises — logs errors only."""
    import smtplib
    from email.mime.text import MIMEText
    if not FLASK_MAIL_USERNAME or not FLASK_MAIL_PASSWORD:
        print("Email not configured — skipping.")
        return False
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From']    = MAIL_FROM
    msg['To']      = to
    try:
        with smtplib.SMTP(FLASK_MAIL_SERVER, FLASK_MAIL_PORT, timeout=10) as s:
            s.starttls()
            s.login(FLASK_MAIL_USERNAME, FLASK_MAIL_PASSWORD)
            s.sendmail(MAIL_FROM, [to], msg.as_string())
        return True
    except Exception as e:
        print(f"Email error (non-fatal): {e}")
        return False

# ── Login required decorator ──────────────────────────────────────────────────
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'username' not in session:
            return redirect('/login')
        # Token check every 60 s (2-session enforcement)
        username = session['username']
        token    = session.get('session_token')
        last_check = session.get('token_last_check', 0)
        if token and (time.time() - last_check > 60):
            try:
                user = supabase.table('users').select('session_token').eq('username', username).execute().data
                # Check if our token is still in the allowed list
                allowed = [u.get('session_token') for u in user if u.get('session_token')]
                session_tokens = session.get('session_token', '')
                if session_tokens and session_tokens not in allowed:
                    session.clear()
                    return redirect('/login?msg=session_expired')
                session['token_last_check'] = time.time()
            except:
                pass
        return f(*args, **kwargs)
    return decorated

# ── Login ─────────────────────────────────────────────────────────────────────
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'username' in session:
        return redirect('/app')

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not password:
            return render_template('login.html', error="Please fill in all fields.")

        try:
            result = supabase.table('users').select('*').eq('username', username).execute()
            users  = result.data
        except Exception as e:
            return render_template('login.html', error=f"Database error: {e}")

        if not users:
            return render_template('login.html', error="Username not found.")

        user = users[0]
        if user['password'] != hash_password(password):
            return render_template('login.html', error="Incorrect password.")

        # Generate new session token (2-session limit handled by storing up to 2 tokens)
        token = secrets.token_hex(32)

        # Get existing tokens
        existing_tokens = user.get('session_tokens', []) or []
        if isinstance(existing_tokens, str):
            import json
            try: existing_tokens = json.loads(existing_tokens)
            except: existing_tokens = []

        # Keep only last 1 token (for 2-device limit, keep last 2)
        existing_tokens = existing_tokens[-1:] + [token]

        try:
            supabase.table('users').update({
                'session_token':  token,
                'session_tokens': existing_tokens,
                'last_login':     datetime.utcnow().isoformat()
            }).eq('username', username).execute()
        except:
            pass

        session['username']          = user['username']
        session['name']              = user.get('name', username)
        session['session_token']     = token
        session['token_last_check']  = time.time()
        session['trial_ends']        = user.get('trial_ends', '')
        session['premium']           = user.get('premium', False)

        return redirect('/app')

    return render_template('login.html')

# ── Sign Up ───────────────────────────────────────────────────────────────────
@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if 'username' in session:
        return redirect('/app')

    if request.method == 'POST':
        name       = request.form.get('name', '').strip()
        email      = request.form.get('email', '').strip().lower()
        username   = request.form.get('username', '').strip().lower()
        password   = request.form.get('password', '').strip()
        confirm    = request.form.get('confirm', '').strip()
        promo_code = request.form.get('promo_code', '').strip().upper()

        # Validation
        if not all([name, email, username, password, confirm]):
            return render_template('signup.html', error="Please fill in all fields.")
        if password != confirm:
            return render_template('signup.html', error="Passwords do not match.")
        if len(password) < 6:
            return render_template('signup.html', error="Password must be at least 6 characters.")
        if len(username) < 3:
            return render_template('signup.html', error="Username must be at least 3 characters.")

        try:
            existing = supabase.table('users').select('username, email').execute().data
        except Exception as e:
            return render_template('signup.html', error=f"Database error: {e}")

        if any(u['username'] == username for u in existing):
            return render_template('signup.html', error="Username already taken.")
        if any(u['email'] == email for u in existing):
            return render_template('signup.html', error="Email already registered.")

        # Promo code check
        trial_days   = 14
        promo_applied = None
        if promo_code:
            try:
                promo = supabase.table('promo_codes').select('*').eq('code', promo_code).eq('active', True).execute()
                if promo.data:
                    p = promo.data[0]
                    max_uses = p.get('max_uses', 0)
                    uses     = p.get('uses_count', 0)
                    if max_uses == 0 or uses < max_uses:
                        trial_days   = p.get('trial_days', 14)
                        promo_applied = promo_code
            except:
                pass

        trial_ends = (datetime.utcnow() + timedelta(days=trial_days)).isoformat()

        try:
            supabase.table('users').insert({
                'name':          name,
                'email':         email,
                'username':      username,
                'password':      hash_password(password),
                'trial_ends':    trial_ends,
                'premium':       False,
                'created_at':    datetime.utcnow().isoformat(),
                'session_token': None,
                'session_tokens': []
            }).execute()
        except Exception as e:
            return render_template('signup.html', error=f"Could not create account: {e}")

        if promo_applied:
            try:
                p_data = supabase.table('promo_codes').select('uses_count').eq('code', promo_applied).execute().data
                supabase.table('promo_codes').update({
                    'uses_count': (p_data[0]['uses_count'] if p_data else 0) + 1
                }).eq('code', promo_applied).execute()
            except:
                pass

        # Welcome email
        send_email(
            email,
            "Welcome to SmartBasket 🛒",
            f"Hi {name},\n\nWelcome to SmartBasket by Natts Digital!\n\n"
            f"Your account is ready. You have a {trial_days}-day free trial.\n\n"
            f"Username: {username}\n\n"
            f"Start saving on your grocery shop at https://smart-basket-63ww.onrender.com\n\n"
            f"— Natts Digital"
        )

        return render_template('signup.html', success=f"Account created! Welcome, {name}.")

    return render_template('signup.html')

# ── Forgot ────────────────────────────────────────────────────────────────────
@auth_bp.route('/forgot', methods=['GET', 'POST'])
def forgot():
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'username':
            email = request.form.get('email', '').strip().lower()
            try:
                result = supabase.table('users').select('*').eq('email', email).execute()
                users  = result.data
            except:
                return render_template('forgot.html', error="Database error.")

            if not users:
                return render_template('forgot.html', error="No account found with that email.")

            user = users[0]
            send_email(
                email,
                "Your SmartBasket Username",
                f"Hi {user['name']},\n\nYour SmartBasket username is: {user['username']}\n\n— Natts Digital"
            )
            return render_template('forgot.html', success="✅ Your username has been sent to your email.")

        elif action == 'password':
            username = request.form.get('username', '').strip().lower()
            email    = request.form.get('email', '').strip().lower()
            try:
                result = supabase.table('users').select('*').eq('username', username).execute()
                users  = result.data
            except:
                return render_template('forgot.html', error="Database error.")

            if not users or users[0]['email'] != email:
                return render_template('forgot.html', error="Username and email do not match.")

            user = users[0]
            new_pw = secrets.token_urlsafe(8)
            try:
                supabase.table('users').update({
                    'password': hash_password(new_pw)
                }).eq('username', username).execute()
            except:
                return render_template('forgot.html', error="Could not reset password.")

            send_email(
                email,
                "Your SmartBasket Password Reset",
                f"Hi {user['name']},\n\nYour new temporary password is: {new_pw}\n\n"
                f"Please log in and change it immediately.\n\n— Natts Digital"
            )
            return render_template('forgot.html', success="✅ A new password has been sent to your email.")

    return render_template('forgot.html')

# ── Logout ────────────────────────────────────────────────────────────────────
@auth_bp.route('/logout')
def logout():
    if 'username' in session:
        try:
            supabase.table('users').update({
                'session_token': None
            }).eq('username', session['username']).execute()
        except:
            pass
    session.clear()
    return redirect('/login')

# ── Promo validation (AJAX) ───────────────────────────────────────────────────
@auth_bp.route('/validate_promo')
def validate_promo():
    code = request.args.get('code', '').strip().upper()
    if not code:
        return jsonify(valid=False, message="No code entered.")
    try:
        promo = supabase.table('promo_codes').select('*').eq('code', code).eq('active', True).execute()
        if not promo.data:
            return jsonify(valid=False, message="Invalid or expired promo code.")
        p        = promo.data[0]
        max_uses = p.get('max_uses', 0)
        uses     = p.get('uses_count', 0)
        if max_uses > 0 and uses >= max_uses:
            return jsonify(valid=False, message="This promo code has reached its limit.")
        trial_days = p.get('trial_days', 14)
        return jsonify(valid=True, message=f"Code applied! {trial_days}-day free trial.")
    except:
        return jsonify(valid=False, message="Error checking code.")
