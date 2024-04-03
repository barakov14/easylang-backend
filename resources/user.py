from flask import jsonify
from flask.views import MethodView
from flask_smorest import Blueprint, abort
from flask_jwt_extended import create_access_token, jwt_required, get_jwt, get_jwt_identity
from passlib.hash import pbkdf2_sha256
from sqlalchemy.exc import SQLAlchemyError
from models import UserModel
from models.user import InvitationCodeModel
from schemas import UserSchema, LoginUserSchema, InvitationCodeSchema, RegisterUserSchema
from blocklist import BLOCKLIST

from db import db

blp = Blueprint("users", __name__, description="Users operations")

@blp.route("/register")
class Register(MethodView):
    @blp.arguments(RegisterUserSchema)
    def post(self, user_data):
        name = user_data["name"]
        surname = user_data["surname"]
        username = user_data["username"]
        password = user_data["password"]
        invitation_code_value = user_data["invitation_code"]


        # Проверяем, существует ли пользователь с таким именем
        existing_user = UserModel.query.filter(UserModel.username == username).first()
        if existing_user:
            abort(409, f"A user with username '{username}' already exists")

        invitation_code_obj = InvitationCodeModel.query.filter_by(code=invitation_code_value).first()
        if not invitation_code_obj:
            abort(404, f"No invitation code found with value '{invitation_code_value}'")

        role = invitation_code_obj.role

        # Хешируем пароль
        hashed_password = pbkdf2_sha256.hash(password)

        # Создаем нового пользователя
        user = UserModel(
            username=username, password=hashed_password, name=name, surname=surname, role=role
        )

        try:
            # Добавляем пользователя в базу данных и сохраняем изменения
            db.session.add(user)
            db.session.commit()
        except SQLAlchemyError as e:
            db.session.rollback()
            # В случае ошибки вернем 500 с сообщением об ошибке
            abort(500, str(e))

        # Создаем токены доступа и обновления
        token = create_access_token(identity=user.id)

        # Возвращаем успешный ответ с токенами
        return jsonify({
            "token": token
        })

@blp.route("/login")
class Login(MethodView):
    @blp.arguments(LoginUserSchema)
    def post(self, user_data):
        username = user_data["username"]
        password = user_data["password"]

        # Находим пользователя по имени
        user = UserModel.query.filter(UserModel.username == username).first()
        if not user or not pbkdf2_sha256.verify(password, user.password):
            abort(401, "Invalid username or password")

        # Создаем токены доступа и обновления
        token = create_access_token(identity=user.id)

        # Возвращаем успешный ответ с токенами
        return jsonify({
            "token": token,
        })

@blp.route("/logout")
class Logout(MethodView):
    @jwt_required()
    @blp.response(200, description="Successfully logged out")
    def post(self):
        # Получаем токен из запроса
        jti = get_jwt()["jti"]
        BLOCKLIST.add(jti)
        return jsonify({"message": "Successfully logged out"})

@blp.route("/user")
class UserInfo(MethodView):
    @jwt_required()
    @blp.response(200, UserSchema)
    def get(self):
        # Получаем идентификатор пользователя из токена доступа
        current_user_id = get_jwt_identity()

        # Находим пользователя по идентификатору
        user = UserModel.query.get(current_user_id)
        if not user:
            abort(404, "User not found")

        # Возвращаем информацию о пользователе
        return jsonify(UserSchema().dump(user))


@blp.route("/users")
class UserList(MethodView):
    @blp.response(200, UserSchema(many=True))
    def get(self):
        # Query all users and sort them by 'rate' attribute in descending order
        users = UserModel.query.order_by(UserModel.rate.desc()).all()

        # Serialize the user data into JSON format
        user_schema = UserSchema(many=True)
        serialized_users = user_schema.dump(users)

        # Return the sorted list of users
        return jsonify(serialized_users)

@blp.route("/users/editors")
class EditorsList(MethodView):
    @blp.response(200, UserSchema(many=True))
    def get(self):
        # Query editors and sort them by 'rate' attribute in descending order
        editors = UserModel.query.filter_by(role='editor').order_by(UserModel.rate.desc()).all()

        # Serialize the editor data into JSON format
        user_schema = UserSchema(many=True)
        serialized_editors = user_schema.dump(editors)

        # Return the sorted list of editors
        return jsonify(serialized_editors)

@blp.route("/users/managers")
class ManagersList(MethodView):
    @blp.response(200, UserSchema(many=True))
    def get(self):
        # Query managers and sort them by 'rate' attribute in descending order
        managers = UserModel.query.filter_by(role='manager').order_by(UserModel.rate.desc()).all()

        # Serialize the manager data into JSON format
        user_schema = UserSchema(many=True)
        serialized_managers = user_schema.dump(managers)

        # Return the sorted list of managers
        return jsonify(serialized_managers)

@blp.route("/users/translators")
class TranslatorsList(MethodView):
    @blp.response(200, UserSchema(many=True))
    def get(self):
        # Query translators and sort them by 'rate' attribute in descending order
        translators = UserModel.query.filter_by(role='translator').order_by(UserModel.rate.desc()).all()

        # Serialize the translator data into JSON format
        user_schema = UserSchema(many=True)
        serialized_translators = user_schema.dump(translators)

        # Return the sorted list of translators
        return jsonify(serialized_translators)

@blp.route("/generate-invitation-code")
class GenerateInvitationCode(MethodView):
    @blp.arguments(InvitationCodeSchema)
    @blp.response(201, InvitationCodeSchema)
    # @jwt_required()
    def post(self, code_data):
        # current_user_id = get_jwt_identity()
        # current_user = UserModel.query.get(current_user_id)
        #
        # if current_user.role != "manager":
        #     abort(403, message="Only managers can generate invitation codes.")

        # Генерация случайного кода
        random_code = generate_random_code()

        # Создание записи с invitation_code в базе данных
        invitation_code = InvitationCodeModel(code=random_code, role=code_data["role"])

        try:
            # Добавление кода в базу данных и сохранение изменений
            db.session.add(invitation_code)
            db.session.commit()
        except SQLAlchemyError as e:
            db.session.rollback()
            # В случае ошибки вернем 500 с сообщением об ошибке
            abort(500, message=str(e))

        # Возвращаем успешный ответ с созданным кодом
        return jsonify({
            "code": random_code,
            "role": code_data["role"]
        })



@blp.route("/user/role")
class UserRole(MethodView):
    @jwt_required()
    def get(self):
        # Получаем идентификатор текущего пользователя из токена доступа
        current_user_id = get_jwt_identity()

        # Находим пользователя по его идентификатору
        user = UserModel.query.get(current_user_id)
        if not user:
            abort(404, "User not found")

        # Получаем роль пользователя
        user_role = user.role

        # Возвращаем роль текущего пользователя
        return jsonify({"role": user_role})

def generate_random_code():
    # Ваш код для генерации случайного кода
    # В этом примере я использую библиотеку secrets для генерации случайной строки
    import secrets
    random_code = secrets.token_urlsafe(16)  # Генерация случайной строки длиной 16 символов
    return random_code
