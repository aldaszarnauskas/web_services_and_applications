from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
import re
from dotenv import load_dotenv
import os
from google import genai
from get_a_dialogue import get_a_dialogue # Custom made app
# import base64
# import io
# from flask import send_file
# from google import genai
# from google.genai import types

# load_dotenv()
# client = genai.Client()




app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

##############################################################################
# SQL Alchemy
##############################################################################

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(BASE_DIR, "mydatabase.db")
db = SQLAlchemy(app)




class Account(db.Model):
    __tablename__ = 'accounts'   
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False, unique=True)
    password = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(100), nullable=False, unique=True)
    
class Choices(db.Model):
    __tablename__ = 'default_choices'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    default_parameters = db.Column(db.Boolean(), nullable=False, default=False)
    primary_language = db.Column(db.String(255), nullable=True)
    secondary_language = db.Column(db.String(255), nullable=True)
    lang_level = db.Column(db.String(255), nullable=True)
    dialogue_length = db.Column(db.Integer, nullable=True)

    
with app.app_context():
    db.create_all()

##############################################################################
# The Main Sites
##############################################################################

@app.route('/')
@app.route('/home', methods=['GET'])
def home():
    return render_template('home.html')


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
            return redirect(url_for('select_languages'))
        else:
            msg = 'Incorrect username/password!'
    return render_template('login.html', msg=msg)


@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('username', None)
    return redirect(url_for('home'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    msg = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form:
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']

        primary = request.form.get('primary_language')
        level = request.form.get('language_level')
        secondary = request.form.get('secondary_language')
        length = request.form.get('dialogue_length')

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
            db.session.commit()  # commit so new_account.id is generated

            new_default_parameters = Choices(
                account_id=new_account.id,
                default_parameters=True,
                primary_language=primary,
                secondary_language=secondary,
                lang_level=level,
                dialogue_length=int(length)
            )
            db.session.add(new_default_parameters)
            db.session.commit()

            msg = 'You have successfully registered!'

    return render_template('register.html', msg=msg, defaults=None)


##############################################################################
# Account Update Sites
##############################################################################


@app.route('/account_settings', methods=['GET'])
def account_settings():
    if not session.get('loggedin'):
        return redirect(url_for('login'))
    defaults = Choices.query.filter_by(account_id=session['id']).first()
    return render_template('account_settings.html', defaults=defaults)

@app.route('/update_settings', methods=['PUT'])
def update_settings():
    if not session.get('loggedin'):
        return jsonify({'error': 'Not logged in'}), 401

    data = request.get_json()

    defaults = Choices.query.filter_by(account_id=session['id']).first()

    if defaults:
        # Record exists — update it
        defaults.primary_language = data['primary_language']
        defaults.secondary_language = data['secondary_language']
        defaults.lang_level = data['lang_level']
        defaults.dialogue_length = data['dialogue_length']
    else:
        # No record yet — create one
        defaults = Choices(
            account_id=session['id'],
            default_parameters=True,
            primary_language=data['primary_language'],
            secondary_language=data['secondary_language'],
            lang_level=data['lang_level'],
            dialogue_length=data['dialogue_length']
        )
        db.session.add(defaults)

    db.session.commit()
    return jsonify({'msg': 'Settings updated successfully'})

@app.route('/update_user', methods=['PUT'])
def update_user():
    if not session.get('loggedin'):
        return jsonify({'error': 'Not logged in'}), 401

    data = request.get_json()
    user = Account.query.filter_by(id=session['id']).first()

    # Verify current password first
    if data.get('current_password') != user.password:
        return jsonify({'error': 'Incorrect password'}), 403

    # Update only provided fields
    if data.get('username'):
        existing = Account.query.filter_by(username=data['username']).first()
        if existing and existing.id != session['id']:
            return jsonify({'error': 'Username already taken'}), 400
        user.username = data['username']
        session['username'] = data['username']

    if data.get('password'):
        user.password = data['password']

    if data.get('email'):
        user.email = data['email']

    db.session.commit()
    return jsonify({'msg': 'Details updated successfully'})


@app.route('/delete_account', methods=['DELETE'])
def delete_account():
    if not session.get('loggedin'):
        return jsonify({'error': 'Not logged in'}), 401
    Choices.query.filter_by(account_id=session['id']).delete()
    account = Account.query.filter_by(id=session['id']).first()
    db.session.delete(account)
    db.session.commit()
    session.clear()
    return jsonify({'msg': 'Account deleted successfully'})


##############################################################################
# Language Practising Sites
##############################################################################


@app.route('/select_languages', methods=['GET', 'POST'])
def select_languages():
    if not session.get('loggedin'):
        return redirect(url_for('login'))

    if request.method == 'GET':
        default_parameters = Choices.query.filter_by(account_id=session['id']).first()
        return render_template("select_languages.html", defaults=default_parameters)


    elif request.method == 'POST':

        primary = request.form.get('primary_language')
        level = request.form.get('language_level')
        secondary = request.form.get('secondary_language')
        length = request.form.get('dialogue_length')

        response = get_a_dialogue(primary, level, secondary, length)


        session['current_practice'] = response
        session['current_lang_code'] = secondary


        return redirect(url_for('translation_practice'))

    return render_template("select_languages.html")


@app.route('/translation_practice')
def translation_practice():

    if 'current_practice' not in session:

        return redirect(url_for('select_languages'))


    return render_template(
        "translation_practice.html", 
        response=session['current_practice'], 
        lang_code=session['current_lang_code']
    )


if __name__ == '__main__':
    app.run(debug=True)