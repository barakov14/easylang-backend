from os import abort

from flask.views import MethodView
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_smorest import Blueprint

from db import db
from models import NotificationModel, ProjectModel, UserModel
from models.notifications import NotificationUserModel
from schemas import NotificationSchema

blp = Blueprint("notifications", __name__, description="Operations on notifications")



@blp.route("/notifications/<int:notification_id>")
class Notification(MethodView):
    @jwt_required()
    def delete(self, notification_id):
        current_user_id = get_jwt_identity()

        # Проверяем, существует ли уведомление с указанным ID
        notification = NotificationModel.query.get_or_404(notification_id)

        # Проверяем, принадлежит ли уведомление текущему пользователю
        if not NotificationUserModel.query.filter_by(notification_id=notification_id, user_id=current_user_id).first():
            abort(403, message="You are not authorized to delete this notification")

        try:
            # Удаляем уведомление из базы данных
            db.session.delete(notification)
            db.session.commit()
            return {"message": "Notification deleted successfully"}, 200
        except Exception as e:
            db.session.rollback()
            abort(500, message=f"Failed to delete notification: {str(e)}")

@blp.route("/notifications")
class NotificationList(MethodView):
    @jwt_required()
    @blp.response(200, NotificationSchema(many=True))
    def get(self):
        current_user_id = get_jwt_identity()

        # Получаем список уведомлений для текущего пользователя
        notifications = NotificationModel.query \
            .join(NotificationUserModel) \
            .filter(NotificationUserModel.user_id == current_user_id) \
            .all()

        return notifications, 200

def send_notification(user_id, project_id, project_name, status, msg):
    # Create a new notification
    notification = NotificationModel(project_id=project_id, project_name=project_name, status=status, msg=msg)
    db.session.add(notification)
    db.session.commit()

    # Associate the notification with the user
    notification_user = NotificationUserModel(notification_id=notification.id, user_id=user_id)
    db.session.add(notification_user)
    db.session.commit()
@blp.route("/notifications/count", methods=["GET"])
class NotificationCount(MethodView):
    @jwt_required()
    def get(self):
        current_user_id = get_jwt_identity()
        user = UserModel.query.filter_by(id=current_user_id).first()
        count = user.notifications_count
        return {"count": count}, 200

@blp.route("/notifications/clear", methods=["DELETE"])
class NotificationClear(MethodView):
    @jwt_required()
    def delete(self):
        try:
            current_user_id = get_jwt_identity()
            user = UserModel.query.filter_by(id=current_user_id).first()
            user.notifications_count = 0
            db.session.commit()
            return {"message": "Notification count cleared successfully"}, 200
        except Exception as e:
            db.session.rollback()
            return {"message": f"Failed to clear notification count: {str(e)}"}, 500
