from flask.views import MethodView
from flask_smorest import Blueprint, abort
from sqlalchemy.exc import SQLAlchemyError
from flask_jwt_extended import jwt_required, get_jwt_identity

from db import db
from models import ProjectModel, UserModel
from resources.notifications import send_notification
from schemas import CreateProjectSchema, UserSchema, ReadProjectSchema

blp = Blueprint("project", __name__, description="Operations on project")


@blp.route("/projects")
class ProjectList(MethodView):
    @blp.arguments(CreateProjectSchema)
    @blp.response(201, ReadProjectSchema)
    @jwt_required()
    def post(self, project_data):
        current_user_id = get_jwt_identity()
        current_user = UserModel.query.get(current_user_id)

        if current_user.role != "manager":
            abort(403, message="Only managers can create projects.")

        try:
            project = ProjectModel(**project_data)
            db.session.add(project)
            db.session.commit()
            return "Project created successfully", 201
        except SQLAlchemyError as e:
            db.session.rollback()
            abort(500, message="Failed to create project due to a database error.")

    @blp.response(200, ReadProjectSchema(many=True))
    @jwt_required()
    def get(self):
        projects = ProjectModel.query.all()
        return projects, 200


@blp.route("/projects/<int:project_id>")
class Project(MethodView):
    @blp.response(200, ReadProjectSchema)
    @jwt_required()
    def get(self, project_id):
        project = ProjectModel.query.get_or_404(project_id)
        return project, 200


@blp.route("/projects/<int:project_id>/editors/<int:editor_id>")
class ProjectEditor(MethodView):
    @blp.response(200, UserSchema)
    @jwt_required()
    def post(self, project_id, editor_id):
        current_user_id = get_jwt_identity()
        current_user = UserModel.query.get(current_user_id)

        if current_user.role != "manager":
            abort(403, message="Only managers can assign editors to projects.")

        project = ProjectModel.query.get_or_404(project_id)

        # Находим редактора в базе данных по editor_id
        editor = UserModel.query.get_or_404(editor_id)
        if editor.role != "editor":
            abort(400, message=f"User with ID {editor_id} is not an editor.")

        # Добавляем редактора к проекту
        try:
            project.editors.append(editor)
            notification_msg = f"You've been assigned as an editor to project {project.name}"
            send_notification(editor_id, project_id, project.name, "in_process", notification_msg)
            db.session.commit()
            return editor, 200
        except SQLAlchemyError as e:
            db.session.rollback()
            abort(500, message=f"Failed to add editor to project due to a database error: {str(e)}")
