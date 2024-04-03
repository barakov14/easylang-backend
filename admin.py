from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from models import ProjectModel, UserModel
from db import db

admin = Admin()

def setup_admin(app):
    admin.init_app(app)
    admin.add_view(ModelView(ProjectModel, db.session))
    admin.add_view(ModelView(UserModel, db.session))
