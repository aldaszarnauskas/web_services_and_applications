from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
import re
from dotenv import load_dotenv
import os
from google import genai
from get_a_dialogue import get_a_dialogue # Custom made app


load_dotenv()

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///mydatabase.db"
db = SQLAlchemy(app)

class Account(db.Model):
    __tablename__ = 'accounts'   
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False, unique=True)
    password = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(100), nullable=False, unique=True
                      )
    
with app.app_context():
    db.create_all()





@app.route('/')
@app.route('/login', methods=['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        user = Account.query.filter_by(
            username=request.form["username"],
            password=request.form["password"]
        ).first()
        
        if user:
            session['loggedin'] = True
            session['id'] = user.id
            session['username'] = user.username
            return render_template('index.html', msg='Logged in successfully!')
        else:
            msg = 'Incorrect username/password!'
    return render_template('index.html', msg=msg)

@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    msg = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form:
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']

        # Check if username already exists
        account = Account.query.filter_by(username=username).first()

        if account:
            msg = 'Account already exists!'
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            msg = 'Invalid email address!'
        elif not re.match(r'[A-Za-z0-9]+', username):
            msg = 'Username must contain only letters and numbers!'
        elif not username or not password or not email:
            msg = 'Please fill out the form!'
        else:
            new_account = Account(
                username=username,
                password=password,
                email=email
            )
            db.session.add(new_account)
            db.session.commit()
            msg = 'You have successfully registered!'

    return render_template('register.html', msg=msg)

@app.route('/language_learning', methods=['GET', 'POST'])
def language_learning():

    if request.method == 'POST' and 'primary_language' in request.form and 'cambridge_level' in request.form and 'secondary_language' in request.form and 'dialogue_length' in request.form:
        primary_language = request.form['primary_language']
        cambridge_level = request.form['cambridge_level']
        secondary_language = request.form['secondary_language']
        dialogue_length = request.form['dialogue_length']

        response = get_a_dialogue(primary_language, cambridge_level, secondary_language, dialogue_length)

        return render_template("translation_practise.html", response=response)
    

    return render_template("language_learning.html")

@app.route('/translate_language', methods=['GET', 'POST'])
def translate_language():
    return render_template('translation_practise.html')

if __name__ == '__main__':
    app.run(debug=True)