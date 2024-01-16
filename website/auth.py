import os, requests
from dotenv import load_dotenv
from flask import Blueprint, render_template, request, flash, redirect, url_for, abort, session, jsonify
from flask_login import login_user, login_required, logout_user, current_user
from flask_limiter import RateLimitExceeded
from website import db
from website.models import User
from website import bcrypt_extension
from email_validator import validate_email, EmailNotValidError
# from . import limiter

auth = Blueprint('auth', __name__)
load_dotenv()

SITE_KEY = os.getenv('SITE_KEY')
SECRET_KEY = os.getenv('SECRET_KEY')
VERIFY_URL = os.getenv('VERIFY_URL')


# Error handler fonksiyonu, RateLimitExceeded exceptionunda direkt çağırılıyor, 429=too many requests
# @auth.errorhandler(RateLimitExceeded)
# def rate_limit_exceeded(e):
#     flash('Too many login attempts. Please try again in a minute.', category='error')
#     return render_template("login.html", user=current_user, site_key=SITE_KEY), 429


@auth.route('/signup', methods=['GET', 'POST'])
def sign_up():
    if current_user.is_authenticated:
        flash("Access Denied: First you need to logout before signing up!", 'error')
        return redirect(url_for('views.home'))

    if request.method == 'POST':
        bcrypt = bcrypt_extension
        secret_response = request.form['g-recaptcha-response']
        verify_response = requests.post(url=f'{VERIFY_URL}?secret={SECRET_KEY}&response={secret_response}').json()

        if verify_response['success']:
            special_chars = "!@#$%^&*()-_=+[]{};:',.<>/?"
            email = request.form.get('email')
            firstName = request.form.get('firstName')
            password1 = request.form.get('password1')
            password2 = request.form.get('password2')
            user = User.query.filter_by(email=email).first()

            try:
                validate = validate_email(email)
                email = validate["email"]
            except EmailNotValidError as e:
                flash('Please enter a valid email!', category='error')
                return render_template("sign_up.html", user=current_user, site_key=SITE_KEY)

            if user:
                flash('Email already exists!', category='error')
            elif len(firstName) < 2:
                flash('Name length must be greater than 1 characters!', category='error')
            elif any(char.isdigit() for char in firstName):
                flash('Name parameter can\'t have numbers!', category='error')
            elif password1 != password2:
                flash('Passwords don\'t match.', category='error')
            elif len(password1) < 10:
                flash('Passwords must be at least 10 characters.', category='error')
            elif not any(char in special_chars for char in password1):
                flash('Password must include special characters!', category='error')
            elif not any(char.isdigit() for char in password1):
                flash('Password must include at least one number!', category='error')
            elif not any(char.islower() for char in password1):
                flash('Password must include at least one lowercase letter!', category='error')
            elif not any(char.isupper() for char in password1):
                flash('Password must include at least one uppercase letter!', category='error')
            else:
                current_directory = os.path.dirname(os.path.realpath(__file__))
                file_path = os.path.join(current_directory, 'static', 'top100badpasswords.txt')

                with open(file_path, 'r') as file:
                    bad_passwords = [line.strip() for line in file.readlines()]

                    if password1 in bad_passwords:
                        flash('Password too common. Please choose a stronger password', category='error')
                    else:
                        new_user = User(email=email, firstName=firstName, role="student",
                                        password=bcrypt.generate_password_hash(password1).decode('utf-8'))
                        db.session.add(new_user)
                        db.session.commit()
                        login_user(new_user)
                        flash('Account created!', category='success')
                        return redirect(url_for('views.home'))
        else:
            abort(401)

    return render_template("sign_up.html", user=current_user, site_key=SITE_KEY)


@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        flash("Access Denied: First you need to logout before logging in!", 'error')
        return redirect(url_for('views.home'))

    if request.method == 'POST':
        bcrypt = bcrypt_extension
        secret_response = request.form['g-recaptcha-response']
        verify_response = requests.post(url=f'{VERIFY_URL}?secret={SECRET_KEY}&response={secret_response}').json()

        if verify_response['success']:
            email = request.form.get('email')
            password = request.form.get('password')
            user = User.query.filter_by(email=email).first()

            if user:
                if bcrypt.check_password_hash(user.password, password):
                    login_user(user, remember=True)
                    flash('Logged in', category='success')
                    return redirect(url_for('views.home'))
                else:
                    flash('Incorrect password, try again!', category='error')
            else:
                flash('Email does not exist!', category='error')
        else:
            abort(401)

    return render_template("login.html", user=current_user, site_key=SITE_KEY)


@auth.route('/logout')
@login_required
def logout():
    session.clear()
    logout_user()
    return redirect(url_for('views.home'))


# This is for logging out users after some time
@auth.route('/check_login_status', methods=['POST'])
def check_login_status():
    if current_user.is_authenticated:
        return jsonify({'isLoggedIn': True})
    else:
        return jsonify({'isLoggedIn': False})
