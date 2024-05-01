from datetime import datetime, timedelta
from celery import Celery
from flask.views import MethodView
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_smorest import Blueprint, abort
from sqlalchemy.exc import SQLAlchemyError
from db import db
from models import UserModel, ProjectModel
from models.notifications import NotificationUserModel
from models.project import ProjectTasksModel
from models.task import TaskModel, TaskSubmissionModel, TaskSubmittedModel
from resources.notifications import send_notification
from schemas import ReadTaskSchema, CreateTaskSchema, UserSchema, TaskSubmissionSchema, TaskSubmissionCheckingSchema, \
    TaskSubmissionFilterSchema, DeadlineSchema, SetTaskDeadlineSchema, TaskSubmissionSchemaSendForCorrection

blp = Blueprint("task", __name__, description="Operations on tasks")

# Создаем экземпляр Celery
celery = Celery(__name__)

# Настройки Celery
celery.conf.update(
    broker_url='redis://localhost:6379/0',
    result_backend='redis://localhost:6379/0'
)


def next_friday():
    today = datetime.now()
    days_until_friday = (4 - today.weekday() + 7) % 7
    next_friday_date = today + timedelta(days=days_until_friday)
    next_friday_datetime = datetime.combine(next_friday_date, datetime.min.time())
    return next_friday_datetime


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

        if task_data.get('pages') is not None and project.number_of_pages is not None:
            if task_data['pages'] > project.number_of_pages / 6:
                abort(400, message="Task pages cannot be more than 1/6 of project number of pages.")

        # Получаем текущее количество задач в проекте и добавляем 1 для генерации нового кода задачи
        task_count = len(project.tasks) + 1

        # Генерируем код задачи в формате "PRJ_ID-Task_Number", например, "1-1", "1-2" и т.д.
        new_task_code = f"{task_count}"

        # Создаем новую задачу на основе переданных данных
        new_task = TaskModel(
            code=new_task_code,
            **task_data
        )

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


@blp.route("/task/<int:task_id>/set_deadline")
class SetTaskDeadline(MethodView):
    @jwt_required()
    @blp.arguments(SetTaskDeadlineSchema)
    @blp.response(200, ReadTaskSchema)
    def post(self, deadline_data, task_id):
        current_user_id = get_jwt_identity()
        current_user = UserModel.query.get(current_user_id)

        # Проверяем, является ли текущий пользователь переводчиком
        if current_user.role == "translator":
            # Получаем задачу по ее ID
            task = TaskModel.query.get_or_404(task_id)

            # Проверяем, принадлежит ли задача текущему пользователю (переводчику)
            if task.translator_id == current_user_id:
                # Устанавливаем дедлайн для задачи и сохраняем изменения
                task.deadline = deadline_data['deadline']
                db.session.commit()
                return task, 200
            else:
                abort(403, message="You can only set deadline for your own tasks.")
        else:
            abort(403, message="Only translators can set deadlines.")


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
        task = TaskModel.query.join(ProjectTasksModel).filter(ProjectTasksModel.project_id == project_id,
                                                              TaskModel.id == task_id).first_or_404()

        # Find the translator in the database by translator_id
        translator = UserModel.query.get_or_404(translator_id)
        if translator.role != "translator":
            abort(400, message=f"User with ID {translator_id} is not a translator.")

        # Add the translator to the task
        project_name = ProjectModel.query.get_or_404(project_id).name
        send_task_assigned_notification(translator_id, project_id, task.name, project_name)
        send_deadline_notification(translator_id, project_id, task.name, project_name)

        user = UserModel.query.filter_by(id=current_user_id).first()
        user.notifications_count += 1
        project = ProjectModel.query.get_or_404(project_id)

        project.translators.append(translator)
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

        task = TaskModel.query.get_or_404(task_id)
        if current_user not in task.responsibles:
            abort(403, message="You are not assigned to this task.")

        num_pages_done = submission_data.get("pages_done")
        pages = task.pages

        if num_pages_done is None or pages is None:
            abort(400, message="Number of pages done and total pages must be provided.")

        if num_pages_done > pages:
            abort(400, message="Number of pages done cannot be greater than total pages.")


        task_submission = TaskSubmissionModel(**submission_data)
        task_submission.task_id = task_id
        task_submission.pages_done= num_pages_done
        task_submission.translator_id = current_user_id
        task_submission.status = "IN VERIFYING"  # Change submission status

        try:
            user = UserModel.query.filter_by(id=current_user_id).first()
            user.notifications_count += 1
            project_name = ProjectModel.query.get_or_404(project_id).name
            notification_msg = f"{current_user.name} {current_user.surname} has submitted the task {task.name} in project {project_name} for review"
            editors = UserModel.query.filter_by(role="editor").all()
            for editor in editors:
                send_notification(editor.id, project_id, project_name, "IN VERIFYING", notification_msg)

            task.submissions.append(task_submission)
            db.session.add(task_submission)
            db.session.commit()

            return task_submission, 201
        except SQLAlchemyError as e:
            print(e)
            db.session.rollback()
            abort(500, message="Failed to create task submission")
    @jwt_required()
    @blp.arguments(TaskSubmissionFilterSchema, location='query')
    @blp.response(200, TaskSubmissionCheckingSchema(many=True))
    def get(self, query_args, project_id, task_id):
        current_user_id = get_jwt_identity()
        current_user = UserModel.query.get(current_user_id)

        if current_user.role not in ["translator", "editor", "manager"]:
            abort(403, message=f"Only translators, managers and editors can view submissions.")

        submissions = TaskModel.query.get_or_404(task_id).submissions

        return submissions, 200


