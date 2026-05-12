from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('students', '0002_adminprofile_name'),
    ]

    operations = [
        migrations.DeleteModel(
            name='UserActivity',
        ),
    ]