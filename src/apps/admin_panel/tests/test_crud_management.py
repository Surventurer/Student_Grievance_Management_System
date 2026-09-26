from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from apps.students.models import School, Department, AdminProfile
from apps.grievances.models import Category

User = get_user_model()


class CrudManagementTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.superadmin = User.objects.create_user(email="super_crud@univ.edu", password="Pw!", role="superadmin")
        self.super_prof = AdminProfile.objects.create(
            user=self.superadmin, role_level="superadmin", department="Central", employee_id="SA_CRUD"
        )
        self.client.force_login(self.superadmin)

    def test_school_create_and_edit(self):
        # Create School
        create_url = reverse('admin_panel:school_create')
        response = self.client.post(create_url, {
            'name': 'School of Humanities',
            'code': 'SOH',
            'description': 'Humanities and Arts'
        })
        self.assertEqual(response.status_code, 302)
        school = School.objects.filter(code='SOH').first()
        self.assertIsNotNone(school)
        self.assertEqual(school.name, 'School of Humanities')

        # Edit School
        edit_url = reverse('admin_panel:school_edit', kwargs={'school_id': school.id})
        response2 = self.client.post(edit_url, {
            'name': 'School of Humanities and Social Sciences',
            'code': 'SOHSS',
            'description': 'Updated description'
        })
        self.assertEqual(response2.status_code, 302)
        school.refresh_from_db()
        self.assertEqual(school.name, 'School of Humanities and Social Sciences')
        self.assertEqual(school.code, 'SOHSS')

    def test_department_create_and_edit(self):
        school = School.objects.create(name="School of Management", code="SOM")
        create_url = reverse('admin_panel:department_create')

        response = self.client.post(create_url, {
            'name': 'Finance and Accounting',
            'school': school.id
        })
        self.assertEqual(response.status_code, 302)
        dept = Department.objects.filter(name='Finance and Accounting').first()
        self.assertIsNotNone(dept)
        self.assertEqual(dept.school, school)

        # Edit Department
        edit_url = reverse('admin_panel:department_edit', kwargs={'department_id': dept.id})
        response2 = self.client.post(edit_url, {
            'name': 'Finance, Banking and Accounting',
            'school': school.id
        })
        self.assertEqual(response2.status_code, 302)
        dept.refresh_from_db()
        self.assertEqual(dept.name, 'Finance, Banking and Accounting')

    def test_category_create_and_edit(self):
        create_url = reverse('admin_panel:category_create')
        response = self.client.post(create_url, {
            'name': 'Mess Food Quality',
            'category_type': 'non_academic',
            'sla_hours': 36,
            'description': 'Mess food cleanliness and hygiene',
            'auto_assign_enabled': 'on'
        })
        self.assertEqual(response.status_code, 302)
        cat = Category.objects.filter(name='Mess Food Quality').first()
        self.assertIsNotNone(cat)
        self.assertEqual(cat.sla_hours, 36)

        # Edit Category
        edit_url = reverse('admin_panel:category_edit', kwargs={'category_id': cat.id})
        response2 = self.client.post(edit_url, {
            'name': 'Dining & Mess Hygiene',
            'category_type': 'non_academic',
            'sla_hours': 24,
            'description': 'Updated description',
            'auto_assign_enabled': 'on'
        })
        self.assertEqual(response2.status_code, 302)
        cat.refresh_from_db()
        self.assertEqual(cat.name, 'Dining & Mess Hygiene')
        self.assertEqual(cat.sla_hours, 24)

    def test_category_toggle_status(self):
        cat = Category.objects.create(
            name='Hostel Wi-Fi',
            category_type='non_academic',
            is_active=True
        )
        toggle_url = reverse('admin_panel:toggle_category_status', kwargs={'category_id': cat.id})
        
        # Deactivate
        response = self.client.post(toggle_url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertFalse(data['is_active'])
        self.assertEqual(data['status'], 'deactivated')
        cat.refresh_from_db()
        self.assertFalse(cat.is_active)

        # Reactivate
        response2 = self.client.post(toggle_url)
        self.assertEqual(response2.status_code, 200)
        data2 = response2.json()
        self.assertTrue(data2['success'])
        self.assertTrue(data2['is_active'])
        self.assertEqual(data2['status'], 'activated')
        cat.refresh_from_db()
        self.assertTrue(cat.is_active)

    def test_category_bulk_update_status(self):
        cat1 = Category.objects.create(name='Cat 1', category_type='academic', is_active=True)
        cat2 = Category.objects.create(name='Cat 2', category_type='non_academic', is_active=True)
        
        bulk_url = reverse('admin_panel:bulk_update_category_status')
        
        # Bulk deactivate
        response = self.client.post(
            bulk_url,
            data={'category_ids': [str(cat1.id), str(cat2.id)], 'is_active': False},
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['updated_count'], 2)
        cat1.refresh_from_db()
        cat2.refresh_from_db()
        self.assertFalse(cat1.is_active)
        self.assertFalse(cat2.is_active)

        # Bulk activate
        response2 = self.client.post(
            bulk_url,
            data={'category_ids': [str(cat1.id), str(cat2.id)], 'is_active': True},
            content_type='application/json'
        )
        self.assertEqual(response2.status_code, 200)
        data2 = response2.json()
        self.assertTrue(data2['success'])
        cat1.refresh_from_db()
        cat2.refresh_from_db()
        self.assertTrue(cat1.is_active)
        self.assertTrue(cat2.is_active)

