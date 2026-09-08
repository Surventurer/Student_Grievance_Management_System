import csv
import json
import uuid
from datetime import datetime, timedelta

from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.db import transaction, IntegrityError
from django.db.models import Count, Q, Avg, Sum, Case, When, IntegerField, F, Max
from django.utils import timezone
from django.core.paginator import Paginator
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.grievances.models import (
    Grievance, Category, GrievanceComment, AuditLog, CategoryAssignment,
    GrievanceAttachment, GrievanceStatusHistory, GrievanceAssignmentHistory
)
from apps.notifications.models import Notification
from apps.students.models import School, Department, StudentProfile, AdminProfile
from apps.authentication.models import User
from apps.authentication.decorators import (
    dept_admin_required, admin_required, superadmin_required, permission_required, role_required
)
from apps.admin_panel.permissions import (
    filter_grievances_by_access, filter_students_by_access, can_access_all_data,
    can_manage_system_settings, can_manage_categories, can_manage_auto_assignment,
    can_view_audit_logs, can_view_system_reports, department_access_required
)


@login_required
def departments_api(request):
    """API endpoint to get departments by school"""
    if not request.user.is_admin_or_officer:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    school_id = request.GET.get('school')
    if school_id:
        from apps.students.models import Department
        departments = Department.objects.filter(
            school_id=school_id, 
            school__is_active=True, 
            is_active=True
        ).values('id', 'name')
        return JsonResponse({'departments': list(departments)})
    else:
        from apps.students.models import Department
        departments = Department.objects.filter(
            school__is_active=True, 
            is_active=True
        ).values('id', 'name')
        return JsonResponse({'departments': list(departments)})



@login_required
def department_management(request):
    """Department management view"""
    if not hasattr(request.user, 'is_admin') or not request.user.is_admin_or_officer:
        messages.error(request, 'Access denied - Admin privileges required')
        return redirect('authentication:login')
    
    from apps.students.models import Department, School, StudentProfile
    
    # Get filter parameters
    search = request.GET.get('search', '').strip()
    school_filter = request.GET.get('school', '')
    status = request.GET.get('status', '')
    hod_status = request.GET.get('hod_status', '')
    sort = request.GET.get('sort', 'name')
    per_page = int(request.GET.get('per_page', 10))
    
    # Start with all departments
    departments = Department.objects.select_related('school', 'head_of_department')
    
    # Apply search filter
    if search:
        departments = departments.filter(
            Q(name__icontains=search) | 
            Q(school__name__icontains=search) |
            Q(description__icontains=search)
        )
    
    # Apply school filter
    if school_filter:
        departments = departments.filter(school_id=school_filter)
    
    # Apply status filter
    if status == 'active':
        departments = departments.filter(is_active=True)
    elif status == 'inactive':
        departments = departments.filter(is_active=False)
    
    # Apply HOD filter
    if hod_status == 'with_hod':
        departments = departments.filter(head_of_department__isnull=False)
    elif hod_status == 'without_hod':
        departments = departments.filter(head_of_department__isnull=True)
    
    # Calculate statistics (before applying sorting and pagination)
    total_departments = Department.objects.count()
    active_departments = Department.objects.filter(is_active=True).count()
    inactive_departments = Department.objects.filter(is_active=False).count()
    with_hod = Department.objects.filter(head_of_department__isnull=False).count()
    total_students = StudentProfile.objects.count()
    
    stats = {
        'total': total_departments,
        'active': active_departments,
        'inactive': inactive_departments,
        'with_hod': with_hod,
        'total_students': total_students
    }
    
    # Apply sorting
    if sort == 'name':
        departments = departments.order_by('name')
    elif sort == '-created_at':
        departments = departments.order_by('-created_at')
    elif sort == 'created_at':
        departments = departments.order_by('created_at')
    elif sort == 'school':
        departments = departments.order_by('school__name')
    else:
        departments = departments.order_by('name')
    
    # Note: We'll get student counts in the template since it's not a direct FK relationship
    
    # Pagination
    paginator = Paginator(departments, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'departments': page_obj,
        'page_obj': page_obj,
        'stats': stats,
        'schools': School.objects.filter(is_active=True).order_by('name'),
        'search': search,
        'school_filter': school_filter,
        'status': status,
        'hod_status': hod_status,
        'page_title': 'Department Management'
    }
    return render(request, 'admin_panel/department_management.html', context)



