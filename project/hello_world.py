from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
import re
from dotenv import load_dotenv
import os
from google import genai
from get_a_dialogue import get_a_dialogue
from sqlalchemy.sql.expression import func
import json
import stripe
from datetime import date
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
import secrets

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
STRIPE_PUBLISHABLE_KEY = os.getenv('STRIPE_PUBLISHABLE_KEY')
STRIPE_PRICE_ID = os.getenv('STRIPE_PRICE_ID')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')

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
    role = db.Column(db.String(20), nullable=False, default='free')
    stripe_customer_id = db.Column(db.String(100), nullable=True)
    stripe_subscription_id = db.Column(db.String(100), nullable=True)
    subscription_active = db.Column(db.Boolean, nullable=False, default=False)
    email_verified = db.Column(db.Boolean, nullable=False, default=False)  


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


class SubscriptionEvent(db.Model):
    __tablename__ = 'subscription_events'
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    event_type = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.now())
    stripe_event_id = db.Column(db.String(100), nullable=True)

class DialogueUsage(db.Model):
    __tablename__ = 'dialogue_usage'
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=db.func.current_date())
    count = db.Column(db.Integer, nullable=False, default=0)


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
            if not user.email_verified:
                msg = 'Please confirm your email before logging in. Check your inbox.'
            else:
                session['loggedin'] = True
                session['id'] = user.id
                session['username'] = user.username
                session['user_role'] = user.role
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
            password_error = is_strong_password(password)
            if password_error:
                msg = password_error
            else:
                # Create account but leave email_verified as False
                new_account = Account(
                    username=username,
                    password=password,
                    email=email,
                    email_verified=False
                )
                db.session.add(new_account)
                db.session.commit()

                new_default_parameters = Choices(
                    account_id=new_account.id,
                    default_parameters=True,
                    primary_language=primary,
                    secondary_language=secondary,
                    lang_level=level,
                    dialogue_length=int(length) if length else 10
                )
                db.session.add(new_default_parameters)
                db.session.commit()

                # Send confirmation email
                try:
                    send_confirmation_email(email)
                    msg = 'Registered! Please check your email to confirm your account.'
                except Exception as e:
                    print(f"Email error: {e}")
                    msg = 'Registered but could not send confirmation email. Contact support.'

    return render_template('register.html', msg=msg, defaults=None)

def is_strong_password(password):
    """Returns a message if the password is too weak, or None if it is strong enough."""
    if len(password) < 8:
        return 'Password must be at least 8 characters long.'
    if not re.search(r'[A-Z]', password):
        return 'Password must contain at least one uppercase letter.'
    if not re.search(r'[a-z]', password):
        return 'Password must contain at least one lowercase letter.'
    if not re.search(r'[0-9]', password):
        return 'Password must contain at least one number.'
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return 'Password must contain at least one special character (!@#$%^&* etc).'
    return None


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

    user = Account.query.filter_by(id=session['id']).first()

    # Check basic access first
    if not has_access(user):
        return redirect(url_for('pricing'))

    if request.method == 'GET':
        default_parameters = Choices.query.filter_by(account_id=session['id']).first()

        # Pass usage info to the template so we can show remaining generations
        daily_used = get_daily_usage(user.id)
        remaining = None
        if user.role == 'subscriber':
            remaining = DAILY_LIMIT - daily_used

        return render_template(
            "select_languages.html",
            defaults=default_parameters,
            remaining=remaining
        )

    elif request.method == 'POST':
        # Check if they have hit the daily limit
        if not can_generate(user):
            return render_template(
                "select_languages.html",
                defaults=Choices.query.filter_by(account_id=session['id']).first(),
                remaining=0,
                error="You have reached your 5 dialogue limit for today. Come back tomorrow!"
            )

        primary = request.form.get('primary_language')
        level = request.form.get('language_level')
        secondary = request.form.get('secondary_language')
        length = request.form.get('dialogue_length')

        response = get_a_dialogue(primary, level, secondary, length)

        # Only count it if the generation actually succeeded
        if response:
            increment_daily_usage(user.id)

        session['current_practice'] = response
        session['current_lang_code'] = secondary
        session['primary_language'] = primary
        session['secondary_language'] = secondary

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


#---- Stripe ----~

