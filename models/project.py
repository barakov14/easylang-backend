from db import db
from datetime import datetime


class ProjectModel(db.Model):
    __tablename__ = 'projects'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    color = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), default="NEW")
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    ended_at = db.Column(db.DateTime, nullable=True, default=None)
    progress = db.Column(db.Float, default=0)
    number_of_pages = db.Column(db.Integer)
    deadline = db.Column(db.String(255))
    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    creator = db.relationship('UserModel', backref='projects_created_by_user', secondary='project_creators')

    editors = db.relationship('UserModel', backref='edited_projects', secondary='project_editors')

    translators = db.relationship('UserModel', backref='translated_projects', secondary='project_translators')

    tasks = db.relationship('TaskModel', backref='projects', secondary='project_tasks')



class ProjectEditorsModel(db.Model):
    __tablename__ = 'project_editors'

    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)

class ProjectTranslatorsModel(db.Model):
    __tablename__ = 'project_translators'

    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)


class ProjectCreatorsModel(db.Model):
    __tablename__ = 'project_creators'

    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)

class ProjectTasksModel(db.Model):
    __tablename__ = 'project_tasks'

    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), primary_key=True)

    # Определяем отношение между таблицей project_tasks и таблицей projects
    # project = db.relationship('ProjectModel', backref=db.backref('tasks_associated', cascade='all, delete-orphan'))
    #
    # Определяем отношение между таблицей project_tasks и таблицей tasks
    # task = db.relationship('TaskModel', backref=db.backref('projects_associated', cascade='all, delete-orphan'))