@login_required
@require_http_methods(["GET"])
def departments_api(request):
    """API endpoint for getting departments list"""
    if not hasattr(request.user, 'is_admin') or not request.user.is_admin_or_officer:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    from apps.students.models import Department
    
    departments = Department.objects.select_related('school').filter(is_active=True).order_by('name')
    
    departments_data = []
    for dept in departments:
        departments_data.append({
            'id': dept.id,
            'name': dept.name,
            'school_name': dept.school.name if dept.school else None,
            'school_id': dept.school.id if dept.school else None,
            'current_hod': {
                'id': dept.head_of_department.id,
                'name': dept.head_of_department.get_full_name(),
                'email': dept.head_of_department.email
            } if dept.head_of_department else None
        })
    
    return JsonResponse({'departments': departments_data})



@login_required
@require_http_methods(["GET", "POST"])
def user_hod_assignment_api(request, user_id):
    """API endpoint for getting/setting user HOD assignment"""
    if not hasattr(request.user, 'is_admin') or not request.user.is_admin_or_officer:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    from apps.authentication.models import User
    from apps.students.models import Department
    
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)
    
    if request.method == 'GET':
        # Get current HOD assignment
        try:
            department = Department.objects.get(head_of_department=user)
            return JsonResponse({
                'department_id': department.id,
                'department_name': department.name,
                'school_name': department.school.name if department.school else None
            })
        except Department.DoesNotExist:
            return JsonResponse({'department_id': None})
    
    elif request.method == 'POST':
        import json
        try:
            data = json.loads(request.body)
            department_id = data.get('department_id')
            
            # Remove user from any current HOD assignments
            Department.objects.filter(head_of_department=user).update(head_of_department=None)
            
            # Assign to new department if specified
            if department_id:
                try:
                    department = Department.objects.get(id=department_id)
                    
                    # Remove any existing HOD from this department
                    if department.head_of_department:
                        old_hod = department.head_of_department
                        AuditLog.objects.create(
                            user=request.user,
                            action='hod_removed',
                            description=f'Removed {old_hod.get_full_name()} as HOD of {department.name}',
                            target_model='Department',
                            target_id=str(department.id)
                        )
                    
                    # Assign new HOD
                    department.head_of_department = user
                    department.save()
                    
                    # Create audit log
                    AuditLog.objects.create(
                        user=request.user,
                        action='hod_assigned',
                        description=f'Assigned {user.get_full_name()} as HOD of {department.name}',
                        target_model='Department',
                        target_id=str(department.id)
                    )
                    
                    return JsonResponse({
                        'success': True,
                        'message': f'{user.get_full_name()} assigned as HOD of {department.name}'
                    })
                    
                except Department.DoesNotExist:
                    return JsonResponse({'error': 'Department not found'}, status=404)
            else:
                # Just remove from any HOD assignments
                AuditLog.objects.create(
                    user=request.user,
                    action='hod_removed',
                    description=f'Removed {user.get_full_name()} from all HOD assignments',
                    target_model='User',
                    target_id=str(user.id)
                )
                
                return JsonResponse({
                    'success': True,
                    'message': f'{user.get_full_name()} removed from HOD assignments'
                })
                
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)



