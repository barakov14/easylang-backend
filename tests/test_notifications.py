import pytest
from flask_jwt_extended import create_access_token
from db import db
from models import NotificationModel, UserModel
from app import create_app

@pytest.fixture
def app():
    app = create_app(db_url="sqlite:///:memory:")
    with app.app_context():
        db.create_all()
        translator = UserModel(username='translator123', name='name', surname='surname', password='123456',
                               email='trans@example.com', role='translator')
        manager = UserModel(username='manager123', name='name', surname='surname', password='123456',
                         email='manager@example.com', role='manager')
        db.session.add(manager)
        db.session.add(translator)
        notification = NotificationModel(project_name="PROJ1", project_id="123", status="ready", msg="hello world")
        db.session.add(notification)
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
def access_token_translator(app):
    with app.app_context():
        user = UserModel.query.filter_by(username='translator123').first()
        access_token = create_access_token(identity=user.id)
        return access_token

# def test_get_notifications(client, access_token):
#     headers = {'Authorization': f'Bearer {access_token}'}
#     response = client.get('/notifications', headers=headers)
#     assert response.status_code == 200
#     assert len(response.json) == 0  # Assuming there are no projects initially

# def test_get_notifications_count(client, access_token):
#     headers = {'Authorization': f'Bearer {access_token}'}
#     response = client.get('/notifications/count', headers=headers)
#     assert response.status_code == 200
#     assert len(response.json) == 1


def test_delete_notification(client, access_token):
    headers = {'Authorization': f'Bearer {access_token}'}
    data = {
        "project_name": "PROJ1", "project_id": "123", "status": "ready", "msg": "hello world"
    }
    response = client.post('/notifications', json=data, headers=headers)
    not_id = response.json['id']

    response = client.delete(f'/notifications/{not_id}', headers=headers)
    assert response.status_code == 204