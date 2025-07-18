#!/usr/bin/env python
"""
Debug script to test department API
"""
import os
import sys
import django

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.students.models import Department
from apps.students.serializers import DepartmentSerializer

def test_departments():
    """Test department serialization"""
    print("=== Department API Test ===")
    
    # Get all departments
    departments = Department.objects.all()
    print(f"Total departments in database: {departments.count()}")
    
    # Serialize departments
    serializer = DepartmentSerializer(departments, many=True)
    data = serializer.data
    
    print(f"Serialized departments: {len(data)}")
    print("\nFirst 5 departments:")
    for i, dept in enumerate(data[:5]):
        print(f"{i+1}. ID: {dept['id']}, Display Name: {dept['display_name']}")
    
    print("\nAll departments:")
    for dept in data:
        print(f"- {dept['display_name']}")
    
    print(f"\nTotal: {len(data)} departments")

if __name__ == "__main__":
    test_departments()
