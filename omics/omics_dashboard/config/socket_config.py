from flask_socketio import SocketIO, join_room, emit
from flask_login import current_user
import os

from data_tools.db_models import User, Notification, db

redis_host = os.environ.get('REDISSERVER', 'redis')
redis_port = int(os.environ.get('REDISPORT', 6379))
socketio = SocketIO(async_mode='gevent_uwsgi')  # , message_queue=f'redis://{redis_host}:{redis_port}')


@socketio.on('connect', namespace='/omics/notifications')
def connect_handler():
    if current_user.is_authenticated:
        user_room = f'user_{current_user.id}'
        join_room(user_room)
        emit('response', {'meta': 'WebSocket connected.'}, room=user_room)


def send_message(user: User, contents: str, color: str = 'info'):
    notification = Notification(contents=contents, color=color, read=False, recipient_id=user.id)
    db.session.add(notification)
    db.session.commit()
    user_room = f'user_{user.id}'
    emit('response',
         {
             'meta': 'New notifications.',
             'message_count': user.unread_notification_count,
             'message': user.most_recent_notification.to_dict()
         }, room=user_room, namespace='/omics/notifications')
    print('emitted')
