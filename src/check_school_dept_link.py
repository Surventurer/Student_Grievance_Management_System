#!/usr/bin/env python
"""
Check School-Department relationships and fix if needed
"""
import os
import sys
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
django.setup()

from apps.students.models import School, Department

print("=== SCHOOL-DEPARTMENT RELATIONSHIPS ===\n")

# Check current relationships
schools = School.objects.all()
for school in schools:
    print(f"🏫 {school.name} (ID: {school.id})")
    departments = Department.objects.filter(school=school)
    if departments.exists():
        for dept in departments:
            print(f"   └── {dept.name} (ID: {dept.id})")
    else:
        print("   └── No departments linked")
    print()

# Check departments without school assignment
unlinked_depts = Department.objects.filter(school__isnull=True)
if unlinked_depts.exists():
    print("🚨 DEPARTMENTS WITHOUT SCHOOL:")
    for dept in unlinked_depts:
        print(f"   - {dept.name} (ID: {dept.id})")
    print()

print(f"Total Schools: {School.objects.count()}")
print(f"Total Departments: {Department.objects.count()}")
print(f"Linked Departments: {Department.objects.filter(school__isnull=False).count()}")
print(f"Unlinked Departments: {Department.objects.filter(school__isnull=True).count()}")

if __name__ == "__main__":
    pass
