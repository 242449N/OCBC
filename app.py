import os
from flask import Flask, render_template, request, url_for, flash, redirect, session, Response
from dotenv import load_dotenv
from Forms import CreateSearchForm_Admin
import mysql.connector
load_dotenv()


app = Flask(__name__)

app.secret_key = os.getenv('secret_key')
mydb = mysql.connector.connect(
    host='localhost',
    user='root',
    password=os.getenv('db_password'),
    port='3306',
    database=os.getenv('db_name')
)
mycursor = mydb.cursor()    # For accessing MySQL Database



@app.route('/', methods=['GET', 'POST'])
def home():
    return render_template('homepage.html')


if __name__ == '__main__':
    app.run()