@login_required
@require_http_methods(["GET", "POST"])
def department_create(request):
    """Create new department"""
    if not hasattr(request.user, 'is_admin') or not request.user.is_admin_or_officer:
        messages.error(request, 'Access denied - Admin privileges required')
        return redirect('authentication:login')
    
    if request.method == 'POST':
        try:
            from apps.students.models import Department, School
            
            name = request.POST.get('name', '').strip()
            school_id = request.POST.get('school')
            
            if not name:
                messages.error(request, 'Department name is required')
                return render(request, 'admin_panel/department_form.html', {
                    'schools': School.objects.filter(is_active=True).order_by('name'),
                    'form_data': request.POST
                })
            
            school = None
            if school_id:
                try:
                    school = School.objects.get(id=school_id)
                except School.DoesNotExist:
                    messages.error(request, 'Selected school does not exist')
                    return render(request, 'admin_panel/department_form.html', {
                        'schools': School.objects.filter(is_active=True).order_by('name'),
                        'form_data': request.POST
                    })
            
            # Check for duplicate names within the same school
            if school:
                if Department.objects.filter(name__iexact=name, school=school).exists():
                    messages.error(request, f'A department with this name already exists in {school.name}')
                    return render(request, 'admin_panel/department_form.html', {
                        'schools': School.objects.filter(is_active=True).order_by('name'),
                        'form_data': request.POST
                    })
            else:
                if Department.objects.filter(name__iexact=name, school__isnull=True).exists():
                    messages.error(request, 'A department with this name already exists')
                    return render(request, 'admin_panel/department_form.html', {
                        'schools': School.objects.filter(is_active=True).order_by('name'),
                        'form_data': request.POST
                    })
            
            # Handle HOD assignment
            head_of_department = None
            hod_id = request.POST.get('head_of_department')
            if hod_id:
                try:
                    from apps.authentication.models import User
                    head_of_department = User.objects.get(id=hod_id)
                except User.DoesNotExist:
                    messages.error(request, 'Selected HOD does not exist')
                    return render(request, 'admin_panel/department_form.html', {
                        'schools': School.objects.filter(is_active=True).order_by('name'),
                        'form_data': request.POST
                    })
            
            department = Department.objects.create(
                name=name,
                school=school,
                head_of_department=head_of_department
            )
            
            # Create audit log
            hod_info = f' (HOD: {head_of_department.get_full_name()})' if head_of_department else ''
            AuditLog.objects.create(
                user=request.user,
                action='department_create',
                description=f'Created department: {department.name}' + (f' in {school.name}' if school else '') + hod_info,
                target_model='Department',
                target_id=str(department.id)
            )
            
            messages.success(request, f'Department "{department.name}" created successfully')
            return redirect('admin_panel:department_management')
            
        except Exception as e:
            messages.error(request, f'Error creating department: {str(e)}')
    
    from apps.students.models import School
    context = {
        'schools': School.objects.filter(is_active=True).order_by('name'),
        'action': 'Create',
        'page_title': 'Create Department'
    }
    return render(request, 'admin_panel/department_form.html', context)



