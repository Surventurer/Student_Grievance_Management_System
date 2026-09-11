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
def school_management(request):
    """School management view"""
    if not hasattr(request.user, 'is_admin') or not request.user.is_admin_or_officer:
        messages.error(request, 'Access denied - Admin privileges required')
        return redirect('authentication:login')
    
    from apps.students.models import School, Department
    
    # Get filter parameters
    search = request.GET.get('search', '').strip()
    status = request.GET.get('status', '')
    sort = request.GET.get('sort', 'name')
    per_page = int(request.GET.get('per_page', 10))
    
    # Start with all schools
    schools = School.objects.all()
    
    # Apply search filter
    if search:
        schools = schools.filter(
            Q(name__icontains=search) | 
            Q(code__icontains=search) |
            Q(description__icontains=search)
        )
    
    # Apply status filter
    if status == 'active':
        schools = schools.filter(is_active=True)
    elif status == 'inactive':
        schools = schools.filter(is_active=False)
    
    # Calculate statistics (before applying sorting and pagination)
    total_schools = School.objects.count()
    active_schools = School.objects.filter(is_active=True).count()
    inactive_schools = School.objects.filter(is_active=False).count()
    total_departments = Department.objects.count()
    
    stats = {
        'total': total_schools,
        'active': active_schools,
        'inactive': inactive_schools,
        'total_departments': total_departments
    }
    
    # Apply sorting
    if sort == 'name':
        schools = schools.order_by('name')
    elif sort == '-created_at':
        schools = schools.order_by('-created_at')
    elif sort == 'created_at':
        schools = schools.order_by('created_at')
    elif sort == 'code':
        schools = schools.order_by('code')
    else:
        schools = schools.order_by('name')
    
    # Annotate with department count
    schools = schools.annotate(
        department_count=Count('departments')
    )
    
    # Pagination
    paginator = Paginator(schools, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'schools': page_obj,
        'page_obj': page_obj,
        'stats': stats,
        'search': search,
        'page_title': 'School Management'
    }
    return render(request, 'admin_panel/school_management.html', context)



@login_required
@require_http_methods(["GET", "POST"])
def school_create(request):
    """Create new school"""
    if not hasattr(request.user, 'is_admin') or not request.user.is_admin_or_officer:
        messages.error(request, 'Access denied - Admin privileges required')
        return redirect('authentication:login')
    
    if request.method == 'POST':
        try:
            from apps.students.models import School
            
            name = request.POST.get('name', '').strip()
            code = request.POST.get('code', '').strip()
            description = request.POST.get('description', '').strip()
            
            if not name:
                messages.error(request, 'School name is required')
                return render(request, 'admin_panel/school_form.html', {
                    'form_data': request.POST
                })
            
            # Check for duplicate names
            if School.objects.filter(name__iexact=name).exists():
                messages.error(request, 'A school with this name already exists')
                return render(request, 'admin_panel/school_form.html', {
                    'form_data': request.POST
                })

            # Check for duplicate codes if code is provided
            if code and School.objects.filter(code__iexact=code).exists():
                messages.error(request, 'A school with this code already exists')
                return render(request, 'admin_panel/school_form.html', {
                    'form_data': request.POST
                })
            
            school = School.objects.create(
                name=name,
                code=code if code else None,
                description=description if description else None
            )
            
            # Create audit log
            AuditLog.objects.create(
                user=request.user,
                action='school_create',
                description=f'Created school: {school.name}',
                target_model='School',
                target_id=str(school.id)
            )
            
            messages.success(request, f'School "{school.name}" created successfully')
            return redirect('admin_panel:school_management')
            
        except Exception as e:
            messages.error(request, f'Error creating school: {str(e)}')
    
    context = {
        'action': 'Create',
        'page_title': 'Create School'
    }
    return render(request, 'admin_panel/school_form.html', context)



@login_required
@require_http_methods(["GET", "POST"])
def school_edit(request, school_id):
    """Edit existing school"""
    if not hasattr(request.user, 'is_admin') or not request.user.is_admin_or_officer:
        messages.error(request, 'Access denied - Admin privileges required')
        return redirect('authentication:login')
    
    from apps.students.models import School
    
    school = get_object_or_404(School, id=school_id)
    
    if request.method == 'POST':
        try:
            name = request.POST.get('name', '').strip()
            code = request.POST.get('code', '').strip()
            description = request.POST.get('description', '').strip()
            
            if not name:
                messages.error(request, 'School name is required')
                return render(request, 'admin_panel/school_form.html', {
                    'school': school,
                    'form_data': request.POST
                })
            
            # Check for duplicate names (excluding current school)
            if School.objects.filter(name__iexact=name).exclude(id=school.id).exists():
                messages.error(request, 'A school with this name already exists')
                return render(request, 'admin_panel/school_form.html', {
                    'school': school,
                    'form_data': request.POST
                })

            # Check for duplicate codes if code is provided (excluding current school)
            if code and School.objects.filter(code__iexact=code).exclude(id=school.id).exists():
                messages.error(request, 'A school with this code already exists')
                return render(request, 'admin_panel/school_form.html', {
                    'school': school,
                    'form_data': request.POST
                })
            
            old_name = school.name
            school.name = name
            school.code = code if code else None
            school.description = description if description else None
            school.save()
            
            # Create audit log
            AuditLog.objects.create(
                user=request.user,
                action='school_update',
                description=f'Updated school: {old_name} → {school.name}',
                target_model='School',
                target_id=str(school.id)
            )
            
            messages.success(request, f'School "{school.name}" updated successfully')
            return redirect('admin_panel:school_management')
            
        except Exception as e:
            messages.error(request, f'Error updating school: {str(e)}')
    
    context = {
        'school': school,
        'action': 'Edit',
        'page_title': 'Edit School'
    }
    return render(request, 'admin_panel/school_form.html', context)