def has_access(user):
    """Returns True if the user is allowed to generate dialogues."""
    if user is None:
        return False
    if user.role in ('admin', 'member'):
        return True
    if user.role == 'subscriber' and user.subscription_active:
        return True
    return False


@app.route('/create_checkout_session', methods=['POST'])
def create_checkout_session():
    if not session.get('loggedin'):
        return redirect(url_for('login'))

    user = Account.query.filter_by(id=session['id']).first()

    # Create or reuse a Stripe customer so we can link them later
    if user.stripe_customer_id:
        customer_id = user.stripe_customer_id
    else:
        customer = stripe.Customer.create(email=user.email)
        user.stripe_customer_id = customer.id
        db.session.commit()
        customer_id = customer.id

    checkout_session = stripe.checkout.Session.create(
        customer=customer_id,
        payment_method_types=['card'],
        line_items=[{
            'price': STRIPE_PRICE_ID,
            'quantity': 1,
        }],
        mode='subscription',          # ← changed from 'payment' to 'subscription'
        success_url=url_for('payment_success', _external=True),
        cancel_url=url_for('pricing', _external=True),
        metadata={'user_id': str(user.id)}
    )

    return redirect(checkout_session.url)


@app.route('/stripe_webhook', methods=['POST'])
def stripe_webhook():
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        return '', 400
    except stripe.error.SignatureVerificationError:
        return '', 400

    if event['type'] in ('checkout.session.completed', 'invoice.payment_succeeded'):
        data = event['data']['object']
        customer_id = data.get('customer')
        subscription_id = data.get('subscription')

        if customer_id:
            user = Account.query.filter_by(stripe_customer_id=customer_id).first()
            if user:
                user.role = 'subscriber'
                user.subscription_active = True
                if subscription_id:
                    user.stripe_subscription_id = subscription_id

                # Log the event
                log = SubscriptionEvent(
                    account_id=user.id,
                    event_type=event['type'],
                    stripe_event_id=event['id']
                )
                db.session.add(log)
                db.session.commit()

    elif event['type'] in ('customer.subscription.deleted', 'invoice.payment_failed'):
        data = event['data']['object']
        customer_id = data.get('customer')

        if customer_id:
            user = Account.query.filter_by(stripe_customer_id=customer_id).first()
            if user and user.role == 'subscriber':
                user.subscription_active = False

                # Log the event
                log = SubscriptionEvent(
                    account_id=user.id,
                    event_type=event['type'],
                    stripe_event_id=event['id']
                )
                db.session.add(log)
                db.session.commit()

    return '', 200

@app.route('/cancel_subscription', methods=['POST'])
def cancel_subscription():
    if not session.get('loggedin'):
        return jsonify({'error': 'Not logged in'}), 401

    user = Account.query.filter_by(id=session['id']).first()

    if not user.stripe_subscription_id:
        return jsonify({'error': 'No active subscription found'}), 400

    # Cancel at period end so they keep access until the billing cycle ends
    stripe.Subscription.modify(
        user.stripe_subscription_id,
        cancel_at_period_end=True
    )

    return jsonify({'msg': 'Subscription will cancel at the end of the billing period'})



@app.route('/pricing')
def pricing():
    role = 'free'
    if session.get('loggedin'):
        user = Account.query.filter_by(id=session['id']).first()
        if user:
            role = user.role
    return render_template('pricing.html',
        stripe_key=STRIPE_PUBLISHABLE_KEY,
        current_user_role=role
    )

@app.route('/payment/success')
def payment_success():
    return render_template('payment_success.html')


@app.route('/payment/cancel')
def payment_cancel():
    return render_template('pricing.html',
        stripe_key=STRIPE_PUBLISHABLE_KEY,
        msg='Payment was cancelled.'
    )


#---- Admin ----#
@app.route('/admin/users')
def admin_users():
    if not session.get('loggedin'):
        return redirect(url_for('login'))

    user = Account.query.filter_by(id=session['id']).first()
    if user.role != 'admin':
        return redirect(url_for('home'))

    users = Account.query.all()

    # Get today's usage for all users in one query
    today = date.today()
    usage_records = DialogueUsage.query.filter_by(date=today).all()
    usage = {r.account_id: r.count for r in usage_records}

    return render_template(
        'admin_users.html',
        users=users,
        usage=usage,
        daily_limit=DAILY_LIMIT
    )

