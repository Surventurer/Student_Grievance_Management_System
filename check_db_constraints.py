#!/usr/bin/env python3
"""
Check the exact foreign key constraint that's causing the issue
"""
import os
import sys
import django
import sqlite3

# Setup Django
sys.path.insert(0, r'c:\Users\Abhinav\Desktop\Student_Grievance_Management_System\src')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.authentication.models import User
from apps.students.models import StudentProfile
from django.db import connection

def check_foreign_keys():
    """Check all foreign key constraints in the database"""
    print("🔍 Checking Foreign Key Constraints")
    print("=" * 50)
    
    # Get database path
    db_path = r'c:\Users\Abhinav\Desktop\Student_Grievance_Management_System\src\db.sqlite3'
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Enable foreign key info
        cursor.execute("PRAGMA foreign_key_list(authentication_user)")
        fk_constraints = cursor.fetchall()
        
        print("🔗 Foreign keys pointing TO authentication_user table:")
        for fk in fk_constraints:
            print(f"   {fk}")
        
        # Check all tables that reference authentication_user
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        print("\n🔍 Checking all tables for references to authentication_user:")
        for table in tables:
            table_name = table[0]
            if table_name.startswith('sqlite_') or table_name == 'django_migrations':
                continue
                
            try:
                cursor.execute(f"PRAGMA foreign_key_list({table_name})")
                foreign_keys = cursor.fetchall()
                
                for fk in foreign_keys:
                    if 'authentication_user' in str(fk):
                        print(f"   Table {table_name}: {fk}")
            except Exception as e:
                print(f"   Error checking {table_name}: {e}")
        
        conn.close()
        
    except Exception as e:
        print(f"Error accessing database: {e}")

def check_specific_user_relations():
    """Check what's preventing deletion of a specific user"""
    print("\n🎯 Checking User ID 4 Relations")
    print("=" * 40)
    
    user = User.objects.get(id=4)
    print(f"User: {user.email}")
    
    # Check all related objects
    for field in user._meta.get_fields():
        if field.is_relation and hasattr(field, 'related_name'):
            try:
                if hasattr(user, field.related_name):
                    related_objects = getattr(user, field.related_name)
                    if hasattr(related_objects, 'all'):
                        count = related_objects.count()
                        if count > 0:
                            print(f"   {field.related_name}: {count} objects")
                            # Show first few objects
                            for obj in related_objects.all()[:3]:
                                print(f"     - {obj}")
                    elif hasattr(related_objects, 'id'):
                        print(f"   {field.related_name}: {related_objects}")
            except Exception as e:
                print(f"   Error checking {field.related_name}: {e}")

if __name__ == "__main__":
    try:
        check_foreign_keys()
        check_specific_user_relations()
    except Exception as e:
        print(f"❌ Script error: {e}")
        import traceback
        traceback.print_exc()
