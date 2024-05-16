from datetime import datetime

from flask.views import MethodView
from flask_smorest import Blueprint, abort
from sqlalchemy import desc
from sqlalchemy.exc import SQLAlchemyError
from flask_jwt_extended import jwt_required, get_jwt_identity
from celery import Celery
from db import db
from models import ProjectModel, UserModel
from models.notifications import NotificationUserModel
from resources.notifications import send_notification
from schemas import CreateProjectSchema, UserSchema, ReadProjectSchema, UserListQueryArgsSchema, \
    ProjectsListQueryArgsSchema

blp = Blueprint("project", __name__, description="Operations on project")


celery = Celery(__name__)


@blp.route("/projects")
class ProjectList(MethodView):
    @blp.arguments(CreateProjectSchema, location='json')
    @blp.response(201, ReadProjectSchema)
    @jwt_required()
    def post(self, project_data):
        current_user_id = get_jwt_identity()
        current_user = UserModel.query.get(current_user_id)

        if current_user.role != "manager":
            abort(403, message="Only managers can create projects.")

        try:
            project_number = ProjectModel.query.count() + 1
            project_code = generate_project_id(project_data['name'], project_number)

            project = ProjectModel(
                name=project_data['name'],
                code=project_code,
                description=project_data['description'],
                number_of_pages=project_data['number_of_pages'],
                creator_id=current_user_id,
                status="NEW",
                color=project_data['color']
            )
            db.session.add(project)
            db.session.commit()
            project_id = project.id
            project_switch_status(project_id)
            return project, 201
        except SQLAlchemyError as e:
            db.session.rollback()
            print(e)
            abort(500, message="Failed to create project due to a database error.")

    @blp.response(200, ReadProjectSchema(many=True))
    @jwt_required()
    def get(self):
        current_user_id = get_jwt_identity()
        current_user = UserModel.query.get(current_user_id)

        if current_user.role == "manager":
            projects_query = ProjectModel.query.order_by(desc(ProjectModel.started_at))
        elif current_user.role in ["editor", "translator"]:
            projects_query = ProjectModel.query.filter(
                (ProjectModel.editors.any(id=current_user_id)) |
                (ProjectModel.translators.any(id=current_user_id))
            ).order_by(desc(ProjectModel.started_at))
        else:
            projects_query = ProjectModel.query.order_by(desc(ProjectModel.started_at))

        projects = projects_query.all()
        return projects, 200



@celery.task
def project_switch_status(project_id):
    try:
        project = ProjectModel.query.get_or_404(project_id)

        # Задаем таймаут на 5 минут (300 секунд)
        timeout = 300

        if project.status == 'NEW':
            # Выполняем свитч через 5 минут с использованием countdown
            project_switch_status.apply_async(args=[project_id], countdown=timeout)
            project.status = 'IN PROGRESS'

        # Сохраняем изменения в базе данных
        db.session.commit()
    except Exception as e:
        # Handle exceptions here, log them or perform necessary actions
        print("Error occurred during project switch status:", str(e))
        db.session.rollback()








@blp.route("/projects/<int:project_id>")
class Project(MethodView):
    @blp.response(200, ReadProjectSchema)
    @jwt_required()
    def get(self, project_id):
        current_user_id = get_jwt_identity()
        current_user = UserModel.query.get(current_user_id)

        project = ProjectModel.query.filter_by(id=project_id).first_or_404()

        if current_user.role == "manager" or \
           current_user_id == project.creator_id or \
           current_user_id in [editor.id for editor in project.editors] or \
           current_user_id in [translator.id for translator in project.translators]:
            return project, 200
        else:
            abort(403, message="You are not authorized to access this project.")

    @blp.arguments(CreateProjectSchema)
    @blp.response(200, ReadProjectSchema)
    @jwt_required()
    def put(self, project_data, project_id):
        current_user_id = get_jwt_identity()
        current_user = UserModel.query.get(current_user_id)

        project = ProjectModel.query.get_or_404(project_id)

        if current_user.role != "manager":
            abort(403, message="Only managers can edit projects.")

        try:
            # Update project data
            for key, value in project_data.items():
                setattr(project, key, value)
            db.session.commit()
            return project, 200
        except SQLAlchemyError as e:
            db.session.rollback()
            abort(500, message=f"Failed to update project: {str(e)}")

    @blp.response(204)
    @jwt_required()
    def delete(self, project_id):
        current_user_id = get_jwt_identity()
        current_user = UserModel.query.get(current_user_id)

        project = ProjectModel.query.get_or_404(project_id)

        if current_user.role != "manager":
            abort(403, message="Only managers can delete projects.")

        try:
            db.session.delete(project)
            db.session.commit()
            return "", 204
        except SQLAlchemyError as e:
            db.session.rollback()
            abort(500, message=f"Failed to delete project: {str(e)}")


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

        editor = UserModel.query.get_or_404(editor_id)
        if editor.role != "editor":
            abort(400, message=f"User with ID {editor_id} is not an editor.")

        try:
            project.editors.append(editor)
            notification_msg = f"You've been assigned as an editor to project {project.name}"
            send_notification(editor_id, project_id, project.name, "in_process", notification_msg)
            editor.notifications_count += 1  # Increment editor's notifications count
            db.session.commit()
            return editor, 200
        except SQLAlchemyError as e:
            db.session.rollback()
            abort(500, message=f"Failed to add editor to project: {str(e)}")


@blp.route("/projects/user")
class UserProjects(MethodView):
    @blp.response(200, ReadProjectSchema(many=True))
    @jwt_required()
    def get(self):
        current_user_id = get_jwt_identity()
        current_user = UserModel.query.get(current_user_id)

        projects = []

        if current_user.role == "manager":
            projects = ProjectModel.query.filter_by(creator_id=current_user_id).order_by(ProjectModel.id.desc()).limit(10).all()
        elif current_user.role == "translator":
            projects = ProjectModel.query.filter(ProjectModel.translators.any(id=current_user_id)).order_by(ProjectModel.id.desc()).limit(10).all()
        elif current_user.role == "editor":
            projects = ProjectModel.query.filter(ProjectModel.editors.any(id=current_user_id)).order_by(ProjectModel.id.desc()).limit(10).all()

        return projects, 200




def generate_project_id(name, number):
    # Разделяем имя проекта на слова и берем первые три буквы каждого слова
    initials = ''.join(word[:3].upper() for word in name.split())
    # Ограничиваем количество букв до трех
    initials = initials[:3]
    # Создаем идентификатор в формате "буквенные_инициалы-номер"
    project_id = f"{initials}-{number}"
    return project_id
