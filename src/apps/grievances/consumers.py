import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Grievance, GrievanceComment
from django.utils import timezone
from apps.students.models import StudentProfile

class GrievanceChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.grievance_id = self.scope['url_route']['kwargs']['grievance_id']
        self.room_group_name = f'chat_{self.grievance_id}'
        
        # Verify access
        user = self.scope['user']
        if not user.is_authenticated:
            await self.close()
            return
            
        has_access = await self.check_access(user, self.grievance_id)
        if not has_access:
            await self.close()
            return

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json.get('message')
        is_internal = text_data_json.get('is_internal', False)
        
        user = self.scope['user']
        
        # Students can't send internal notes
        if hasattr(user, 'is_student') and user.is_student:
            is_internal = False

        if message:
            # Save comment to database
            comment, is_anonymous = await self.save_comment(user, self.grievance_id, message, is_internal)
            
            is_student = hasattr(user, 'is_student') and user.is_student
            if is_student and is_anonymous:
                user_name = 'Anonymous Student'
                user_email = 'hidden@anonymous.local'
            else:
                user_name = user.get_full_name() or user.email
                user_email = user.email

            # Send message to room group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': message,
                    'user_name': user_name,
                    'user_email': user_email,
                    'timestamp': comment.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    'is_internal': is_internal,
                    'is_student': is_student
                }
            )

    # Receive message from room group
    async def chat_message(self, event):
        message = event['message']
        user_name = event['user_name']
        user_email = event['user_email']
        timestamp = event['timestamp']
        is_internal = event.get('is_internal', False)
        is_student = event.get('is_student', False)
        
        user = self.scope['user']
        
        # If it's an internal note, only send to non-students
        if is_internal and hasattr(user, 'is_student') and user.is_student:
            return

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message': message,
            'user_name': user_name,
            'user_email': user_email,
            'timestamp': timestamp,
            'is_internal': is_internal,
            'is_student': is_student
        }))

    @database_sync_to_async
    def check_access(self, user, grievance_id):
        try:
            grievance = Grievance.objects.get(id=grievance_id)
            if hasattr(user, 'is_superadmin') and user.is_superadmin:
                return True
            if hasattr(user, 'is_student') and user.is_student:
                return grievance.student.user == user
            admin_profile = getattr(user, 'admin_profile', None)
            if hasattr(user, 'is_officer') and user.is_officer:
                is_assigned = grievance.assigned_to and grievance.assigned_to.user == user
                is_dept = bool(admin_profile and admin_profile.department and grievance.department and grievance.department.strip().lower() == admin_profile.department.strip().lower())
                return is_assigned or is_dept
            if hasattr(user, 'is_admin') and user.is_admin:
                return bool(admin_profile and admin_profile.department and grievance.department and grievance.department.strip().lower() == admin_profile.department.strip().lower())
            return False
        except Exception:
            return False

    @database_sync_to_async
    def save_comment(self, user, grievance_id, message, is_internal):
        grievance = Grievance.objects.get(id=grievance_id)
        comment = GrievanceComment.objects.create(
            grievance=grievance,
            user=user,
            message=message,
            is_internal=is_internal
        )
        return comment, grievance.is_anonymous
