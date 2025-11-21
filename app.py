import os
import json
from flask import Flask, render_template, request, url_for, jsonify, redirect, session
from translate import Translator
from flask_babel import Babel, gettext as _
from dotenv import load_dotenv
from Forms import CreateSearchForm_Admin
import mysql.connector
load_dotenv()


app = Flask(__name__)
app.secret_key = os.getenv('secret_key', 'my_fallback_secret_key_123')


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



if __name__ == '__main__':
    app.run()
