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

MAIL_SERVER   = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
MAIL_PORT     = int(os.environ.get("MAIL_PORT", 587))
MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")
MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "")
MAIL_FROM     = os.environ.get("MAIL_FROM", MAIL_USERNAME)

def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def send_email(to, subject, body):
    import smtplib
    from email.mime.text import MIMEText
    if not MAIL_USERNAME or not MAIL_PASSWORD:
        print("Email not configured — skipping.")
        return False
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From']    = MAIL_FROM
    msg['To']      = to
    try:
        with smtplib.SMTP(MAIL_SERVER, MAIL_PORT, timeout=10) as s:
            s.starttls()
            s.login(MAIL_USERNAME, MAIL_PASSWORD)
            s.sendmail(MAIL_FROM, [to], msg.as_string())
        return True
    except Exception as e:
        print(f"Email error (non-fatal): {e}")
        return False

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'username' not in session:
            return redirect('/login')
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

        token = secrets.token_hex(32)
        existing_tokens = user.get('session_tokens', []) or []
        if isinstance(existing_tokens, str):
            import json
            try: existing_tokens = json.loads(existing_tokens)
            except: existing_tokens = []
        existing_tokens = existing_tokens[-1:] + [token]

        try:
            supabase.table('users').update({
                'session_token':  token,
                'session_tokens': existing_tokens,
                'last_login':     datetime.utcnow().isoformat()
            }).eq('username', username).execute()
        except:
            pass

        session['username']      = user['username']
        session['name']          = user.get('name', username)
        session['session_token'] = token
        session['token_last_check'] = time.time()

        return redirect('/app')

    return render_template('login.html')

# ── Sign Up ───────────────────────────────────────────────────────────────────
@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if 'username' in session:
        return redirect('/app')

    if request.method == 'POST':
        name     = request.form.get('name', '').strip()
        email    = request.form.get('email', '').strip().lower()
        username = request.form.get('username', '').strip().lower()
        password = request.form.get('password', '').strip()
        confirm  = request.form.get('confirm', '').strip()

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

        try:
            supabase.table('users').insert({
                'name':           name,
                'email':          email,
                'username':       username,
                'password':       hash_password(password),
                'created_at':     datetime.utcnow().isoformat(),
                'session_token':  None,
                'session_tokens': [],
                'telegram_chat_id': None,
            }).execute()
        except Exception as e:
            return render_template('signup.html', error=f"Could not create account: {e}")

        send_email(
            email,
            "Welcome to SmartPicks!",
            f"Hi {name},\n\nWelcome to SmartPicks by Natts Digital!\n\n"
            f"Your account is ready. Start saving on your grocery shop!\n\n"
            f"Username: {username}\n\n"
            f"Visit: https://smart-basket-63ww.onrender.com\n\n"
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
            send_email(email, "Your SmartPicks Username",
                f"Hi {user['name']},\n\nYour SmartPicks username is: {user['username']}\n\n— Natts Digital")
            return render_template('forgot.html', success="Your username has been sent to your email.")

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
            user   = users[0]
            new_pw = secrets.token_urlsafe(8)
            try:
                supabase.table('users').update({
                    'password': hash_password(new_pw)
                }).eq('username', username).execute()
            except:
                return render_template('forgot.html', error="Could not reset password.")
            send_email(email, "Your SmartPicks Password Reset",
                f"Hi {user['name']},\n\nYour new temporary password is: {new_pw}\n\n"
                f"Please log in and change it.\n\n— Natts Digital")
            return render_template('forgot.html', success="A new password has been sent to your email.")

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

# ── API: current user (called by React frontend) ──────────────────────────────
@auth_bp.route('/api/me')
def me():
    if 'username' not in session:
        return jsonify({'logged_in': False}), 401
    return jsonify({
        'logged_in':  True,
        'username':   session['username'],
        'name':       session.get('name', session['username']),
    })

# ── API: save shopping list to Supabase ───────────────────────────────────────
@auth_bp.route('/api/list/save', methods=['POST'])
def save_list():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    username = session['username']
    items = request.json.get('items', [])  # list of product name strings

    try:
        # Delete existing list items for this user
        supabase.table('list_items').delete().eq('username', username).execute()
        # Insert new items
        if items:
            rows = [{'username': username, 'product_name': item, 'list_id': None} for item in items]
            supabase.table('list_items').insert(rows).execute()
        return jsonify({'ok': True, 'saved': len(items)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ── API: load shopping list from Supabase ────────────────────────────────────
@auth_bp.route('/api/list/load')
def load_list():
    if 'username' not in session:
        return jsonify({'items': []})
    username = session['username']
    try:
        result = supabase.table('list_items').select('product_name').eq('username', username).execute()
        items = [r['product_name'] for r in result.data]
        return jsonify({'items': items})
    except Exception as e:
        return jsonify({'items': [], 'error': str(e)})

# ── Telegram connect ──────────────────────────────────────────────────────────
@auth_bp.route('/api/telegram/connect', methods=['POST'])
def telegram_connect():
    """User submits their Telegram chat ID to enable notifications."""
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    chat_id = request.json.get('chat_id', '').strip()
    if not chat_id:
        return jsonify({'error': 'No chat ID provided'}), 400
    try:
        supabase.table('users').update({
            'telegram_chat_id': chat_id
        }).eq('username', session['username']).execute()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ── API: get telegram status ──────────────────────────────────────────────────
@auth_bp.route('/api/telegram/status')
def telegram_status():
    if 'username' not in session:
        return jsonify({'connected': False}), 401
    try:
        result = supabase.table('users').select('telegram_chat_id').eq('username', session['username']).execute()
        chat_id = result.data[0].get('telegram_chat_id') if result.data else None
        return jsonify({'connected': bool(chat_id), 'chat_id': chat_id})
    except Exception as e:
        return jsonify({'connected': False, 'error': str(e)})