@app.route('/admin/update_role', methods=['POST'])
def admin_update_role():
    if not session.get('loggedin'):
        return jsonify({'error': 'Not logged in'}), 401

    me = Account.query.filter_by(id=session['id']).first()
    if me.role != 'admin':
        return jsonify({'error': 'Forbidden'}), 403

    data = request.get_json()
    user = Account.query.filter_by(id=data['user_id']).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    user.role = data['role']
    # Give free access to members and admins automatically
    if user.role in ('admin', 'member'):
        user.subscription_active = True
    db.session.commit()
    return jsonify({'msg': 'Role updated'})


@app.route('/admin/delete_user', methods=['DELETE'])
def admin_delete_user():
    if not session.get('loggedin'):
        return jsonify({'error': 'Not logged in'}), 401

    me = Account.query.filter_by(id=session['id']).first()
    if me.role != 'admin':
        return jsonify({'error': 'Forbidden'}), 403

    data = request.get_json()

    # Prevent deleting yourself
    if data['user_id'] == session['id']:
        return jsonify({'error': 'Cannot delete your own account'}), 400

    user = Account.query.filter_by(id=data['user_id']).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    Choices.query.filter_by(account_id=user.id).delete()
    db.session.delete(user)
    db.session.commit()
    return jsonify({'msg': 'User deleted'})




#---- User usaged ----#
def get_daily_usage(user_id):
    """Returns how many dialogues this user has generated today."""
    today = date.today()
    usage = DialogueUsage.query.filter_by(
        account_id=user_id,
        date=today
    ).first()
    return usage.count if usage else 0


def increment_daily_usage(user_id):
    """Adds one to today's dialogue count for this user."""
    today = date.today()
    usage = DialogueUsage.query.filter_by(
        account_id=user_id,
        date=today
    ).first()

    if usage:
        usage.count += 1
    else:
        usage = DialogueUsage(
            account_id=user_id,
            date=today,
            count=1
        )
        db.session.add(usage)

    db.session.commit()


DAILY_LIMIT = 5

def can_generate(user):
    """Returns True if the user is allowed to generate a dialogue right now."""
    if user is None:
        return False
    # Admins and members have unlimited generations
    if user.role in ('admin', 'member'):
        return True
    # Subscribers are limited to 5 per day
    if user.role == 'subscriber' and user.subscription_active:
        return get_daily_usage(user.id) < DAILY_LIMIT
    return False


#---- Email Confirmation ----#
# Mail configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_USERNAME')

mail = Mail(app)

# Used to generate and verify secure tokens
serializer = URLSafeTimedSerializer(app.secret_key)

def send_confirmation_email(user_email):
    # Generate a secure token that expires after 1 hour
    token = serializer.dumps(user_email, salt='email-confirm')

    confirm_url = url_for('confirm_email', token=token, _external=True)

    msg = Message(
        subject='Confirm your email — Active Language Learning',
        recipients=[user_email]
    )

    msg.html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 500px; margin: auto;">
        <h2 style="color: #236B8E;">Welcome to Active Language Learning!</h2>
        <p>Thank you for registering. Please confirm your email address by clicking the button below.</p>
        <a href="{confirm_url}"
           style="display:inline-block; background:#236B8E; color:white;
                  padding:14px 28px; border-radius:8px; text-decoration:none;
                  font-weight:bold; margin:20px 0;">
            Confirm Email
        </a>
        <p style="color:#999; font-size:0.85rem;">
            This link expires in 1 hour. If you did not register, ignore this email.
        </p>
    </div>
    """

    mail.send(msg)

@app.route('/confirm/<token>')
def confirm_email(token):
    try:
        # Token expires after 3600 seconds (1 hour)
        email = serializer.loads(token, salt='email-confirm', max_age=3600)
    except Exception:
        return render_template('confirm_result.html',
            success=False,
            message='This confirmation link is invalid or has expired. Please register again.'
        )

    user = Account.query.filter_by(email=email).first()

    if not user:
        return render_template('confirm_result.html',
            success=False,
            message='Account not found.'
        )

    if user.email_verified:
        return render_template('confirm_result.html',
            success=True,
            message='Your email is already confirmed. You can log in.'
        )

    user.email_verified = True
    db.session.commit()

    return render_template('confirm_result.html',
        success=True,
        message='Email confirmed! You can now log in.'
    )

if __name__ == '__main__':
    app.run(debug=True)