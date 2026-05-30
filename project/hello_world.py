from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
import re
from dotenv import load_dotenv
import os
from google import genai
from get_a_dialogue import get_a_dialogue
from sqlalchemy.sql.expression import func
import json

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

# Point SQLite database to the same folder as this file
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(BASE_DIR, "mydatabase.db")
db = SQLAlchemy(app)


# Stores user login credentials
class Account(db.Model):
    __tablename__ = 'accounts'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False, unique=True)
    password = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(100), nullable=False, unique=True)


# Linked to accounts via foreign key — stores each user's language preferences
class Choices(db.Model):
    __tablename__ = 'default_choices'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    default_parameters = db.Column(db.Boolean(), nullable=False, default=False)
    primary_language = db.Column(db.String(255), nullable=True)
    secondary_language = db.Column(db.String(255), nullable=True)
    lang_level = db.Column(db.String(255), nullable=True)
    dialogue_length = db.Column(db.Integer, nullable=True)


class Dialogue(db.Model):
    __tablename__ = 'dialogues'
    id = db.Column(db.Integer, primary_key=True)
    topic = db.Column(db.String(255), nullable=True)
    lang_level = db.Column(db.String(10), nullable=False)
    length = db.Column(db.Integer, nullable=False)

    lines = db.relationship(
        'DialogueLine',
        backref='dialogue',
        order_by='DialogueLine.line_number',
        cascade='all, delete-orphan'
    )


class DialogueLine(db.Model):
    __tablename__ = 'dialogue_lines'
    id = db.Column(db.Integer, primary_key=True)
    dialogue_id = db.Column(db.Integer, db.ForeignKey('dialogues.id'), nullable=False)
    line_number = db.Column(db.Integer, nullable=False)
    speaker_name = db.Column(db.String(50), nullable=False)

    # European languages
    lithuanian = db.Column(db.Text, nullable=True)
    latvian = db.Column(db.Text, nullable=True)
    estonian = db.Column(db.Text, nullable=True)
    english = db.Column(db.Text, nullable=True)
    german = db.Column(db.Text, nullable=True)
    french = db.Column(db.Text, nullable=True)
    spanish = db.Column(db.Text, nullable=True)
    italian = db.Column(db.Text, nullable=True)
    portuguese = db.Column(db.Text, nullable=True)
    dutch = db.Column(db.Text, nullable=True)
    polish = db.Column(db.Text, nullable=True)
    ukrainian = db.Column(db.Text, nullable=True)
    russian = db.Column(db.Text, nullable=True)
    swedish = db.Column(db.Text, nullable=True)
    norwegian = db.Column(db.Text, nullable=True)
    danish = db.Column(db.Text, nullable=True)
    finnish = db.Column(db.Text, nullable=True)
    greek = db.Column(db.Text, nullable=True)

    # American languages
    brazilian_portuguese = db.Column(db.Text, nullable=True)

    # Asian languages
    mandarin = db.Column(db.Text, nullable=True)
    japanese = db.Column(db.Text, nullable=True)
    korean = db.Column(db.Text, nullable=True)
    hindi = db.Column(db.Text, nullable=True)
    vietnamese = db.Column(db.Text, nullable=True)

    # Middle Eastern / African
    arabic = db.Column(db.Text, nullable=True)


# Create tables if they don't exist yet
with app.app_context():
    db.create_all()


# ---- Main Pages ----

@app.route('/')
@app.route('/home', methods=['GET'])
def home():
    return render_template('home.html')


