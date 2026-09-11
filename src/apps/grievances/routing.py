from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path('ws/grievances/<uuid:grievance_id>/chat/', consumers.GrievanceChatConsumer.as_asgi()),
]
