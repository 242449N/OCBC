import os
from flask import Flask, render_template, request, url_for, flash, redirect, session, Response
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



if __name__ == '__main__':
    app.run()
