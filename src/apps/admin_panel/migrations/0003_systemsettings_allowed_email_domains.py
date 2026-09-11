# Generated manually for allowed_email_domains

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('admin_panel', '0002_remove_systemsettings_enable_feedback'),
    ]

    operations = [
        migrations.AddField(
            model_name='systemsettings',
            name='allowed_email_domains',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Comma-separated allowed domains for registration (e.g. university.edu). Leave empty to allow any valid email.',
                max_length=255,
                null=True,
            ),
        ),
    ]

