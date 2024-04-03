from db import db
from datetime import datetime


class ProjectModel(db.Model):
    __tablename__ = 'projects'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='in_process')
    started_at = db.Column(db.String, default=datetime.utcnow)
    ended_at = db.Column(db.String, nullable=True, default=None)
    progress = db.Column(db.Integer, default=0)
    number_of_chapters = db.Column(db.Integer)
    editors = db.relationship('UserModel', backref='projects', secondary='project_editors')
    tasks = db.relationship('TaskModel', backref='projects', secondary='project_tasks')


class ProjectEditorsModel(db.Model):
    __tablename__ = 'project_editors'

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
