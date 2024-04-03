from flask.views import MethodView
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_smorest import Blueprint, abort
from sqlalchemy.exc import SQLAlchemyError

from db import db
from models import UserModel, ProjectModel
from models.project import ProjectTasksModel
from models.task import TaskModel, TaskSubmissionModel, TaskSubmittedModel
from resources.notifications import send_notification
from schemas import ReadTaskSchema, CreateTaskSchema, UserSchema, TaskSubmissionSchema, TaskSubmissionCheckingSchema

blp = Blueprint("task", __name__, description="Operations on tasks")


@blp.route("/task/<int:project_id>")
class Task(MethodView):
    @jwt_required()
    @blp.arguments(CreateTaskSchema)
    @blp.response(201, ReadTaskSchema)
    def post(self, task_data, project_id):
        current_user_id = get_jwt_identity()
        current_user = UserModel.query.get(current_user_id)

        if current_user.role != "manager":
            abort(403, message="Only managers can assign tasks to projects.")

        project = ProjectModel.query.get_or_404(project_id)

        # Создаем новую задачу на основе переданных данных
        new_task = TaskModel(**task_data)
        new_task.project_id = project_id

        try:
            # Добавляем задачу к проекту и сохраняем изменения
            db.session.add(new_task)
            db.session.commit()

            # Привязываем задачу к проекту
            project.tasks.append(new_task)
            db.session.commit()

            return new_task, 201
        except SQLAlchemyError as e:
            db.session.rollback()
            abort(500, message="Failed to create task due to a database error.")

    @blp.response(200, ReadTaskSchema(many=True))
    @jwt_required()
    def get(self, project_id):
        # Получаем проект по его ID
        project = ProjectModel.query.get_or_404(project_id)

        # Получаем список задач для указанного проекта
        tasks = project.tasks
        return tasks, 200


@blp.route("/task/<int:project_id>/<int:task_id>/translators/<int:translator_id>")
class TaskTranslator(MethodView):
    @blp.response(200, UserSchema)
    @jwt_required()
    def post(self, project_id, task_id, translator_id):
        current_user_id = get_jwt_identity()
        current_user = UserModel.query.get(current_user_id)

        if current_user.role != "manager":
            abort(403, message="Only managers can assign translators to tasks.")

        # Check if the task belongs to the specified project
        task = TaskModel.query.join(ProjectTasksModel).filter(ProjectTasksModel.project_id == project_id, TaskModel.id == task_id).first_or_404()



        # Find the translator in the database by translator_id
        translator = UserModel.query.get_or_404(translator_id)
        if translator.role != "translator":
            abort(400, message=f"User with ID {translator_id} is not a translator.")

        # Add the translator to the task
        project_name = ProjectModel.query.get_or_404(project_id).name
        notification_msg = f"You've been assigned as a translator to task {task.name} in project {project_name}"
        send_notification(translator_id, project_id, project_name, "in_process", notification_msg)

        task.responsibles.append(translator)
        db.session.commit()

        return translator, 200




@blp.route("/task/<int:project_id>/<int:task_id>/submissions")
class TaskSubmission(MethodView):
    @jwt_required()
    @blp.arguments(TaskSubmissionSchema)
    @blp.response(201, TaskSubmissionSchema)
    def post(self, submission_data, project_id, task_id):
        current_user_id = get_jwt_identity()
        current_user = UserModel.query.get(current_user_id)

        if current_user.role != "translator":
            abort(403, message=f"Only translators can submit submissions.")

        # Проверяем, существует ли задача для указанного проекта
        task = TaskModel.query.join(ProjectTasksModel).filter(ProjectTasksModel.project_id == project_id, TaskModel.id == task_id).first_or_404()

        task_submission = TaskSubmissionModel(**submission_data)
        task_submission.task_id = task_id
        task_submission.status = "checking"


        try:
            project_name = ProjectModel.query.get_or_404(project_id).name
            notification_msg = f"{current_user.name} {current_user.surname} has submitted the task {task.name} in project {project_name} for review"
            editors = UserModel.query.filter_by(role="editor").all()
            for editor in editors:
                send_notification(editor.id, project_id, project_name, "checking", notification_msg)

            task.submissions.append(task_submission)
            db.session.add(task_submission)
            db.session.commit()
            return task_submission, 201
        except SQLAlchemyError:
            db.session.rollback()
            abort(500, message="Failed to create task submission")

    @jwt_required()
    @blp.response(200, TaskSubmissionCheckingSchema(many=True))
    def get(self, project_id, task_id):
        current_user_id = get_jwt_identity()
        current_user = UserModel.query.get(current_user_id)

        if current_user.role not in ["translator", "editor"]:
            abort(403, message=f"Only translators and editors can view submissions.")

        task = TaskModel.query.join(ProjectTasksModel).filter(ProjectTasksModel.project_id == project_id, TaskModel.id == task_id).first_or_404()

        submissions = task.submissions
        return submissions, 200


@blp.route("/task/<int:project_id>/<int:task_id>/submission/<int:submission_id>/grade")
class TaskSubmissionGrade(MethodView):
    @jwt_required()
    @blp.arguments(TaskSubmissionCheckingSchema)
    @blp.response(200, TaskSubmissionSchema)
    def put(self, grade_data, project_id, task_id, submission_id):
        current_user_id = get_jwt_identity()
        current_user = UserModel.query.get(current_user_id)

        if current_user.role != "editor":
            abort(403, message="Only editors can grade submissions.")

        # Query the task based on project_id and task_id
        task = TaskModel.query.join(ProjectTasksModel).filter(ProjectTasksModel.project_id == project_id,
                                                              TaskModel.id == task_id).first_or_404()

        # Query the submission based on submission_id and task_id
        submission = TaskSubmissionModel.query.join(TaskSubmittedModel).filter(TaskSubmittedModel.task_id == task_id,
                                                                               TaskSubmittedModel.submission_id == submission_id).first_or_404()

        # Update the grade of the submission
        submission.grade = grade_data["grade"]
        submission.status = "done"

        try:
            project_name = ProjectModel.query.get_or_404(project_id).name
            notification_msg = f"{current_user.name} {current_user.surname} has graded the task {task.name} in project {project_name}. Grade: {submission.grade}"
            translators = UserModel.query.filter_by(role="translator").all()
            for translator in translators:
                send_notification(translator.id, project_id, "done", notification_msg)
            db.session.commit()
            return submission, 200
        except SQLAlchemyError:
            db.session.rollback()
            abort(500, message="Failed to update submission grade")