@login_required
@require_http_methods(["POST"])
def school_delete(request, school_id):
    """Delete school"""
    if not hasattr(request.user, 'is_admin') or not request.user.is_admin_or_officer:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    try:
        from apps.students.models import School
        
        school = get_object_or_404(School, id=school_id)
        
        # Count departments that will be cascade deleted
        department_count = school.departments.count()
        school_name = school.name
        
        # Delete school (departments will be cascade deleted automatically)
        school.delete()
        
        # Create audit log
        deletion_message = f'Deleted school: {school_name}'
        if department_count > 0:
            deletion_message += f' and {department_count} associated departments'
            
        AuditLog.objects.create(
            user=request.user,
            action='school_delete',
            description=deletion_message,
            target_model='School',
            target_id=str(school_id)
        )
        
        success_message = f'School "{school_name}" deleted successfully'
        if department_count > 0:
            success_message += f' along with {department_count} associated departments'
            
        return JsonResponse({'success': True, 'message': success_message})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)



@login_required
@require_http_methods(["POST"])
def bulk_activate_schools(request):
    """Bulk activate schools"""
    if not hasattr(request.user, 'is_admin') or not request.user.is_admin_or_officer:
        return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)
    
    try:
        import json
        from apps.students.models import School
        
        data = json.loads(request.body)
        school_ids = data.get('school_ids', [])
        
        # Convert string IDs to integers
        try:
            school_ids = [int(id) for id in school_ids]
        except (ValueError, TypeError):
            return JsonResponse({'success': False, 'error': 'Invalid school IDs'}, status=400)
        
        if not school_ids:
            return JsonResponse({'success': False, 'error': 'No schools selected'}, status=400)
        
        schools = School.objects.filter(id__in=school_ids)
        activated_count = schools.filter(is_active=False).count()
        
        # Activate schools
        result = schools.update(is_active=True)
        
        # Also reactivate all departments in these schools
        from apps.students.models import Department
        departments_updated = Department.objects.filter(school__in=school_ids).update(is_active=True)
        
        # Create audit log
        AuditLog.objects.create(
            user=request.user,
            action='bulk_activate_schools',
            description=f'Bulk activated {activated_count} schools and {departments_updated} associated departments',
            target_model='School'
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Successfully activated {activated_count} school(s)',
            'activated_count': activated_count
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)



@login_required
@require_http_methods(["POST"])
def bulk_deactivate_schools(request):
    """Bulk deactivate schools"""
    if not hasattr(request.user, 'is_admin') or not request.user.is_admin_or_officer:
        return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)
    
    try:
        import json
        from apps.students.models import School
        
        data = json.loads(request.body)
        school_ids = data.get('school_ids', [])
        
        # Convert string IDs to integers
        try:
            school_ids = [int(id) for id in school_ids]
        except (ValueError, TypeError):
            return JsonResponse({'success': False, 'error': 'Invalid school IDs'}, status=400)
        
        if not school_ids:
            return JsonResponse({'success': False, 'error': 'No schools selected'}, status=400)
        
        schools = School.objects.filter(id__in=school_ids)
        deactivated_count = schools.filter(is_active=True).count()
        
        # Deactivate schools
        result = schools.update(is_active=False)
        
        # Also deactivate all departments in these schools
        from apps.students.models import Department
        departments_updated = Department.objects.filter(school__in=school_ids).update(is_active=False)
        
        # Create audit log
        AuditLog.objects.create(
            user=request.user,
            action='bulk_deactivate_schools',
            description=f'Bulk deactivated {deactivated_count} schools and {departments_updated} associated departments',
            target_model='School'
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Successfully deactivated {deactivated_count} school(s)',
            'deactivated_count': deactivated_count
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)



@login_required
@require_http_methods(["POST"])
def bulk_delete_schools(request):
    """Bulk delete schools"""
    if not hasattr(request.user, 'is_admin') or not request.user.is_admin_or_officer:
        return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)
    
    try:
        import json
        from apps.students.models import School
        
        data = json.loads(request.body)
        school_ids = data.get('school_ids', [])
        
        if not school_ids:
            return JsonResponse({'success': False, 'error': 'No schools selected'}, status=400)
        
        schools = School.objects.filter(id__in=school_ids)
        
        # Count total departments that will be cascade deleted
        total_departments = sum(school.departments.count() for school in schools)
        
        deleted_count = schools.count()
        school_names = list(schools.values_list('name', flat=True))
        
        # Delete schools (departments will be cascade deleted automatically)
        schools.delete()
        
        # Create audit log
        deletion_message = f'Bulk deleted {deleted_count} schools: {", ".join(school_names)}'
        if total_departments > 0:
            deletion_message += f' and {total_departments} associated departments'
            
        AuditLog.objects.create(
            user=request.user,
            action='bulk_delete_schools',
            description=deletion_message,
            target_model='School'
        )
        
        success_message = f'Successfully deleted {deleted_count} school(s)'
        if total_departments > 0:
            success_message += f' and {total_departments} associated departments'
        
        return JsonResponse({
            'success': True,
            'message': success_message,
            'deleted_count': deleted_count,
            'deleted_departments': total_departments
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

