import os
import sys
import django

# Set up Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.authentication.forms import StudentRegistrationForm
from apps.students.models import School

# Create a form instance
form = StudentRegistrationForm()

# Print the school select HTML
print("SCHOOL SELECT HTML:")
print("=" * 50)
print(form['school'])
print()

# Print the department select HTML
print("DEPARTMENT SELECT HTML:")
print("=" * 50)
print(form['department'])
print()

# Check available schools
print("AVAILABLE SCHOOLS:")
print("=" * 50)
schools = School.objects.all()
for school in schools:
    print(f"ID: {school.id}, Name: {school.name}")
print()

# Check the HTML attributes
print("SCHOOL FIELD ATTRIBUTES:")
print("=" * 50)
print(f"Widget: {form.fields['school'].widget}")
print(f"Widget attrs: {form.fields['school'].widget.attrs}")
print()

print("DEPARTMENT FIELD ATTRIBUTES:")
print("=" * 50)
print(f"Widget: {form.fields['department'].widget}")
print(f"Widget attrs: {form.fields['department'].widget.attrs}")
