import pytest
from flask_jwt_extended import create_access_token
from db import db
from models import UserModel, TaskModel
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

def test_manager_access(client, access_token_manager):
    headers = {'Authorization': f'Bearer {access_token_manager}'}
    response = client.get('/projects', headers=headers)
    assert response.status_code == 200

def test_editor_access(client, access_token_editor):
    headers = {'Authorization': f'Bearer {access_token_editor}'}
    response = client.get('/projects', headers=headers)
    assert response.status_code == 200

def test_translator_access(client, access_token_translator):
    headers = {'Authorization': f'Bearer {access_token_translator}'}
    response = client.get('/projects', headers=headers)
    assert response.status_code == 200
