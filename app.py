import os
import json
import google.generativeai as genai # CHANGED: Import Google Library
from flask import Flask, render_template, request, url_for, jsonify, redirect, session
from flask_babel import Babel, gettext as _
from dotenv import load_dotenv
from Forms import CreateSearchForm_Admin
import mysql.connector
load_dotenv()


app = Flask(__name__)
genai.configure(api_key=os.getenv('api_key'))
app.secret_key = os.getenv('secret_key', 'my_fallback_secret_key_123')

model = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
    generation_config={"response_mime_type": "application/json"}
)

# Define the valid pages the AI can recommend
SITE_MAP = [
{
        "label": "Personal Login",
        "url": "/login",
        "icon": "user",
        "desc": "Internet Banking",
        "keywords": "login, sign in, access, user, password, account"
    },
    {
        "label": "Business Login",
        "url": "/login/business",
        "icon": "briefcase",
        "desc": "Velocity @ OCBC",
        "keywords": "login, sign in, access, sme, corporate, velocity"
    },
    {
        "label": "Open 360 Account",
        "url": "/personal/accounts/360",
        "icon": "wallet",
        "desc": "High interest savings",
        "keywords": "create, new, register, signup, save, money"
    },
    {"label": "Personal Login", "url": "/login", "icon": "user"},
    {"label": "Business Login (Velocity)", "url": "/login/business", "icon": "briefcase"},
    {"label": "Open 360 Account", "url": "/personal/accounts/360", "icon": "wallet"},
    {"label": "Frank Account (Youth)", "url": "/personal/accounts/frank", "icon": "smile"},
    {"label": "Credit Card Application", "url": "/personal/cards/apply", "icon": "credit-card"},
    {"label": "Contact Customer Service", "url": "/support/contact", "icon": "phone"},
]


mydb = mysql.connector.connect(
    host='localhost',
    user='root',
    password=os.getenv('db_password'),
    port='3306',
    database=os.getenv('db_name')
)
mycursor = mydb.cursor()    # For accessing MySQL Database


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
                email VARCHAR(100),
                role ENUM('member', 'staff', 'manager') NOT NULL
            )
        """)


        mydb.commit()
        print("Database initialized.")
    except Exception as e:
        print("Error initializing database:", e)


@app.route('/', methods=['GET', 'POST'])
def home():
    return render_template('homepage.html')


@app.route('/login')
def login():
    return render_template('login.html')


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
    user_query = data.get('message', '')

    if not user_query or len(user_query) < 2:
        return jsonify({"suggestions": []})

    # IMPROVED PROMPT
    prompt = f"""
    You are a navigation router for OCBC.

    User Input: "{user_query}"

    Task: Match the input to the following Site Map:
    {json.dumps(SITE_MAP)}

    CRITICAL RULES:
    1. If the user input is generic (e.g., "login", "sign in"), you MUST return ALL login options (both Personal and Business).
    2. If the user specifies a type (e.g., "business login"), return ONLY that specific one.
    3. Return a JSON object: {{ "suggestions": [ {{ "label": "...", "url": "...", "icon": "...", "desc": "..." }} ] }}
    """

    try:
        response = model.generate_content(prompt)
        result = json.loads(response.text)
        return jsonify(result)

    except Exception as e:
        print(f"Gemini Error: {e}")
        return jsonify({"suggestions": []})


if __name__ == '__main__':
    app.run()
