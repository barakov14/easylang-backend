from datetime import datetime

import pytest
from flask import Flask
from flask_jwt_extended import create_access_token
from db import db
from models import UserModel, TaskModel
from app import create_app
from unittest.mock import patch, MagicMock
from resources.task import send_submission_reminder, submit_task


@pytest.fixture
def app():
    app = create_app(db_url="sqlite:///:memory:")
    with app.app_context():
        db.create_all()
        editor = UserModel(username='editor123', name='name', surname='surname', password='123456',
                           email='edirjefjkds@example.com', role='editor')
        manager = UserModel(username='manager123', name='name', surname='surname', password='123456',
                            email='manager@example.com', role='manager')
        translator = UserModel(username='translator123', name='name', surname='surname', password='123456',
                               email='trans@example.com', role='translator')
        db.session.add(manager)
        db.session.add(translator)
        db.session.add(editor)
        db.session.commit()
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def access_token_manager(app):
    with app.app_context():
        manager = UserModel.query.filter_by(username='manager123').first()
        access_token = create_access_token(identity=manager.id)
        return access_token


@pytest.fixture
def access_token_editor(app):
    with app.app_context():
        editor = UserModel.query.filter_by(username='editor123').first()
        access_token = create_access_token(identity=editor.id)
        return access_token


@pytest.fixture
def access_token_translator(app):
    with app.app_context():
        translator = UserModel.query.filter_by(username='translator123').first()
        if translator:
            access_token = create_access_token(identity=translator.id)
            return access_token
        else:
            raise ValueError("Translator user not found")


def test_get_task(client, access_token_manager):
    headers = {'Authorization': f'Bearer {access_token_manager}'}
    data = {
        'name': 'Test Project',
        'description': 'Test project description',
        'number_of_pages': 13
    }
    response = client.post('/projects', json=data, headers=headers)
    projid = response.json['id']

    taskdata = {
        'name': 'Test',
        'description': 'Test task',
        'pages': 2,
    }
    tresponse = client.post(f'/task/{projid}', json=taskdata, headers=headers)
    t2response = client.get(f'/task/{projid}', headers=headers)

    assert t2response.status_code == 200


def test_set_deadline_task(client, access_token_manager, access_token_translator, app):
    headers = {'Authorization': f'Bearer {access_token_manager}'}
    headers2 = {'Authorization': f'Bearer {access_token_translator}'}
    data = {
        'name': 'Test Project',
        'description': 'Test project description',
        'number_of_pages': 13
    }
    response = client.post('/projects', json=data, headers=headers)
    projid = response.json['id']

    taskdata = {
        'name': 'Test',
        'description': 'Test task',
        'pages': 2,
    }

    tresponse = client.post(f'/task/{projid}', json=taskdata, headers=headers)
    tid = tresponse.json["id"]

    translator_id = 1

    with app.app_context():  # Устанавливаем контекст приложения Flask
        translator = UserModel.query.filter_by(username='translator123').first()
        if translator:
            translator_id = translator.id
        else:
            raise ValueError("Translator user not found")

    client.post(f'/task/{projid}/{tid}/translators/{translator_id}', headers=headers)
    dresponse = client.post(f'/task/{tid}/set_deadline', json={"deadline": "01-01-2004"}, headers=headers2)

    assert dresponse.status_code == 201

    # Проверяем, что срок выполнения был установлен для задачи
    with app.app_context():  # Устанавливаем контекст приложения Flask для доступа к модели
        assert TaskModel.query.get(tid).deadline == "01-01-2004"


def test_create_task(client, access_token_manager):
    headers = {'Authorization': f'Bearer {access_token_manager}'}
    data = {
        'name': 'Test Project',
        'description': 'Test project description',
        'number_of_pages': 13
    }
    response = client.post('/projects', json=data, headers=headers)

    assert response.status_code == 201
    assert 'id' in response.json
    assert response.json['name'] == data['name']


@pytest.fixture
def mocker():
    return pytest.importorskip("pytest_mock")


@pytest.fixture(scope='module')
def celery_worker():
    pass


