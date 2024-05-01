from flask import jsonify, current_app
from flask.views import MethodView
from flask_mail import Message, Mail
from flask_smorest import Blueprint, abort
from flask_jwt_extended import create_access_token, jwt_required, get_jwt, get_jwt_identity
from passlib.hash import pbkdf2_sha256
from sqlalchemy.exc import SQLAlchemyError
from models import UserModel
from schemas import UserSchema, LoginUserSchema, RegisterUserSchema, UserListQueryArgsSchema
from blocklist import BLOCKLIST
from db import db

blp = Blueprint("users", "users", description="Users operations")


@blp.route("/register", methods=["POST"])
class Register(MethodView):
    @blp.arguments(RegisterUserSchema)
    def post(self, user_data):
        username = user_data["username"]
        name = user_data["name"]
        surname = user_data["surname"]
        email = user_data["email"]
        password = user_data["password"]
        role = user_data["role"]

        if role not in ["editor", "manager", "translator", "admin"]:
            abort(400, message="Invalid role")

        existing_user = UserModel.query.filter(UserModel.username == username).first()
        if existing_user:
            abort(409, message=f"A user with username '{username}' already exists")

        existing_email = UserModel.query.filter(UserModel.email == email).first()
        if existing_email:
            abort(409, message=f"A user with email '{email}' already exists")

        hashed_password = pbkdf2_sha256.hash(password)

        user = UserModel(
            username=username, name=name, surname=surname, email=email, password=hashed_password, role=role
        )

        try:
            db.session.add(user)
            db.session.commit()

            user_schema = UserSchema()
            # send_registration_email(email, username, password)
            serialized_user = user_schema.dump(user)

            return serialized_user, 201
        except SQLAlchemyError as e:
            db.session.rollback()
            abort(500, message=str(e))


@blp.route("/login", methods=["POST"])
class Login(MethodView):
    @blp.arguments(LoginUserSchema)
    def post(self, user_data):
        username = user_data["username"]
        password = user_data["password"]

        user = UserModel.query.filter(UserModel.username == username).first()
        if not user or not pbkdf2_sha256.verify(password, user.password):
            abort(400, message="Username or password is not correct. Please try again.")

        token = create_access_token(identity=user.id)
        return jsonify({"token": token})


@blp.route("/logout", methods=["POST"])
class Logout(MethodView):
    @jwt_required()
    def post(self):
        jti = get_jwt()["jti"]
        BLOCKLIST.add(jti)
        return jsonify({"message": "Successfully logged out"}), 200


@blp.route("/user", methods=["GET"])
class UserInfo(MethodView):
    @jwt_required()
    @blp.response(200, UserSchema)
    def get(self):
        current_user_id = get_jwt_identity()
        user = UserModel.query.get(current_user_id)
        if not user:
            abort(404, message="User not found")
        user_schema = UserSchema()
        return user_schema.dump(user)


@blp.route("/users", methods=["GET"])
class UserList(MethodView):
    @blp.arguments(UserListQueryArgsSchema, location='query')
    @blp.response(200, UserSchema(many=True))
    def get(self, args):
        users_query = UserModel.query
        if args.get('name'):
            users_query = users_query.filter(UserModel.name.ilike(f"%{args['name']}%"))
        if args.get('id'):
            users_query = users_query.filter(UserModel.id == args['id'])
        if args.get('role'):
            users_query = users_query.filter(UserModel.role == args['role'])

        users_query = users_query.order_by(UserModel.rate.desc())
        users = users_query.all()

        user_schema = UserSchema(many=True)
        return user_schema.dump(users)


@blp.route("/users/editors", methods=["GET"])
class EditorsList(MethodView):
    @blp.response(200, UserSchema(many=True))
    def get(self):
        editors = UserModel.query.filter_by(role='editor').order_by(UserModel.rate.desc()).all()
        user_schema = UserSchema(many=True)
        return user_schema.dump(editors)


@blp.route("/users/managers", methods=["GET"])
class ManagersList(MethodView):
    @blp.response(200, UserSchema(many=True))
    def get(self):
        managers = UserModel.query.filter_by(role='manager').order_by(UserModel.rate.desc()).all()
        user_schema = UserSchema(many=True)
        return user_schema.dump(managers)


@blp.route("/users/translators", methods=["GET"])
class TranslatorsList(MethodView):
    @blp.response(200, UserSchema(many=True))
    def get(self):
        translators = UserModel.query.filter_by(role='translator').order_by(UserModel.rate.desc()).all()
        user_schema = UserSchema(many=True)
        return user_schema.dump(translators)


