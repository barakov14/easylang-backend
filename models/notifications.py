from sqlalchemy.orm import relationship

from db import db


class NotificationModel(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    project_name = db.Column(db.String, nullable=False)
    link = db.Column(db.String, nullable=True)
    status = db.Column(db.String(20), nullable=False)
    msg = db.Column(db.String(255), nullable=False)

    users = relationship("NotificationUserModel", cascade="all, delete-orphan")


class NotificationUserModel(db.Model):
    __tablename__ = 'notification_user'

    notification_id = db.Column(db.Integer, db.ForeignKey('notifications.id'), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
