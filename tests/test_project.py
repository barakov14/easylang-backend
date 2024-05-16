from datetime import datetime

import pytest
from flask_jwt_extended import create_access_token
from db import db
from models import UserModel
from app import create_app


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
        user = UserModel.query.filter_by(username='manager123').first()
        access_token = create_access_token(identity=user.id)
        return access_token


def test_create_project(client, access_token_manager):
    headers = {'Authorization': f'Bearer {access_token_manager}'}
    data = {
        'name': 'Test Project',
        'description': 'Test project description',
        'number_of_pages': 10,
        'deadline': datetime.utcnow()
    }
    response = client.post('/projects', json=data, headers=headers)
    assert response.status_code == 201
    assert 'id' in response.json
    assert response.json['name'] == data['name']


def test_get_projects(client, access_token_manager):
    headers = {'Authorization': f'Bearer {access_token_manager}'}
    response = client.get('/projects', headers=headers)
    assert response.status_code == 200
    assert len(response.json) == 0  # Assuming there are no projects initially


def test_get_single_project(client, access_token_manager):
    headers = {'Authorization': f'Bearer {access_token_manager}'}
    data = {
        'name': 'Test Project',
        'description': 'Test project description',
        'number_of_pages': 10,
        'deadline': datetime.utcnow()
    }
    response = client.post('/projects', json=data, headers=headers)
    project_id = response.json['id']

    response = client.get(f'/projects/{project_id}', headers=headers)
    assert response.status_code == 200
    assert response.json['id'] == project_id



def test_delete_project(client, access_token_manager):
    headers = {'Authorization': f'Bearer {access_token_manager}'}
    data = {
        'name': 'Test Project',
        'description': 'Test project description',
        'number_of_pages': 10,
        'deadline': datetime.utcnow()
    }
    response = client.post('/projects', json=data, headers=headers)
    project_id = response.json['id']

    response = client.delete(f'/projects/{project_id}', headers=headers)
    assert response.status_code == 204


def test_add_project_editor(client, access_token_manager, app):
    headers = {'Authorization': f'Bearer {access_token_manager}'}

    data = {
        'name': 'Test Project',
        'description': 'Test project description',
        'number_of_pages': 13,
        'deadline': datetime.utcnow()
    }
    response = client.post('/projects', json=data, headers=headers)
    projid = response.json.get('id')  # Используем .get(), чтобы безопасно получить значение

    with app.app_context():  # Устанавливаем контекст приложения Flask
        editor = UserModel.query.filter_by(username='editor123').first()
        if editor:
            editor_id = editor.id
        else:
            pytest.fail("Editor user not found.")

    response = client.post(f'/projects/{projid}/editors/{editor_id}', headers=headers)  # Print the response content
    assert response.status_code == 200  # Ensure editor registration is successful


def test_get_user_projects(client, access_token_manager):
    headers = {'Authorization': f'Bearer {access_token_manager}'}
    response = client.get('/projects/user', headers=headers)
    assert response.status_code == 200
    assert len(response.json) == 0  # Assuming there are no projects initially