@blp.route("/user/<int:user_id>", methods=["GET", "PUT", "DELETE"])
class User(MethodView):
    @jwt_required()
    @blp.response(200, UserSchema)
    def get(self, user_id):
        current_user_id = get_jwt_identity()
        current_user = UserModel.query.get(current_user_id)
        if not current_user or current_user.role != "admin":
            abort(403, message="Only admins can access user details.")

        user = UserModel.query.get_or_404(user_id)
        user_schema = UserSchema()
        return user_schema.dump(user)

    @jwt_required()
    @blp.arguments(UserSchema)
    @blp.response(200, UserSchema)
    def put(self, user_data, user_id):
        current_user_id = get_jwt_identity()
        current_user = UserModel.query.get(current_user_id)
        if not current_user or current_user.role != "admin":
            abort(403, message="Only admins can update users.")

        user = UserModel.query.get_or_404(user_id)
        user.username = user_data["username"]
        user.name = user_data["name"]
        user.surname = user_data["surname"]
        user.role = user_data["role"]

        user_schema = UserSchema()

        try:
            db.session.commit()
        except SQLAlchemyError as e:
            db.session.rollback()
            abort(500, message="Failed to update user.")

        return user_schema.dump(user)

    @jwt_required()
    @blp.response(204)
    def delete(self, user_id):
        current_user_id = get_jwt_identity()
        current_user = UserModel.query.get(current_user_id)
        if not current_user or current_user.role != "admin":
            abort(403, message="Only admins can delete users.")

        user = UserModel.query.get_or_404(user_id)

        try:
            db.session.delete(user)
            db.session.commit()
        except SQLAlchemyError as e:
            db.session.rollback()
            abort(500, message="Failed to delete user.")

        return "", 204


@blp.route("/users/translators/available", methods=["GET"])
class AvailableTranslators(MethodView):
    @blp.response(200, UserSchema(many=True))
    def get(self):
        translators = UserModel.query.filter_by(role='translator', status='READY').all()
        user_schema = UserSchema(many=True)
        return user_schema.dump(translators)


@blp.route("/users/editors/available", methods=["GET"])
class AvailableEditors(MethodView):
    @blp.response(200, UserSchema(many=True))
    def get(self):
        editors = UserModel.query.filter_by(role='editor', status='READY').all()
        user_schema = UserSchema(many=True)
        return user_schema.dump(editors)


from flask import jsonify
from flask.views import MethodView


@blp.route("/users/translators/rating", methods=["GET"])
class TranslatorsRating(MethodView):
    @blp.response(200, UserSchema(many=True))
    def get(self):
        translators = UserModel.query.filter_by(role='translator').all()
        ratings = []
        for translator in translators:
            rating = {
                "id": translator.id,
                "name": translator.name,
                "surname": translator.surname,
                "rate": translator.rate,
                "tasks_completed": translator.tasks_completed
            }
            ratings.append(rating)

        # Sort the translators list based on their rating (assuming you have a 'rating' attribute)
        ratings = sorted(ratings, key=lambda x: x.get("rate", 0), reverse=True)

        for i, rating in enumerate(ratings, start=1):
            rating["place"] = i
        return jsonify(ratings)


@blp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    current_user = get_jwt_identity()
    access_token = create_access_token(identity=current_user)
    return jsonify({'access_token': access_token}), 200

@blp.route("/users/<int:user_id>/ready", methods=["POST"])
class SetUserReady(MethodView):
    @jwt_required()
    def post(self, user_id):
        current_user_id = get_jwt_identity()
        current_user = UserModel.query.get(current_user_id)

        # Проверяем, является ли текущий пользователь администратором
        if current_user.role != "admin":
            abort(403, message="Only admin can change user status.")

        # Получаем пользователя по его ID
        user = UserModel.query.get_or_404(user_id)

        # Устанавливаем статус пользователя в READY
        user.status = "READY"

        try:
            db.session.commit()
            return {"message": f"User {user.username} status set to READY"}, 200
        except SQLAlchemyError as e:
            db.session.rollback()
            abort(500, message=str(e))


@blp.route("/users/<int:user_id>/not_ready", methods=["POST"])
class SetUserNotReady(MethodView):
    @jwt_required()
    def post(self, user_id):
        current_user_id = get_jwt_identity()
        current_user = UserModel.query.get(current_user_id)

        # Проверяем, является ли текущий пользователь администратором
        if current_user.role != "admin":
            abort(403, message="Only admin can change user status.")

        # Получаем пользователя по его ID
        user = UserModel.query.get_or_404(user_id)

        # Устанавливаем статус пользователя в NOT READY
        user.status = "NOT READY"

        try:
            db.session.commit()
            return {"message": f"User {user.username} status set to NOT READY"}, 200
        except SQLAlchemyError as e:
            db.session.rollback()
            abort(500, message=str(e))



def send_registration_email(email, username, password):
    mail = Mail(current_app)
    msg = Message('Registration Confirmation', recipients=[email])
    msg.body = f"Hello {username},\n\nThank you for registering! Your password is: {password}"
    mail.send(msg)
