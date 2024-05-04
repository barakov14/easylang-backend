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
        user = UserModel(username='manager123', name='name', surname='surname', password='123456',
                         email='manager@example.com', role='manager')
        db.session.add(user)
        db.session.commit()
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def access_token(app):
    with app.app_context():
        user = UserModel.query.filter_by(username='manager123').first()
        access_token = create_access_token(identity=user.id)
        return access_token

def test_create_project(client, access_token):
    headers = {'Authorization': f'Bearer {access_token}'}
    data = {
        'name': 'Test Project',
        'description': 'Test project description',
        'number_of_pages': 10
    }
    response = client.post('/projects', json=data, headers=headers)
    assert response.status_code == 201
    assert 'id' in response.json
    assert response.json['name'] == data['name']

def test_get_projects(client, access_token):
    headers = {'Authorization': f'Bearer {access_token}'}
    response = client.get('/projects', headers=headers)
    assert response.status_code == 200
    assert len(response.json) == 0  # Assuming there are no projects initially

def test_get_single_project(client, access_token):
    headers = {'Authorization': f'Bearer {access_token}'}
    data = {
        'name': 'Test Project',
        'description': 'Test project description',
        'number_of_pages': 10
    }
    response = client.post('/projects', json=data, headers=headers)
    project_id = response.json['id']

    response = client.get(f'/projects/{project_id}', headers=headers)
    assert response.status_code == 200
    assert response.json['id'] == project_id

def test_update_project(client, access_token):
    headers = {'Authorization': f'Bearer {access_token}'}
    data = {
        'name': 'Test Project',
        'description': 'Test project description',
        'number_of_pages': 10
    }
    response = client.post('/projects', json=data, headers=headers)
    project_id = response.json['id']

    updated_data = {
        'name': 'Updated Project',
        'description': 'Updated project description',
        'number_of_pages': 20
    }
    response = client.put(f'/projects/{project_id}', json=updated_data, headers=headers)
    assert response.status_code == 200
    assert response.json['name'] == updated_data['name']
    assert response.json['description'] == updated_data['description']
    assert response.json['number_of_pages'] == updated_data['number_of_pages']

def test_delete_project(client, access_token):
    headers = {'Authorization': f'Bearer {access_token}'}
    data = {
        'name': 'Test Project',
        'description': 'Test project description',
        'number_of_pages': 10
    }
    response = client.post('/projects', json=data, headers=headers)
    project_id = response.json['id']

    response = client.delete(f'/projects/{project_id}', headers=headers)
    assert response.status_code == 204

def test_add_project_editor(client, access_token):
    headers = {'Authorization': f'Bearer {access_token}'}
    data = {
        'name': 'Test Project',
        'description': 'Test project description',
        'number_of_pages': 10
    }
    response = client.post('/projects', json=data, headers=headers)
    assert response.status_code == 201  # Ensure project creation is successful
    project_id = response.json['id']
    print("Project created successfully. ID:", project_id)

    editor_data = {
        'username': 'editor123',
        'name': 'Editor',
        'surname': 'Surname',
        'password': '123456',
        'email': 'editor1231@example.com',
        'role': 'editor'
    }
    # Step 1: Register the editor
    response = client.post('/register', json=editor_data)
    assert response.status_code == 201  # Ensure editor registration is successful
    editor_id = response.json['id']
    print("Editor registered successfully. ID:", editor_id)

    # Step 2: Add the registered editor to the project
    response = client.post(f'/projects/{project_id}/editors/{editor_id}', headers=headers)
    assert response.status_code == 200
    print("Editor added to the project successfully.")

    # Additional checks if needed
    assert response.json['username'] == editor_data['username']




def test_get_user_projects(client, access_token):
    headers = {'Authorization': f'Bearer {access_token}'}
    response = client.get('/projects/user', headers=headers)
    assert response.status_code == 200
    assert len(response.json) == 0  # Assuming there are no projects initially
