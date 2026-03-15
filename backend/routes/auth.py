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
FRONTEND_URL  = os.environ.get("FRONTEND_URL", "https://smart-basket-63ww.onrender.com")

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

# ── Auth token store (in-memory, good enough for small scale) ─────────────────
# Maps auth_token -> {username, name, created_at}
_auth_tokens = {}

def create_auth_token(username, name):
    """Create a short-lived token to pass to the React frontend."""
    token = secrets.token_urlsafe(32)
    _auth_tokens[token] = {
        'username': username,
        'name': name,
        'created_at': time.time()
    }
    return token

def verify_auth_token(token):
    """Verify token and return user data, or None if invalid/expired."""
    data = _auth_tokens.get(token)
    if not data:
        return None
    # Tokens expire after 5 minutes (one-time use for handoff)
    if time.time() - data['created_at'] > 300:
        _auth_tokens.pop(token, None)
        return None
    return data

# ── Login ─────────────────────────────────────────────────────────────────────
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
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

        # Update last login
        try:
            supabase.table('users').update({
                'last_login': datetime.utcnow().isoformat()
            }).eq('username', username).execute()
        except:
            pass

        # Create token and redirect to React frontend
        token = create_auth_token(username, user.get('name', username))
        return redirect(f"{FRONTEND_URL}?auth_token={token}")

    return render_template('login.html')

# ── Sign Up ───────────────────────────────────────────────────────────────────
@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
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
                'name':             name,
                'email':            email,
                'username':         username,
                'password':         hash_password(password),
                'created_at':       datetime.utcnow().isoformat(),
                'session_token':    None,
                'session_tokens':   [],
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
            f"Visit: {FRONTEND_URL}\n\n"
            f"— Natts Digital"
        )

        # Auto-login after signup
        token = create_auth_token(username, name)
        return redirect(f"{FRONTEND_URL}?auth_token={token}")

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
    session.clear()
    return redirect('/login')

# ── API: verify token (called by React on load) ───────────────────────────────
@auth_bp.route('/api/verify', methods=['POST'])
def verify():
    """React calls this with the auth_token to get user info."""
    token = request.json.get('token', '')
    data = verify_auth_token(token)
    if not data:
        return jsonify({'valid': False}), 401
    # Consume token (one-time use)
    _auth_tokens.pop(token, None)
    return jsonify({
        'valid':    True,
        'username': data['username'],
        'name':     data['name'],
    })

# ── API: check session (React calls this on every load after token exchange) ──
@auth_bp.route('/api/me')
def me():
    """Check if user has a valid session stored in React (via token in header)."""
    token = request.headers.get('X-Auth-Token', '')
    if not token:
        return jsonify({'logged_in': False}), 401
    # Look up token in Supabase session_token field
    try:
        result = supabase.table('users').select('username, name, telegram_chat_id').eq('session_token', token).execute()
        if not result.data:
            return jsonify({'logged_in': False}), 401
        user = result.data[0]
        return jsonify({
            'logged_in':        True,
            'username':         user['username'],
            'name':             user['name'],
            'telegram_connected': bool(user.get('telegram_chat_id')),
        })
    except Exception as e:
        return jsonify({'logged_in': False, 'error': str(e)}), 401

# ── API: exchange auth token for session token ────────────────────────────────
@auth_bp.route('/api/session', methods=['POST'])
def create_session():
    """After verifying auth_token, create a permanent session token for React."""
    token = request.json.get('token', '')
    data = verify_auth_token(token)
    if not data:
        return jsonify({'valid': False}), 401

    # Create a long-lived session token
    session_token = secrets.token_urlsafe(48)
    try:
        supabase.table('users').update({
            'session_token': session_token
        }).eq('username', data['username']).execute()
    except Exception as e:
        return jsonify({'valid': False, 'error': str(e)}), 500

    _auth_tokens.pop(token, None)
    return jsonify({
        'valid':         True,
        'session_token': session_token,
        'username':      data['username'],
        'name':          data['name'],
    })

# ── API: logout (React calls this) ────────────────────────────────────────────
@auth_bp.route('/api/logout', methods=['POST'])
def api_logout():
    token = request.headers.get('X-Auth-Token', '')
    if token:
        try:
            supabase.table('users').update({
                'session_token': None
            }).eq('session_token', token).execute()
        except:
            pass
    return jsonify({'ok': True})

# ── API: save shopping list ───────────────────────────────────────────────────
@auth_bp.route('/api/list/save', methods=['POST'])
def save_list():
    token = request.headers.get('X-Auth-Token', '')
    if not token:
        return jsonify({'error': 'Not logged in'}), 401
    try:
        result = supabase.table('users').select('username').eq('session_token', token).execute()
        if not result.data:
            return jsonify({'error': 'Invalid session'}), 401
        username = result.data[0]['username']
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    items = request.json.get('items', [])
    # items is now a list of objects: {name, price, was_price, saving_pct, store}
    try:
        supabase.table('list_items').delete().eq('username', username).execute()
        if items:
            rows = []
            for item in items:
                if isinstance(item, str):
                    rows.append({'username': username, 'name': item})
                else:
                    rows.append({
                        'username':   username,
                        'name':       item.get('name', ''),
                        'price':      item.get('price'),
                        'was_price':  item.get('was_price'),
                        'saving_pct': item.get('saving_pct'),
                        'store':      item.get('store'),
                    })
            supabase.table('list_items').insert(rows).execute()
        return jsonify({'ok': True, 'saved': len(items)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ── API: load shopping list ───────────────────────────────────────────────────
@auth_bp.route('/api/list/load')
def load_list():
    token = request.headers.get('X-Auth-Token', '')
    if not token:
        return jsonify({'items': []})
    try:
        result = supabase.table('users').select('username').eq('session_token', token).execute()
        if not result.data:
            return jsonify({'items': []})
        username = result.data[0]['username']
        rows = supabase.table('list_items').select('name, price, was_price, saving_pct, store').eq('username', username).execute().data
        return jsonify({'items': rows})
    except Exception as e:
        return jsonify({'items': [], 'error': str(e)})

# ── API: telegram connect ─────────────────────────────────────────────────────
@auth_bp.route('/api/telegram/connect', methods=['POST'])
def telegram_connect():
    token = request.headers.get('X-Auth-Token', '')
    if not token:
        return jsonify({'error': 'Not logged in'}), 401
    chat_id = request.json.get('chat_id', '').strip()
    if not chat_id:
        return jsonify({'error': 'No chat ID provided'}), 400
    try:
        supabase.table('users').update({
            'telegram_chat_id': chat_id
        }).eq('session_token', token).execute()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ── API: telegram status ──────────────────────────────────────────────────────
@auth_bp.route('/api/telegram/status')
def telegram_status():
    token = request.headers.get('X-Auth-Token', '')
    if not token:
        return jsonify({'connected': False}), 401
    try:
        result = supabase.table('users').select('telegram_chat_id').eq('session_token', token).execute()
        chat_id = result.data[0].get('telegram_chat_id') if result.data else None
        return jsonify({'connected': bool(chat_id)})
    except Exception as e:
        return jsonify({'connected': False, 'error': str(e)})