@login_required
@require_http_methods(["GET", "POST"])
def department_edit(request, department_id):
    """Edit existing department"""
    if not hasattr(request.user, 'is_admin') or not request.user.is_admin_or_officer:
        messages.error(request, 'Access denied - Admin privileges required')
        return redirect('authentication:login')
    
    from apps.students.models import Department, School
    
    department = get_object_or_404(Department, id=department_id)
    
    if request.method == 'POST':
        try:
            name = request.POST.get('name', '').strip()
            school_id = request.POST.get('school')
            
            if not name:
                messages.error(request, 'Department name is required')
                return render(request, 'admin_panel/department_form.html', {
                    'department': department,
                    'schools': School.objects.filter(is_active=True).order_by('name'),
                    'form_data': request.POST
                })
            
            school = None
            if school_id:
                try:
                    school = School.objects.get(id=school_id)
                except School.DoesNotExist:
                    messages.error(request, 'Selected school does not exist')
                    return render(request, 'admin_panel/department_form.html', {
                        'department': department,
                        'schools': School.objects.filter(is_active=True).order_by('name'),
                        'form_data': request.POST
                    })
            
            # Check for duplicate names (excluding current department)
            if school:
                if Department.objects.filter(name__iexact=name, school=school).exclude(id=department.id).exists():
                    messages.error(request, f'A department with this name already exists in {school.name}')
                    return render(request, 'admin_panel/department_form.html', {
                        'department': department,
                        'schools': School.objects.filter(is_active=True).order_by('name'),
                        'form_data': request.POST
                    })
            else:
                if Department.objects.filter(name__iexact=name, school__isnull=True).exclude(id=department.id).exists():
                    messages.error(request, 'A department with this name already exists')
                    return render(request, 'admin_panel/department_form.html', {
                        'department': department,
                        'schools': School.objects.filter(is_active=True).order_by('name'),
                        'form_data': request.POST
                    })
            
            # Handle HOD assignment
            head_of_department = None
            hod_id = request.POST.get('head_of_department')
            if hod_id:
                try:
                    from apps.authentication.models import User
                    head_of_department = User.objects.get(id=hod_id)
                except User.DoesNotExist:
                    messages.error(request, 'Selected HOD does not exist')
                    return render(request, 'admin_panel/department_form.html', {
                        'department': department,
                        'schools': School.objects.filter(is_active=True).order_by('name'),
                        'form_data': request.POST
                    })
            
            old_name = department.name
            old_school = department.school
            old_hod = department.head_of_department
            
            # Update department fields
            department.name = name
            department.school = school
            department.head_of_department = head_of_department
            department.save()
            
            # Create audit log
            school_info = f' in {school.name}' if school else ''
            old_school_info = f' in {old_school.name}' if old_school else ''
            
            # Build HOD change info
            hod_change_info = ''
            if old_hod != head_of_department:
                if old_hod and head_of_department:
                    hod_change_info = f' (HOD: {old_hod.get_full_name()} → {head_of_department.get_full_name()})'
                elif head_of_department:
                    hod_change_info = f' (HOD assigned: {head_of_department.get_full_name()})'
                elif old_hod:
                    hod_change_info = f' (HOD removed: {old_hod.get_full_name()})'
            
            AuditLog.objects.create(
                user=request.user,
                action='department_update',
                description=f'Updated department: {old_name}{old_school_info} → {department.name}{school_info}{hod_change_info}',
                target_model='Department',
                target_id=str(department.id)
            )
            
            messages.success(request, f'Department "{department.name}" updated successfully')
            return redirect('admin_panel:department_management')
            
        except Exception as e:
            messages.error(request, f'Error updating department: {str(e)}')
    
    context = {
        'department': department,
        'schools': School.objects.filter(is_active=True).order_by('name'),
        'action': 'Edit',
        'page_title': 'Edit Department'
    }
    return render(request, 'admin_panel/department_form.html', context)



@login_required
@require_http_methods(["POST"])
def department_delete(request, department_id):
    """Delete department"""
    if not hasattr(request.user, 'is_admin') or not request.user.is_admin_or_officer:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    try:
        from apps.students.models import Department, StudentProfile
        
        department = get_object_or_404(Department, id=department_id)
        
        # Check if department has students
        student_count = StudentProfile.objects.filter(department=department.name).count()
        if student_count > 0:
            return JsonResponse({
                'error': f'Cannot delete department. It has {student_count} associated students.'
            }, status=400)
        
        # Check if department has admin profiles
        admin_count = AdminProfile.objects.filter(department=department.name).count()
        if admin_count > 0:
            return JsonResponse({
                'error': f'Cannot delete department. It has {admin_count} associated admin profiles.'
            }, status=400)
        
        department_name = department.name
        school_name = department.school.name if department.school else None
        
        department.delete()
        
        # Create audit log
        school_info = f' from {school_name}' if school_name else ''
        AuditLog.objects.create(
            user=request.user,
            action='department_delete',
            description=f'Deleted department: {department_name}{school_info}',
            target_model='Department',
            target_id=str(department_id)
        )
        
        return JsonResponse({'success': True, 'message': f'Department "{department_name}" deleted successfully'})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)