def test_send_submission_reminder(mocker):
    # Define test data
    user_id = 123
    project_id = 456
    project_name = "Test Project"

    # Устанавливаем текущую дату и время в пятницу
    with patch('resources.task.datetime') as mock_datetime:
        my_date = datetime(2024, 5, 10)  # Пятница
        mock_datetime.now.return_value = my_date

        # Мокируем вызов функции отправки уведомления
        with patch('resources.task.send_notification') as mock_send_notification:
            # Вызываем задачу
            send_submission_reminder(user_id, project_id, project_name)

            # Ожидаемый статус и сообщение
            status = 'REQUIRES_REMINDER'
            msg = 'It`s Friday. Please submit your work'

            # Проверяем, что функция отправки уведомления была вызвана с правильными аргументами
            mock_send_notification.assert_called_once_with(user_id, project_id, project_name, status, msg)


def test_assign_translator_to_task(client, access_token_manager, access_token_translator, app):
    headers = {'Authorization': f'Bearer {access_token_manager}'}
    headers2 = {'Authorization': f'Bearer {access_token_translator}'}
    data = {
        'name': 'Test Project',
        'description': 'Test project description',
        'number_of_pages': 13
    }
    response = client.post('/projects', json=data, headers=headers)
    projid = response.json['id']

    taskdata = {
        'name': 'Test Task',
        'description': 'Test task',
        'pages': 2,
    }

    tresponse = client.post(f'/task/{projid}', json=taskdata, headers=headers)
    tid = tresponse.json["id"]

    translator_id = 1

    with app.app_context():  # Set Flask application context
        translator = UserModel.query.filter_by(username='translator123').first()
        if translator:
            translator_id = translator.id
        else:
            raise ValueError("Translator user not found")

    # Assign translator to the task
    tres = client.post(f'/task/{projid}/{tid}/translators/{translator_id}', headers=headers)
    assert tres.status_code == 200

    # Check if the translator is assigned to the task
    with app.app_context():
        task = TaskModel.query.get(tid)
        assert translator.id in [responsible.id for responsible in task.responsibles]


def test_submit_task(client, access_token_manager, access_token_translator, app):
    headers = {'Authorization': f'Bearer {access_token_manager}'}
    headers1 = {'Authorization': f'Bearer {access_token_translator}'}

    data = {
        'name': 'Test Project',
        'description': 'Test project description',
        'number_of_pages': 13
    }
    response = client.post('/projects', json=data, headers=headers)
    projid = response.json.get('id')  # Используем .get(), чтобы безопасно получить значение

    taskdata = {
        'name': 'Test Task',
        'description': 'Test task',
        'pages': 2,
    }

    tresponse = client.post(f'/task/{projid}', json=taskdata, headers=headers)
    tid = tresponse.json.get('id')  # Используем .get(), чтобы безопасно получить значение

    if not tid:
        pytest.fail("Failed to create task. Check if the project and translator exist.")

    with app.app_context():  # Устанавливаем контекст приложения Flask
        translator = UserModel.query.filter_by(username='translator123').first()
        if translator:
            translator_id = translator.id
        else:
            pytest.fail("Translator user not found.")

    # Присваиваем переводчика задаче
    tres = client.post(f'/task/{projid}/{tid}/translators/{translator_id}', headers=headers)

    # Отправляем задачу на выполнение
    sresponse = client.post(f'/task/{projid}/{tid}/submissions', json={'text': 'sadasdasda', 'pages_done': 2},
                            headers=headers1)
    assert sresponse.status_code == 201  # Убеждаемся, что запрос был успешным