@blp.route("/task/submissions/<int:submission_id>")
class SingleTaskSubmission(MethodView):
    @jwt_required()
    @blp.response(200, TaskSubmissionSchema)
    def get(self, submission_id):
        current_user_id = get_jwt_identity()
        current_user = UserModel.query.get(current_user_id)

        if current_user.role not in ["translator", "manager", "editor"]:
            abort(403, message=f"Only managers and editors can view submission")

        submission = TaskSubmissionModel.query.get_or_404(submission_id)

        return submission, 200

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

        task = TaskModel.query.join(ProjectTasksModel).filter(ProjectTasksModel.project_id == project_id,
                                                              TaskModel.id == task_id).first_or_404()

        submission = TaskSubmissionModel.query.filter_by(id=submission_id).first_or_404()

        project = ProjectModel.query.get_or_404(project_id)

        if task.pages != 0:
            task_progress_increase = (submission.num_pages_done / task.pages) * 100
            task.progress = min(task.progress + task_progress_increase, 100)

        if project.number_of_pages != 0:
            project_progress_increase = (submission.num_pages_done / project.number_of_pages) * 100
            project.progress = min(project.progress + project_progress_increase, 100)

        # Update the grade and status of the submission
        submission.grade = grade_data["grade"]
        submission.status = "APPROVED"

        try:
            project_name = ProjectModel.query.get_or_404(project_id).name
            translators = UserModel.query.filter_by(role="translator", id=submission.translator_id).all()
            notification_msg = f"{current_user.name} {current_user.surname} has graded the task {task.name} in project {project_name}. Grade: {submission.grade}"
            for translator in translators:
                send_notification(translator.id, project_id, project_name, submission.status, notification_msg)

            db.session.commit()
            return submission, 200
        except SQLAlchemyError as e:
            print(e)
            db.session.rollback()
            abort(500, message="Failed to update submission grade")


@blp.route("/task/<int:project_id>/<int:task_id>/submission/<int:submission_id>/reject")
class TaskSubmissionReject(MethodView):
    @jwt_required()
    @blp.arguments(TaskSubmissionSchemaSendForCorrection)
    @blp.response(200, TaskSubmissionSchema)
    def put(self, correction_data, project_id, task_id, submission_id):
        current_user_id = get_jwt_identity()
        current_user = UserModel.query.get(current_user_id)

        if current_user.role != "editor":
            abort(403, message="Only editors can reject submissions.")

        task = TaskModel.query.get_or_404(task_id)
        project = ProjectModel.query.get_or_404(project_id)


        if current_user not in project.editors:
            abort(403, message="You are not assigned to this task.")

        submission = next((sub for sub in task.submissions if sub.id == submission_id), None)

        submission.status = "NOT APPROVED"
        submission.comment = correction_data["comment"]
        submission.rejected += 1

        try:
            project = ProjectModel.query.get_or_404(project_id)
            notification_msg = f"{current_user.name} {current_user.surname} hasn't approved the task {task.name} in project {project.name}. Comment: {correction_data["comment"]}"
            for translator in project.translators:
                send_notification(translator.id, project_id, project.name, submission.status, notification_msg)
            db.session.commit()
            return submission, 200
        except SQLAlchemyError as e:
            db.session.rollback()
            print(e)
            abort(500, message="Failed to reject submission")


@blp.route("/task/<int:project_id>/<int:task_id>")
class SingleTask(MethodView):
    @blp.response(200, ReadTaskSchema)
    @jwt_required()
    def get(self, project_id, task_id):
        # Получаем задачу по её ID и ID проекта
        task = TaskModel.query.get_or_404(task_id)
        return task, 200

    @blp.arguments(CreateTaskSchema, location='json')
    @blp.response(200, ReadTaskSchema)
    @jwt_required()
    def put(self, task_data, project_id, task_id):
        current_user_id = get_jwt_identity()
        current_user = UserModel.query.get(current_user_id)

        if current_user.role != "manager":
            abort(403, message="Only managers can edit tasks.")

        # Получаем задачу по её ID и ID проекта
        task = TaskModel.query.join(ProjectTasksModel).filter(ProjectTasksModel.project_id == project_id,
                                                              TaskModel.id == task_id).first_or_404()

        try:
            task.update(task_data)
            db.session.commit()
            return task, 200
        except SQLAlchemyError as e:
            db.session.rollback()
            abort(500, message="Failed to update task due to a database error.")

    @blp.response(204)
    @jwt_required()
    def delete(self, project_id, task_id):
        current_user_id = get_jwt_identity()
        current_user = UserModel.query.get(current_user_id)

        if current_user.role != "manager":
            abort(403, message="Only managers can delete tasks.")

        # Получаем задачу по её ID и ID проекта
        task = TaskModel.query.join(ProjectTasksModel).filter(ProjectTasksModel.project_id == project_id,
                                                              TaskModel.id == task_id).first_or_404()

        try:
            db.session.delete(task)
            db.session.commit()
            return "", 204
        except SQLAlchemyError as e:
            db.session.rollback()
            abort(500, message="Failed to delete task due to a database error.")