# Checks username and password against the database
@app.route('/login', methods=['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        user = Account.query.filter_by(
            username=request.form["username"],
            password=request.form["password"]
        ).first()

        if user:
            # Store user info in session so other routes can identify them
            session['loggedin'] = True
            session['id'] = user.id
            session['username'] = user.username
            return redirect(url_for('select_languages'))
        else:
            msg = 'Incorrect username/password!'
    return render_template('login.html', msg=msg)


# Clears the session and sends user back to home
@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('username', None)
    return redirect(url_for('home'))


# Validates input, creates an account and saves default language preferences
@app.route('/register', methods=['GET', 'POST'])
def register():
    msg = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form:
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']

        # Read optional language preferences from the form
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
            new_account = Account(username=username, password=password, email=email)
            db.session.add(new_account)
            db.session.commit()  # commit first so new_account.id is available

            # Save the language preferences linked to the new account
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


# ---- Account Settings ----

# Loads the account settings page with the user's current preferences
@app.route('/account_settings', methods=['GET'])
def account_settings():
    if not session.get('loggedin'):
        return redirect(url_for('login'))
    defaults = Choices.query.filter_by(account_id=session['id']).first()
    return render_template('account_settings.html', defaults=defaults)


# Updates language preferences — creates a new record if none exists yet
@app.route('/update_settings', methods=['PUT'])
def update_settings():
    if not session.get('loggedin'):
        return jsonify({'error': 'Not logged in'}), 401

    data = request.get_json()
    defaults = Choices.query.filter_by(account_id=session['id']).first()

    if defaults:
        defaults.primary_language = data['primary_language']
        defaults.secondary_language = data['secondary_language']
        defaults.lang_level = data['lang_level']
        defaults.dialogue_length = data['dialogue_length']
    else:
        # User registered without setting preferences so create them now
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


# Requires current password before allowing any changes to login details
@app.route('/update_user', methods=['PUT'])
def update_user():
    if not session.get('loggedin'):
        return jsonify({'error': 'Not logged in'}), 401

    data = request.get_json()
    user = Account.query.filter_by(id=session['id']).first()

    # Reject the request if the current password is wrong
    if data.get('current_password') != user.password:
        return jsonify({'error': 'Incorrect password'}), 403

    # Only update fields that were actually provided
    if data.get('username'):
        existing = Account.query.filter_by(username=data['username']).first()
        if existing and existing.id != session['id']:
            return jsonify({'error': 'Username already taken'}), 400
        user.username = data['username']
        session['username'] = data['username']  # keep session in sync

    if data.get('password'):
        user.password = data['password']

    if data.get('email'):
        user.email = data['email']

    db.session.commit()
    return jsonify({'msg': 'Details updated successfully'})


# Deletes preferences first, then the account, then clears the session
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


# ---- Language Practice ----

# Loads the language selection form with the user's saved defaults pre-filled
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

        # Call Gemini API to generate the dialogue
        response = get_a_dialogue(primary, level, secondary, length)

        # Store in session so the practice page can access it without re-generating
        session['current_practice'] = response
        session['current_lang_code'] = secondary

        return redirect(url_for('translation_practice'))

    return render_template("select_languages.html")


# Redirects to language selection if no dialogue has been generated yet
@app.route('/translation_practice')
def translation_practice():
    if 'current_practice' not in session:
        return redirect(url_for('select_languages'))

    return render_template(
        "translation_practice.html",
        response=session['current_practice'],
        lang_code=session['current_lang_code']
    )





#---- PWA app like experience ----#
# Serve service worker from root so it can control the whole site
@app.route('/sw.js')
def service_worker():
    return app.send_static_file('sw.js'), 200, {
        'Content-Type': 'application/javascript',
        'Cache-Control': 'no-cache'
    }


# ---- Stored Dialogue Practice ----

# Page to browse and select stored dialogues
@app.route('/browse_dialogues', methods=['GET'])
def browse_dialogues():

    levels = db.session.query(Dialogue.lang_level).distinct().all()
    levels = [l[0] for l in levels]

    level_order = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']
    levels = sorted(levels, key=lambda x: level_order.index(x) if x in level_order else 99)

    return render_template("browse_dialogues.html", levels=levels)


# API route — get a random stored dialogue
@app.route('/api/stored_dialogue', methods=['GET'])
def api_stored_dialogue():
    if not session.get('loggedin'):
        return jsonify({'error': 'Not logged in'}), 401

    level = request.args.get('lang_level', 'A1')
    primary = request.args.get('primary_language', 'english')
    secondary = request.args.get('secondary_language', 'lithuanian')

    # Map language names to column names
    lang_map = {
        'lithuanian': 'lithuanian',
        'latvian': 'latvian',
        'estonian': 'estonian',
        'english': 'english',
        'german': 'german',
        'french': 'french',
        'spanish': 'spanish',
        'italian': 'italian',
        'portuguese': 'portuguese',
        'dutch': 'dutch',
        'polish': 'polish',
        'ukrainian': 'ukrainian',
        'russian': 'russian',
        'swedish': 'swedish',
        'norwegian': 'norwegian',
        'danish': 'danish',
        'finnish': 'finnish',
        'greek': 'greek',
        'brazilian_portuguese': 'brazilian_portuguese',
        'mandarin': 'mandarin',
        'japanese': 'japanese',
        'korean': 'korean',
        'hindi': 'hindi',
        'vietnamese': 'vietnamese',
        'arabic': 'arabic',
    }

    primary_col = lang_map.get(primary, 'english')
    secondary_col = lang_map.get(secondary, 'lithuanian')

    # Get a random dialogue at the chosen level
    dialogue = Dialogue.query.filter_by(
        lang_level=level
    ).order_by(func.random()).first()

    if not dialogue:
        return jsonify({'error': f'No dialogues found for level {level}'}), 404

    lines = []
    for dl in dialogue.lines:
        primary_text = getattr(dl, primary_col) or ''
        secondary_text = getattr(dl, secondary_col) or ''
        if primary_text:
            lines.append({
                'id': dl.line_number,
                'name': dl.speaker_name,
                'primary_lang': primary_text,
                'secondary_lang': secondary_text
            })

    return jsonify({
        'id': dialogue.id,
        'topic': dialogue.topic,
        'lang_level': dialogue.lang_level,
        'lines': lines
    })



if __name__ == '__main__':
    app.run(debug=True)