from db import db
from datetime import datetime


class TaskSubmissionModel(db.Model):
    __tablename__ = 'task_submissions'

    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String)
    grade = db.Column(db.Integer)
    status = db.Column(db.String, default='in_process')


class TaskModel(db.Model):
    __tablename__ = 'tasks'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='in_process')
    started_at = db.Column(db.String, default=datetime.utcnow)
    deadline = db.Column(db.String)
    progress = db.Column(db.Integer, default=0)
    success = db.Column(db.Integer, default=100)
    responsibles = db.relationship('UserModel', secondary='task_responsibles')
    submissions = db.relationship('TaskSubmissionModel', backref='task', secondary='task_submitted')


class TaskResponsiblesModel(db.Model):
    __tablename__ = 'task_responsibles'

    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)


class TaskSubmittedModel(db.Model):
    __tablename__ = 'task_submitted'

    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), primary_key=True)
    submission_id = db.Column(db.Integer, db.ForeignKey('task_submissions.id'), primary_key=True)