@login_required
@require_http_methods(["POST"])
def bulk_activate_departments(request):
    """Bulk activate departments"""
    if not hasattr(request.user, 'is_admin') or not request.user.is_admin_or_officer:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    try:
        import json
        from apps.students.models import Department
        
        data = json.loads(request.body)
        department_ids = data.get('department_ids', [])
        
        if not department_ids:
            return JsonResponse({'error': 'No departments selected'}, status=400)
        
        # Update departments
        activated_count = Department.objects.filter(
            id__in=department_ids,
            is_active=False
        ).update(is_active=True)
        
        # Create audit log
        AuditLog.objects.create(
            user=request.user,
            action='bulk_activate_departments',
            description=f'Bulk activated {activated_count} departments',
            target_model='Department',
            target_id=str(department_ids)
        )
        
        return JsonResponse({
            'success': True, 
            'message': f'Successfully activated {activated_count} department(s)',
            'activated_count': activated_count
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)



@login_required
@require_http_methods(["POST"])
def bulk_deactivate_departments(request):
    """Bulk deactivate departments"""
    if not hasattr(request.user, 'is_admin') or not request.user.is_admin_or_officer:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    try:
        import json
        from apps.students.models import Department
        
        data = json.loads(request.body)
        department_ids = data.get('department_ids', [])
        
        if not department_ids:
            return JsonResponse({'error': 'No departments selected'}, status=400)
        
        # Update departments
        deactivated_count = Department.objects.filter(
            id__in=department_ids,
            is_active=True
        ).update(is_active=False)
        
        # Create audit log
        AuditLog.objects.create(
            user=request.user,
            action='bulk_deactivate_departments',
            description=f'Bulk deactivated {deactivated_count} departments',
            target_model='Department',
            target_id=str(department_ids)
        )
        
        return JsonResponse({
            'success': True, 
            'message': f'Successfully deactivated {deactivated_count} department(s)',
            'deactivated_count': deactivated_count
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)



@login_required
@require_http_methods(["POST"])
def bulk_delete_departments(request):
    """Bulk delete departments"""
    if not hasattr(request.user, 'is_admin') or not request.user.is_admin_or_officer:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    try:
        import json
        from apps.students.models import Department, StudentProfile
        
        data = json.loads(request.body)
        department_ids = data.get('department_ids', [])
        
        if not department_ids:
            return JsonResponse({'error': 'No departments selected'}, status=400)
        
        # Check if any department has students
        departments_with_students = []
        for dept_id in department_ids:
            try:
                dept = Department.objects.get(id=dept_id)
                student_count = StudentProfile.objects.filter(department=dept.name).count()
                if student_count > 0:
                    departments_with_students.append(f"{dept.name} ({student_count} students)")
            except Department.DoesNotExist:
                continue
        
        if departments_with_students:
            return JsonResponse({
                'error': f'Cannot delete departments with students: {", ".join(departments_with_students)}'
            }, status=400)
        
        # Get department names for audit log
        department_names = list(Department.objects.filter(
            id__in=department_ids
        ).values_list('name', flat=True))
        
        # Delete departments
        deleted_count, _ = Department.objects.filter(id__in=department_ids).delete()
        
        # Create audit log
        AuditLog.objects.create(
            user=request.user,
            action='bulk_delete_departments',
            description=f'Bulk deleted {deleted_count} departments: {", ".join(department_names)}',
            target_model='Department',
            target_id=str(department_ids)
        )
        
        return JsonResponse({
            'success': True, 
            'message': f'Successfully deleted {deleted_count} department(s)',
            'deleted_count': deleted_count
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

