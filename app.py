import os
import json
import google.generativeai as genai # CHANGED: Import Google Library
from flask import Flask, render_template, request, url_for, jsonify, redirect, session
from flask_babel import Babel, gettext as _
from dotenv import load_dotenv
from Forms import CreateSearchForm_Admin
import mysql.connector
from twilio.rest import Client
import uuid, time
import qrcode
import socket
load_dotenv()


app = Flask(__name__)
genai.configure(api_key=os.getenv('api_key'))
app.secret_key = os.getenv('secret_key', 'my_fallback_secret_key_123')

model = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
    generation_config={"response_mime_type": "application/json"}
)


SITE_MAP = [
    # ==========================================
    # LEVEL 1: BROAD CATEGORIES
    # (Triggered by "I wanna login", "Login", "Sign in")
    # ==========================================
    {
        "label": "Personal Banking Login",
        "url": "/login",
        "icon": "user",
        "desc": "Internet Banking & Savings",
        "keywords": "login, sign in, access, main menu"
    },
    {
        "label": "Business Login (Velocity)",
        "url": "/login/business",
        "icon": "briefcase",
        "desc": "Corporate & SME Banking",
        "keywords": "login, sign in, business, corporate"
    },

    # ==========================================
    # LEVEL 2: PERSONAL METHODS
    # (Triggered by "Personal Account", "Personal Login")
    # ==========================================
    {
        "label": "Log in with Singpass",
        "url": "/login/qr",
        "icon": "smartphone",
        "desc": "Mobile Login",
        "keywords": "personal account, personal login, singpass, mobile"
    },
    {
        "label": "Access Code & PIN",
        "url": "/login",
        "icon": "key-round",
        "desc": "Standard Login",
        "keywords": "personal account, personal login, access code, password"
    },
    {
        "label": "OneToken / SMS OTP",
        "url": "/send-otp",
        "icon": "shield-check",
        "desc": "Security Token & 2FA",
        # CRITICAL: "personal account" is here so it appears in the list
        "keywords": "personal account, personal login, otp, token, sms, 2fa"
    }
]


mydb = mysql.connector.connect(
    host='localhost',
    user='root',
    password=os.getenv('db_password'),
    port='3306',
    database=os.getenv('db_name')
)
mycursor = mydb.cursor()    # For accessing MySQL Database

account_sid = 'AC28b18e8e89c17c5b7e732e932043c52e'
auth_token = '8a5550abf8d7b38ce5ca4fb0938b5b4b'
client = Client(account_sid, auth_token)

QR_SESSIONS = {}


def send_otp(phone_number):
    verification = client.verify \
        .v2 \
        .services('VAe02e36b90fe1a3df4fdd47939baf0c11') \
        .verifications \
        .create(to=phone_number, channel='sms')
    return verification.sid

def check_otp(phone_number, otp_code):
    verification_check = client.verify \
        .v2 \
        .services('VAe02e36b90fe1a3df4fdd47939baf0c11') \
        .verification_checks \
        .create(to=phone_number, code=otp_code)
    return verification_check.status == "approved"

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Doesn't actually connect, just gets local IP
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

# 1. CONFIGURATION
app.config['BABEL_DEFAULT_LOCALE'] = 'en'
app.config['BABEL_SUPPORTED_LOCALES'] = ['en', 'zh', 'ms']


# 2. LANGUAGE SELECTOR
def get_locale():
    # Priority 1: URL parameter (e.g. ?lang=zh)
    lang = request.args.get('lang')
    if lang in app.config['BABEL_SUPPORTED_LOCALES']:
        session['language'] = lang
        return lang

    # Priority 2: Saved Session
    return session.get('language', request.accept_languages.best_match(app.config['BABEL_SUPPORTED_LOCALES']))


# 3. INITIALIZE BABEL
babel = Babel(app, locale_selector=get_locale)


@app.context_processor
def inject_conf_var():
    return dict(
        get_locale=get_locale,
        current_language=get_locale()
    )


