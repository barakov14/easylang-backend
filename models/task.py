from db import db
from datetime import datetime


class TaskSubmissionModel(db.Model):
    __tablename__ = 'task_submissions'

    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String)
    grade = db.Column(db.Integer)
    status = db.Column(db.String, default='IN PROGRESS')
    pages_done = db.Column(db.Integer)
    comment = db.Column(db.String)
    translator_id = db.Column(db.Integer, db.ForeignKey('users.id'))


class TaskModel(db.Model):
    __tablename__ = 'tasks'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='IN PROGRESS')
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    deadline = db.Column(db.DateTime, nullable=True)
    pages = db.Column(db.Integer, nullable=False)
    rejected = db.Column(db.Integer, default=0)
    progress = db.Column(db.Integer, default=0)
    code = db.Column(db.Integer, nullable=False)
    responsibles = db.relationship('UserModel', secondary='task_responsibles')
    submissions = db.relationship('TaskSubmissionModel', backref='task', secondary='task_submitted')


class TaskResponsiblesModel(db.Model):
    __tablename__ = 'task_responsibles'

    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)


class TaskSubmittedModel(db.Model):
    __tablename__ = 'task_submitted'

    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), primary_key=True)
    submission_id = db.Column(db.Integer, db.ForeignKey('task_submissions.id'), primary_key=True)