def test_grade_submission_with_editor_role(client, access_token_manager, access_token_translator, access_token_editor,
                                           app):
    headers = {'Authorization': f'Bearer {access_token_manager}'}
    headers1 = {'Authorization': f'Bearer {access_token_translator}'}
    headers2 = {'Authorization': f'Bearer {access_token_editor}'}

    data = {
        'name': 'Test Project',
        'description': 'Test project description',
        'number_of_pages': 13
    }
    response = client.post('/projects', json=data, headers=headers)
    projid = response.json.get('id')  # Используем .get(), чтобы безопасно получить значение

    taskdata = {
        'name': 'Test Task',
        'description': 'Test task',
        'pages': 2,
    }

    with app.app_context():  # Устанавливаем контекст приложения Flask
        editor = UserModel.query.filter_by(username='editor123').first()
        if editor:
            editor_id = editor.id
        else:
            pytest.fail("Editor user not found.")

    response = client.post(f'/projects/{projid}/editors/{editor_id}', headers=headers)

    tresponse = client.post(f'/task/{projid}', json=taskdata, headers=headers)
    tid = tresponse.json.get('id')  # Используем .get(), чтобы безопасно получить значение

    if not tid:
        pytest.fail("Failed to create task. Check if the project and translator exist.")

    with app.app_context():  # Устанавливаем контекст приложения Flask
        translator = UserModel.query.filter_by(username='translator123').first()
        if translator:
            translator_id = translator.id
        else:
            pytest.fail("Translator user not found.")

    # Присваиваем переводчика задаче
    tres = client.post(f'/task/{projid}/{tid}/translators/{translator_id}', headers=headers)

    # Отправляем задачу на выполнение
    sresponse = client.post(f'/task/{projid}/{tid}/submissions', json={'text': 'sadasdasda', 'pages_done': 2},
                            headers=headers1)
    submission_id = sresponse.json.get('id')

    gdata = {
        "grade": 5  # Пример данных для оценки
    }

    # Выполнение запроса
    grade_response = client.put(f"/task/{projid}/{tid}/submission/{submission_id}/grade",
                                headers=headers2,
                                json=gdata)
    # Проверка ответа
    assert grade_response.status_code == 200


def test_grade_reject_with_editor_role(client, access_token_manager, access_token_translator, access_token_editor,
                                       app):
    headers = {'Authorization': f'Bearer {access_token_manager}'}
    headers1 = {'Authorization': f'Bearer {access_token_translator}'}
    headers2 = {'Authorization': f'Bearer {access_token_editor}'}

    data = {
        'name': 'Test Project',
        'description': 'Test project description',
        'number_of_pages': 13
    }
    response = client.post('/projects', json=data, headers=headers)
    projid = response.json.get('id')  # Используем .get(), чтобы безопасно получить значение

    taskdata = {
        'name': 'Test Task',
        'description': 'Test task',
        'pages': 2,
    }

    with app.app_context():  # Устанавливаем контекст приложения Flask
        editor = UserModel.query.filter_by(username='editor123').first()
        if editor:
            editor_id = editor.id
        else:
            pytest.fail("Editor user not found.")

    response = client.post(f'/projects/{projid}/editors/{editor_id}', headers=headers)

    tresponse = client.post(f'/task/{projid}', json=taskdata, headers=headers)
    tid = tresponse.json.get('id')  # Используем .get(), чтобы безопасно получить значение

    if not tid:
        pytest.fail("Failed to create task. Check if the project and translator exist.")

    with app.app_context():  # Устанавливаем контекст приложения Flask
        translator = UserModel.query.filter_by(username='translator123').first()
        if translator:
            translator_id = translator.id
        else:
            pytest.fail("Translator user not found.")

    # Присваиваем переводчика задаче
    tres = client.post(f'/task/{projid}/{tid}/translators/{translator_id}', headers=headers)

    # Отправляем задачу на выполнение
    sresponse = client.post(f'/task/{projid}/{tid}/submissions', json={'text': 'sadasdasda', 'pages_done': 2},
                            headers=headers1)
    submission_id = sresponse.json.get('id')

    cdata = {
        "comment": "dfnjskdnfkkjsdf"  # Пример данных для оценки
    }

    # Выполнение запроса
    grade_response = client.put(f"/task/{projid}/{tid}/submission/{submission_id}/reject",
                                headers=headers2,
                                json=cdata)
    # Проверка ответа
    assert grade_response.status_code == 200


@pytest.fixture
def mock_datetime():
    with patch('resources.task.datetime') as mock_dt:
        yield mock_dt

@pytest.fixture
def mock_send_notification():
    with patch('resources.task.send_notification') as mock_send:
        yield mock_send

@pytest.fixture
def mock_query():
    # Create a MagicMock object to mock the query functionality
    mock_query = MagicMock()
    # Add any necessary behavior to the mock_query
    # For example:
    # mock_query.get_or_404.return_value = mock_submission
    return mock_query