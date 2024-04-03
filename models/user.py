from db import db


class UserModel(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    name = db.Column(db.String(80), nullable=False)
    surname = db.Column(db.String(80), nullable=False)
    role = db.Column(db.String(80), nullable=False)
    rate = db.Column(db.Float, nullable=False, default=100)
    status = db.Column(db.String(80), nullable=False, default='ready')
    password = db.Column(db.String(80), nullable=False)

    def __repr__(self):
        return f"<User id={self.id}, name={self.name}, surname={self.surname}, role={self.role}, rate={self.rate}, status={self.status}>"


class InvitationCodeModel(db.Model):
    __tablename__ = 'invitation_codes'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(255), unique=True, nullable=False)
    role = db.Column(db.String(80), nullable=False)