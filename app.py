import os
from datetime import timedelta

from celery import Celery
from flask import Flask
from flask_smorest import Api
from flask_jwt_extended import JWTManager
from flask_mail import Mail
from admin import setup_admin
from db import db
from resources.user import blp as UserBlueprint
from resources.project import blp as ProjectBlueprint
from resources.task import blp as TaskBlueprint
from resources.notifications import blp as NotificationBlueprint
from blocklist import BLOCKLIST

def make_celery(app):
    celery = Celery(
        app.import_name,
        broker=app.config['CELERY_BROKER_URL'],
        backend=app.config['CELERY_RESULT_BACKEND']
    )
    celery.conf.update(app.config)
    return celery

def create_app(db_url=None):
    app = Flask(__name__)

    # Настройки конфигурации
    app.config["PROPAGATE_EXCEPTIONS"] = True
    app.config["API_TITLE"] = "EasyLang REST API"
    app.config["API_VERSION"] = "v1"
    app.config["OPENAPI_VERSION"] = "3.0.3"
    app.config["OPENAPI_URL_PREFIX"] = "/"
    app.config["OPENAPI_SWAGGER_UI_PATH"] = "/swagger-ui"
    app.config["OPENAPI_SWAGGER_UI_URL"] = "https://cdn.jsdelivr.net/npm/swagger-ui-dist/"
    app.config["SQLALCHEMY_DATABASE_URI"] = db_url or os.getenv("DATABASE_URI", "sqlite:///data.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["JWT_SECRET_KEY"] = "adilkhan"
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(days=14)
    app.config['MAIL_SERVER'] = 'smtp.mailtrap.io'
    app.config['MAIL_PORT'] = 2525
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USE_SSL'] = False
    app.config['MAIL_USERNAME'] = 'playmagma4@gmail.com'
    app.config['MAIL_PASSWORD'] = '607215296b88690a86fb8020597f659e'
    app.config['DEBUG'] = True
    app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
    app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/0'

    jwt = JWTManager(app)

    @jwt.additional_claims_loader
    def add_claims_to_jwt(identity):
        if identity == 1:
            return {"isAdmin": True}
        return {"isAdmin": False}

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return {"message": "Token Expired"}, 401

    @jwt.token_in_blocklist_loader
    def check_if_token_in_blocklist(jwt_header, jwt_payload):
        return jwt_payload["jti"] in BLOCKLIST

    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        return {"message": "The token has been revoked"}, 401

    # Инициализация базы данных
    db.init_app(app)

    # Создание API
    api = Api(app)

    # Флаг для отслеживания, была ли уже выполнена инициализация базы данных
    initialized = False

    @app.before_request
    def create_tables():
        nonlocal initialized
        if not initialized:
            db.create_all()
            initialized = True

    # Регистрация blueprint'ов
    api.register_blueprint(UserBlueprint)
    api.register_blueprint(ProjectBlueprint)
    api.register_blueprint(TaskBlueprint)
    api.register_blueprint(NotificationBlueprint)

    setup_admin(app)
    mail = Mail()

    # Подключение и настройка Celery
    celery = make_celery(app)

    return app