def initialize_database():
    try:
        mycursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(100) NOT NULL UNIQUE,
                password VARCHAR(255) NOT NULL,
                access_code VARCHAR(20),
                pin VARCHAR(20)
            )
        """)

        # Insert test user
        mycursor.execute("""
            INSERT IGNORE INTO users (username, password, access_code, pin)
            VALUES (%s, %s, %s, %s)
        """, ("Clara Lim", "password", "A12345B", "123456"))

        mydb.commit()

        print("Database initialized and test user added.")

    except Exception as e:
        print("Error initializing database:", e)


@app.route('/', methods=['GET', 'POST'])
def home():
    return render_template('homepage.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        access_code = request.form.get('access_code')
        pin = request.form.get('pin')

        print("User submitted:", access_code, pin)  # Debug

        # Query database
        mycursor.execute("""
            SELECT * FROM users
            WHERE access_code = %s AND pin = %s
        """, (access_code, pin))

        user = mycursor.fetchone()

        if user:
            session['logged_in'] = True
            session['user_id'] = user[0]  # user_id column
            return redirect(url_for('home'))  # redirect to homepage

        # If wrong access code or PIN
        return render_template('login.html', error="Invalid Access Code or PIN")

    return render_template('login.html')


@app.route('/home/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))


@app.route('/login/business')
def login_business():
    return render_template('login_business.html')


# --- THE LANGUAGE SWITCHER ROUTE ---
@app.route('/set_language/<lang_code>')
def set_language(lang_code):
    # 1. Validate the language
    if lang_code in app.config['BABEL_SUPPORTED_LOCALES']:
        # 2. Save to session
        session['language'] = lang_code

    # 3. Redirect back to home
    return redirect(url_for('home'))


@app.route('/api/navigate', methods=['POST'])
def navigate():
    data = request.get_json()
    user_query = data.get('message', '').lower()

    if not user_query or len(user_query) < 2:
        return jsonify({"suggestions": []})

    # We use strict RULES to force the AI to behave exactly as you want
    prompt = f"""
    You are a precise navigation engine for OCBC Bank.

    User Input: "{user_query}"
    Data Source: {json.dumps(SITE_MAP)}

    STRICT RULES:
    1. IF input is GENERIC (e.g., "login", "i wanna login"):
       - Show ONLY the Level 1 Categories (Personal Banking Login, Business Login).
       - Do NOT show specific methods like Singpass or OTP yet.

    2. IF input specifies "PERSONAL" or "PERSONAL ACCOUNT":
       - You MUST return ALL 3 items related to personal login:
         1. Log in with Singpass
         2. Access Code & PIN
         3. OneToken / SMS OTP
       - Do not leave out the OTP option.

    3. IF input specifies "BUSINESS":
       - Show Business Login options.

    Return JSON: {{ "suggestions": [ ... ] }}
    """

    try:
        # Using Gemini to process the logic
        response = model.generate_content(prompt)
        result = json.loads(response.text)
        return jsonify(result)

    except Exception as e:
        print(f"Gemini Error: {e}")
        return jsonify({"suggestions": []})

# login otp
@app.route('/send-otp', methods=['GET', 'POST'])
def send_otp_route():
    if request.method == 'POST':
        country_code = request.form.get('country_code')
        phone = request.form.get('phone')
        phone_number = f"{country_code}{phone}"
        session['phone_number'] = phone_number
        try:
            # Try sending OTP via Twilio (can fail for many reasons)
            otp_sid = send_otp(phone_number)
        except Exception as e:
            error_message = f"Error sending OTP: {str(e)}"
            # Pass error message to custom error page
            return render_template('error.html') #, error_message=error_message)
        # If all okay, proceed to verification page
        return render_template('verify_otp.html', phone=phone_number)
    return render_template('phone_otp.html')


@app.route('/verify-otp', methods=['POST'])
def verify_otp_route():
    phone_number = session.get('phone_number') or request.form.get('phone')
    otp_code = request.form.get('otp')

    verified = check_otp(phone_number, otp_code)

    if verified:
        session['logged_in'] = True              # ✅ mark user as logged in
        session['login_method'] = "phone_otp"    # optional: record method
        session['phone'] = phone_number          # optional: save phone
        return render_template('otp_result.html', status="success", phone=phone_number)

    else:
        return render_template('otp_result.html', status="fail", phone=phone_number)

@app.route('/error')
def error():
    # Optionally pass extra error message with: render_template('error.html', error_message="Custom info")
    return render_template('error.html')

@app.route('/login/qr')
def login_qr():
    qr_token = str(uuid.uuid4())
    QR_SESSIONS[qr_token] = {"status": "pending", "expires_at": time.time() + 60}
    ip_addr = get_local_ip()
    qr_url = f"http://{ip_addr}:5000/scan-qr/{qr_token}"
    qr_img_path = f"static/qr_{qr_token}.png"
    qrcode.make(qr_url).save(qr_img_path)
    return render_template('login_qr.html', qr_image_path=f'/static/qr_{qr_token}.png', qr_token=qr_token)

@app.route('/scan-qr/<qr_token>')
def scan_qr(qr_token):
    # User scans QR with mobile → this endpoint hit
    info = QR_SESSIONS.get(qr_token)
    if not info or info["expires_at"] < time.time():
        return "QR code expired or invalid", 400
    info["status"] = "authenticated"
    # Optionally, set session/cookie for logged-in user here or redirect
    session['logged_in'] = True
    return "QR Code scanned! You are logged in."

@app.route('/api/qr-status/<qr_token>')
def qr_status(qr_token):
    info = QR_SESSIONS.get(qr_token)
    if not info:
        return jsonify(status="expired")

    if info["status"] == "authenticated":
        session['logged_in'] = True  # <- now the browser gets the session
    return jsonify(status=info["status"])



if __name__ == '__main__':
    initialize_database()
    app.run(host="0.0.0.0")
