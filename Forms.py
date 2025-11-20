from flask_wtf import FlaskForm
from dotenv import load_dotenv
from wtforms import Form, StringField, SelectField, EmailField, validators, DecimalField, FileField, TimeField, DateField, TextAreaField, IntegerField, ValidationError, SubmitField
from flask import session
import mysql.connector
import os
load_dotenv()


mydb = mysql.connector.connect(
    host='localhost',
    user='root',
    password=os.getenv('db_password'),
    port='3306',
    database=os.getenv('db_name')
)
mycursor = mydb.cursor()


class CreateSearchForm_Admin(FlaskForm):
    name = StringField('Username', [validators.Length(min=1, max=50)])
    role = SelectField('Roles', [], choices=[('', 'None'), ('staff', 'Staff'), ('manager', 'Manager')], default='')