@blp.route("/mytasks")
class MyTasks(MethodView):
    @blp.response(200, ReadTaskSchema(many=True))
    @jwt_required()
    def get(self):
        current_user_id = get_jwt_identity()
        current_user = UserModel.query.get(current_user_id)

        if current_user.role != "translator":
            abort(403, message="Only translators can access their tasks.")

        # Query tasks assigned to the current translator
        tasks = TaskModel.query.join(TaskModel.responsibles).filter(UserModel.id == current_user_id).all()
        return tasks, 200


@blp.route("/task/<int:project_id>/<int:task_id>/translator/deadline", methods=["PUT"])
class TaskTranslatorDeadline(MethodView):
    @jwt_required()
    @blp.arguments(DeadlineSchema)
    @blp.response(200, TaskSubmissionSchema)
    def put(self, deadline_data, project_id, task_id):
        current_user_id = get_jwt_identity()
        current_user = UserModel.query.get(current_user_id)

        if current_user.role != "translator":
            abort(403, message="Only translators can set deadlines for tasks.")

        task = TaskModel.query.get_or_404(task_id)
        if current_user not in task.responsibles:
            abort(403, message="You are not assigned to this task.")

        # Check if the task belongs to the specified project
        project_name = ProjectModel.query.get_or_404(project_id).name

        # Update the translator's deadline for the task
        task.deadline = deadline_data["deadline"]
        db.session.commit()

        return {"message": f"Deadline updated successfully for task {task.name} in project {project_name}."}, 200


@blp.route("/task/<int:project_id>/<int:task_id>/submission/<int:submission_id>/send-for-correction", methods=["POST"])
class SendForCorrection(MethodView):
    @jwt_required()
    def post(self, project_id, submission_id):
        current_user_id = get_jwt_identity()
        current_user = UserModel.query.get(current_user_id)

        project = ProjectModel.query.get_or_404(project_id)

        # Проверяем, является ли текущий пользователь ролью "editor"
        if current_user.role != "editor":
            abort(403, message="Only editors can send submissions for correction.")

        if current_user.id not in project.editors:
            abort(403, message="You are not assigned in this project")

        # Получаем сабмит для данной задачи и проекта
        submission = TaskSubmissionModel.query.filter_by(id=submission_id).first_or_404()

        # Проверяем, есть ли ошибки в сабмите
        if submission.errors:
            user = UserModel.query.filter_by(id=current_user_id).first()
            user.notifications_count += 1
            # Отправляем уведомление транслейтору о необходимости исправления
            translator_id = submission.translator_id
            project_name = ProjectModel.query.get_or_404(project_id).name
            notification_msg = f"Your submission for task {submission.task.name} in project {project_name} contains mistakes. Please review and make corrections."
            send_notification(translator_id, project_id, project_name, "REQUIRES_CORRECTION", notification_msg)

            return {"message": "Submission sent for correction successfully"}, 200
        else:
            abort(400, message="Submission does not contain errors, cannot be sent for correction.")


@celery.task
def send_submission_reminder(translator_id):
    # Получаем текущую дату и время
    current_datetime = datetime.now()

    # Проверяем, является ли текущий день пятницей
    if current_datetime.weekday() == 4:
        # Отправляем уведомление о сдаче задания транслятору
        # Здесь вы можете вызвать функцию отправки уведомления или выполнить любые другие действия
        pass


@celery.task
def submit_task(translator_id, task_id, percent_completed):
    # Получаем текущее время
    current_time = datetime.now().time()

    # Проверяем, что текущее время до 18:00
    if current_time < datetime.strptime("18:00", "%H:%M").time():
        # Выполняем сабмит задания
        # Здесь вы можете добавить логику сабмита задания
        pass


def send_task_assigned_notification(user_id, project_id, task_name, project_name):
    notification_msg = f"You've been assigned as a translator to task {task_name} in project {project_name}"
    send_notification(user_id, project_id, project_name, "task_assigned", notification_msg)


def send_deadline_notification(user_id, project_id, task_name, project_name):
    notification_msg = f"Please choose a deadline for task {task_name} in project {project_name}"
    send_notification(user_id, project_id, project_name, "choose_deadline", notification_msg)
