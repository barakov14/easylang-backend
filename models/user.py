from db import db


class UserModel(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    name = db.Column(db.String(80), nullable=False)
    surname = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    role = db.Column(db.String(80), nullable=False)
    rate = db.Column(db.Float, nullable=False, default=100)
    status = db.Column(db.String(80), nullable=False, default='READY')
    password = db.Column(db.String(80), nullable=False)
    tasks_completed = db.Column(db.Integer, default=0)
    tasks_evaluated = db.Column(db.Integer, default=0)
    projects_created = db.Column(db.Integer, default=0)
    projects_completed = db.Column(db.Integer, default=0)
    notifications_count = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f"<User id={self.id}, name={self.name}, email={self.email}, surname={self.surname}, role={self.role}, rate={self.rate}, status={self.status}>"
