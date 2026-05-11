from django.db import models

class SystemSettings(models.Model):
    """
    Singleton model to store global system settings.
    """
    # General Settings
    system_name = models.CharField(max_length=255, default='Student Grievance Management System')
    contact_email = models.EmailField(default='admin@university.edu')
    max_file_size = models.IntegerField(default=10, help_text="Max file size in MB")
    email_notifications = models.BooleanField(default=True)
    auto_assignment = models.BooleanField(default=True)
    
    # Security Settings
    require_email_verification = models.BooleanField(default=True)
    allow_student_registration = models.BooleanField(default=True)
    session_timeout = models.IntegerField(default=60, help_text="Session timeout in minutes")
    password_min_length = models.IntegerField(default=8)
    
    # Grievance Settings
    DEFAULT_PRIORITIES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    default_priority = models.CharField(max_length=10, choices=DEFAULT_PRIORITIES, default='medium')
    auto_resolve_days = models.IntegerField(default=30)
    escalation_threshold = models.IntegerField(default=7)
    allow_anonymous = models.BooleanField(default=False)

    # AI & Knowledge Base Settings
    enable_auto_suggestions = models.BooleanField(default=True)
    auto_categorize = models.BooleanField(default=True)
    kb_confidence_score = models.IntegerField(default=80, help_text="Percentage 50-100")

    # Workflow & SLA Settings
    max_reopen_count = models.IntegerField(default=2)
    SLA_BREACH_ACTIONS = [
        ('notify', 'Notify Admin Only'),
        ('escalate', 'Auto-Escalate Immediately'),
        ('both', 'Notify & Auto-Escalate'),
    ]
    sla_breach_action = models.CharField(max_length=20, choices=SLA_BREACH_ACTIONS, default='escalate')
    require_closure_remark = models.BooleanField(default=True)

    # Student Experience Settings
    enable_feedback = models.BooleanField(default=True)
    allow_attachments_in_replies = models.BooleanField(default=True)
    support_hours = models.CharField(max_length=255, default='Mon-Fri, 9:00 AM - 5:00 PM')

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "System Settings"
        verbose_name_plural = "System Settings"

    def save(self, *args, **kwargs):
        """ Ensure only one instance exists """
        self.pk = 1
        super(SystemSettings, self).save(*args, **kwargs)

    @classmethod
    def load(cls):
        """ Load the singleton instance """
        obj, created = cls.objects.get_or_create(pk=1)
        return obj
