from dotenv import load_dotenv
from flask import Flask
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from os import path, getenv

db = SQLAlchemy()
migrate = Migrate()
bcrypt_extension = Bcrypt()
DB_NAME = 'education_db'
# limiter = Limiter(
#     key_func=get_remote_address,
#     default_limits=["3 per minute"]
# )


def create_app():
    app = Flask(__name__)
    load_dotenv()

    app.config['SECRET_KEY'] = getenv('SECRET_KEY')
    app.config['SQLALCHEMY_DATABASE_URI'] = getenv('SQLALCHEMY_DATABASE_URI')

    db.init_app(app)
    bcrypt_extension.init_app(app)
    migrate.init_app(app, db)
    # limiter.init_app(app)

    from .views import views
    from .auth import auth

    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/')

    from .models import User

    with app.app_context():
        create_database()

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))

    return app


def create_database():
    if not path.exists('website/' + DB_NAME):
        db.create_all()
