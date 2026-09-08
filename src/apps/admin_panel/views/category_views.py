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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def manage_categories(request):
    """Manage categories API"""
    if not request.user.is_admin_or_officer:
        return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)
    
    categories = Category.objects.all()
    
    return Response([
        {
            'id': c.id,
            'name': c.name,
            'description': c.description,
            'category_type': c.category_type,
            'is_active': c.is_active,
        }
        for c in categories
    ])



@login_required
def manage_categories_view(request):
    """View for managing grievance categories"""
    if not request.user.is_admin_or_officer:
        messages.error(request, 'Access denied')
        return redirect('authentication:login')
    
    categories = Category.objects.all().order_by('category_type', 'name')
    
    # Calculate counts
    academic_count = categories.filter(category_type='academic').count()
    non_academic_count = categories.filter(category_type='non_academic').count()
    
    if request.method == 'POST':
        name = request.POST.get('name')
        category_type = request.POST.get('category_type')
        
        if name and category_type:
            Category.objects.create(
                name=name,
                description=f"{name} category",  # Provide a default description
                category_type=category_type,
                is_active=True
            )
            messages.success(request, 'Category created successfully')
            return redirect('admin_panel:manage_categories')
        else:
            messages.error(request, 'Category name and type are required')
    
    context = {
        'categories': categories,
        'academic_count': academic_count,
        'non_academic_count': non_academic_count,
    }
    
    return render(request, 'admin_panel/manage_categories.html', context)



@login_required
def toggle_category_status(request, category_id):
    """Toggle category active status"""
    if not request.user.is_admin_or_officer:
        return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)
    
    try:
        category = get_object_or_404(Category, id=category_id)
        category.is_active = not category.is_active
        category.save()
        
        return JsonResponse({
            'success': True, 
            'is_active': category.is_active,
            'status': 'activated' if category.is_active else 'deactivated'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)



@login_required
def update_category(request):
    """Update category details"""
    if not request.user.is_admin_or_officer:
        return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        import json
        data = json.loads(request.body)
        category_id = data.get('category_id')
        name = data.get('name', '').strip()
        category_type = data.get('category_type')
        
        if not all([category_id, name, category_type]):
            return JsonResponse({'success': False, 'error': 'Category ID, name, and type are required'}, status=400)
        
        if category_type not in ['academic', 'non_academic']:
            return JsonResponse({'success': False, 'error': 'Invalid category type'}, status=400)
        
        category = get_object_or_404(Category, id=category_id)
        
        # Check if name already exists for another category
        if Category.objects.filter(name=name).exclude(id=category_id).exists():
            return JsonResponse({'success': False, 'error': 'Category with this name already exists'}, status=400)
        
        category.name = name
        category.category_type = category_type
        category.description = f"{name} category"  # Auto-generate description
        category.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Category updated successfully'
        })
    
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)



@login_required
def delete_category(request):
    """Delete a single category"""
    if not request.user.is_admin_or_officer:
        return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        import json
        data = json.loads(request.body)
        category_id = data.get('category_id')
        
        if not category_id:
            return JsonResponse({'success': False, 'error': 'Category ID is required'}, status=400)
        
        category = get_object_or_404(Category, id=category_id)
        
        # Check if category has grievances
        if category.grievances.exists():
            return JsonResponse({
                'success': False, 
                'error': f'Cannot delete category "{category.name}" as it has associated grievances'
            }, status=400)
        
        category.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Category deleted successfully'
        })
    
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)



@login_required
def bulk_delete_categories(request):
    """Bulk delete categories"""
    if not request.user.is_admin_or_officer:
        return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        import json
        data = json.loads(request.body)
        category_ids = data.get('category_ids', [])
        
        if not category_ids:
            return JsonResponse({'success': False, 'error': 'No categories selected'}, status=400)
        
        # Get categories and check for associated grievances
        categories = Category.objects.filter(id__in=category_ids)
        categories_with_grievances = []
        
        for category in categories:
            if category.grievances.exists():
                categories_with_grievances.append(category.name)
        
        if categories_with_grievances:
            return JsonResponse({
                'success': False,
                'error': f'Cannot delete categories with associated grievances: {", ".join(categories_with_grievances)}'
            }, status=400)
        
        deleted_count = categories.count()
        categories.delete()
        
        return JsonResponse({
            'success': True,
            'deleted_count': deleted_count,
            'message': f'Successfully deleted {deleted_count} categories'
        })
    
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)



@login_required
def bulk_update_category_status(request):
    """Bulk activate/deactivate categories"""
    if not request.user.is_admin_or_officer:
        return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        import json
        data = json.loads(request.body)
        category_ids = data.get('category_ids', [])
        is_active = data.get('is_active', True)
        
        if not category_ids:
            return JsonResponse({'success': False, 'error': 'No categories selected'}, status=400)
        
        updated_count = Category.objects.filter(id__in=category_ids).update(is_active=is_active)
        
        return JsonResponse({
            'success': True,
            'updated_count': updated_count,
            'message': f'Successfully {"activated" if is_active else "deactivated"} {updated_count} categories'
        })
    
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)



@login_required
def category_assignment_detail(request, category_id):
    """Detailed view for managing assignments for a specific category"""
    if not request.user.role in ['admin', 'superadmin']:
        messages.error(request, 'Access denied - Admin privileges required')
        return redirect('authentication:login')
    
    category = get_object_or_404(Category, id=category_id, is_active=True)
    assignments = CategoryAssignment.objects.filter(
        category=category, 
        is_active=True
    ).select_related('assigned_admin__user').order_by('-priority_level', 'department')
    
    # Get available admins for assignment
    available_admins = AdminProfile.objects.filter(
        role_level__in=['officer', 'dept_admin', 'superadmin']
    ).select_related('user')
    
    # Get departments that need assignment
    from apps.students.models import Department
    departments = Department.objects.all().order_by('name')
    
    # Get assignment statistics for this category
    total_grievances = Grievance.objects.filter(category=category).count()
    auto_assigned = Grievance.objects.filter(
        category=category,
        assigned_to__isnull=False
    ).count()
    unassigned = total_grievances - auto_assigned
    
    context = {
        'category': category,
        'assignments': assignments,
        'available_admins': available_admins,
        'departments': departments,
        'total_grievances': total_grievances,
        'auto_assigned': auto_assigned,
        'unassigned': unassigned,
    }
    
    return render(request, 'admin_panel/category_assignment_detail.html', context)



@login_required
@require_http_methods(["POST"])
def create_category_assignment(request):
    """Create a new category assignment"""
    if not request.user.role in ['admin', 'superadmin']:
        return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)
    
    try:
        data = json.loads(request.body)
        
        category_id = data.get('category_id')
        admin_id = data.get('admin_id')
        department = data.get('department', '').strip()
        school = data.get('school', '').strip()
        priority_level = int(data.get('priority_level', 1))
        keywords = data.get('keywords', '').strip()
        
        # Validate required fields
        if not category_id or not admin_id or not department:
            return JsonResponse({'success': False, 'error': 'Category, admin, and department are required'})
        
        category = get_object_or_404(Category, id=category_id, is_active=True)
        admin = get_object_or_404(AdminProfile, id=admin_id)
        
        # Check for existing assignment
        existing = CategoryAssignment.objects.filter(
            category=category,
            department__iexact=department,
            assigned_admin=admin
        ).first()
        
        if existing:
            if existing.is_active:
                return JsonResponse({'success': False, 'error': 'This assignment already exists'})
            else:
                # Reactivate existing assignment
                existing.is_active = True
                existing.priority_level = priority_level
                existing.auto_assign_keywords = keywords
                existing.school = school
                existing.save()
                assignment = existing
        else:
            # Create new assignment
            assignment = CategoryAssignment.objects.create(
                category=category,
                assigned_admin=admin,
                department=department,
                school=school,
                priority_level=priority_level,
                auto_assign_keywords=keywords,
                created_by=request.user
            )
        
        # Create audit log
        AuditLog.objects.create(
            user=request.user,
            action='create',
            target_model='CategoryAssignment',
            target_id=str(assignment.id),
            description=f"Created assignment: {category.name} → {admin} for {department}",
            ip_address=request.META.get('REMOTE_ADDR', ''),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:255]
        )
        
        return JsonResponse({
            'success': True,
            'assignment': {
                'id': str(assignment.id),
                'admin_name': assignment.assigned_admin.user.get_full_name(),
                'department': assignment.department,
                'school': assignment.school,
                'priority_level': assignment.priority_level,
                'keywords': assignment.auto_assign_keywords or '',
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})



@login_required
@require_http_methods(["POST"])
def update_category_assignment(request, assignment_id):
    """Update an existing category assignment"""
    if not request.user.role in ['admin', 'superadmin']:
        return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)
    
    try:
        assignment = get_object_or_404(CategoryAssignment, id=assignment_id)
        data = json.loads(request.body)
        
        # Update fields
        assignment.priority_level = int(data.get('priority_level', assignment.priority_level))
        assignment.auto_assign_keywords = data.get('keywords', assignment.auto_assign_keywords)
        assignment.school = data.get('school', assignment.school)
        assignment.is_active = data.get('is_active', assignment.is_active)
        assignment.save()
        
        # Create audit log
        AuditLog.objects.create(
            user=request.user,
            action='update',
            target_model='CategoryAssignment',
            target_id=str(assignment.id),
            description=f"Updated assignment: {assignment.category.name} → {assignment.assigned_admin}",
            ip_address=request.META.get('REMOTE_ADDR', ''),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:255]
        )
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})



@login_required
@require_http_methods(["POST"])
def delete_category_assignment(request, assignment_id):
    """Delete a category assignment"""
    if not request.user.role in ['admin', 'superadmin']:
        return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)
    
    try:
        assignment = get_object_or_404(CategoryAssignment, id=assignment_id)
        
        # Soft delete by setting is_active to False
        assignment.is_active = False
        assignment.save()
        
        # Create audit log
        AuditLog.objects.create(
            user=request.user,
            action='delete',
            target_model='CategoryAssignment',
            target_id=str(assignment.id),
            description=f"Deleted assignment: {assignment.category.name} → {assignment.assigned_admin}",
            ip_address=request.META.get('REMOTE_ADDR', ''),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:255]
        )
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})



@login_required
@require_http_methods(["POST"])
def test_auto_assignment(request):
    """Test auto-assignment for unassigned grievances"""
    if not request.user.role in ['admin', 'superadmin']:
        return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)
    
    try:
        # Get unassigned grievances
        unassigned_grievances = Grievance.objects.filter(
            assigned_to__isnull=True,
            status='pending'
        ).select_related('category', 'student')
        
        results = []
        assigned_count = 0
        
        for grievance in unassigned_grievances[:20]:  # Test first 20
            assigned_admin, reason = grievance.auto_assign()
            if assigned_admin:
                assigned_count += 1
                results.append({
                    'grievance_id': grievance.grievance_id,
                    'title': grievance.title,
                    'assigned_to': assigned_admin.user.get_full_name(),
                    'reason': reason
                })
            else:
                results.append({
                    'grievance_id': grievance.grievance_id,
                    'title': grievance.title,
                    'assigned_to': None,
                    'reason': reason
                })
        
        # Create audit log
        AuditLog.objects.create(
            user=request.user,
            action='update',
            target_model='Grievance',
            target_id='bulk',
            description=f"Ran auto-assignment test: {assigned_count}/{len(results)} grievances assigned",
            ip_address=request.META.get('REMOTE_ADDR', ''),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:255]
        )
        
        return JsonResponse({
            'success': True,
            'assigned_count': assigned_count,
            'total_tested': len(results),
            'results': results[:10]  # Return first 10 results
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})



@login_required
def category_management(request):
    """Category management view - Superadmin only"""
    if not can_manage_categories(request.user):
        messages.error(request, 'Access denied - Superadmin privileges required for category management')
        return redirect('admin_panel:dashboard')
    
    # Get search and filter parameters
    search = request.GET.get('search', '')
    category_type = request.GET.get('type', '')
    status_filter = request.GET.get('status', '')
    
    # Build queryset
    categories = Category.objects.all()
    
    if search:
        categories = categories.filter(name__icontains=search)
    
    if category_type:
        categories = categories.filter(category_type=category_type)
        
    if status_filter:
        categories = categories.filter(is_active=(status_filter == 'active'))
    
    categories = categories.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(categories, 10)
    page_number = request.GET.get('page')
    categories = paginator.get_page(page_number)
    
    # Process keywords for each category (after pagination)
    for category in categories:
        if hasattr(category, 'keywords') and category.keywords:
            category.keyword_list = [kw.strip() for kw in category.keywords.split(',') if kw.strip()]
        else:
            category.keyword_list = []
    
    context = {
        'categories': categories,
        'search': search,
        'category_type': category_type,
        'status_filter': status_filter,
        'category_types': Category.CATEGORY_TYPES,
        'page_title': 'Category Management'
    }
    return render(request, 'admin_panel/category_management.html', context)



@login_required 
@require_http_methods(["GET", "POST"])
def category_create(request):
    """Create new category"""
    if not hasattr(request.user, 'is_admin') or not request.user.is_admin_or_officer:
        messages.error(request, 'Access denied - Admin privileges required')
        return redirect('authentication:login')
    
    if request.method == 'POST':
        try:
            name = request.POST.get('name', '').strip()
            category_type = request.POST.get('category_type')
            keywords = request.POST.get('keywords', '').strip()
            is_active = request.POST.get('is_active') == 'on'
            auto_assign_enabled = request.POST.get('auto_assign_enabled') == 'on'
            
            if not name or not category_type:
                messages.error(request, 'Name and category type are required')
                return render(request, 'admin_panel/category_form.html', {
                    'category_types': Category.CATEGORY_TYPES,
                    'form_data': request.POST
                })
            
            # Check for duplicate names
            if Category.objects.filter(name__iexact=name).exists():
                messages.error(request, 'A category with this name already exists')
                return render(request, 'admin_panel/category_form.html', {
                    'category_types': Category.CATEGORY_TYPES,
                    'form_data': request.POST
                })
            
            category = Category.objects.create(
                name=name,
                description=f"{name} category",  # Auto-generate description
                category_type=category_type,
                keywords=keywords,
                is_active=is_active,
                auto_assign_enabled=auto_assign_enabled
            )
            
            # Create audit log
            AuditLog.objects.create(
                user=request.user,
                action='category_create',
                description=f'Created category: {category.name}',
                target_model='Category',
                target_id=str(category.id)
            )
            
            messages.success(request, f'Category "{category.name}" created successfully')
            return redirect('admin_panel:category_management')
            
        except Exception as e:
            messages.error(request, f'Error creating category: {str(e)}')
    
    context = {
        'category_types': Category.CATEGORY_TYPES,
        'action': 'Create',
        'page_title': 'Create Category'
    }
    return render(request, 'admin_panel/category_form.html', context)



@login_required
@require_http_methods(["GET", "POST"])
def category_edit(request, category_id):
    """Edit existing category"""
    if not hasattr(request.user, 'is_admin') or not request.user.is_admin_or_officer:
        messages.error(request, 'Access denied - Admin privileges required')
        return redirect('authentication:login')
    
    category = get_object_or_404(Category, id=category_id)
    
    if request.method == 'POST':
        try:
            name = request.POST.get('name', '').strip()
            category_type = request.POST.get('category_type')
            keywords = request.POST.get('keywords', '').strip()
            is_active = request.POST.get('is_active') == 'on'
            auto_assign_enabled = request.POST.get('auto_assign_enabled') == 'on'
            
            if not name or not category_type:
                messages.error(request, 'Name and category type are required')
                return render(request, 'admin_panel/category_form.html', {
                    'category': category,
                    'category_types': Category.CATEGORY_TYPES,
                    'form_data': request.POST
                })
            
            # Check for duplicate names (excluding current category)
            if Category.objects.filter(name__iexact=name).exclude(id=category.id).exists():
                messages.error(request, 'A category with this name already exists')
                return render(request, 'admin_panel/category_form.html', {
                    'category': category,
                    'category_types': Category.CATEGORY_TYPES,
                    'form_data': request.POST
                })
            
            # Store old values for audit
            old_name = category.name
            
            # Update category
            category.name = name
            category.description = f"{name} category"  # Auto-generate description
            category.category_type = category_type
            category.keywords = keywords
            category.is_active = is_active
            category.auto_assign_enabled = auto_assign_enabled
            category.save()
            
            # Create audit log
            AuditLog.objects.create(
                user=request.user,
                action='category_update',
                description=f'Updated category: {old_name} → {category.name}',
                target_model='Category',
                target_id=str(category.id)
            )
            
            messages.success(request, f'Category "{category.name}" updated successfully')
            return redirect('admin_panel:category_management')
            
        except Exception as e:
            messages.error(request, f'Error updating category: {str(e)}')
    
    context = {
        'category': category,
        'category_types': Category.CATEGORY_TYPES,
        'action': 'Edit',
        'page_title': 'Edit Category'
    }
    return render(request, 'admin_panel/category_form.html', context)



@login_required
@require_http_methods(["POST"])
def category_delete(request, category_id):
    """Delete category"""
    if not hasattr(request.user, 'is_admin') or not request.user.is_admin_or_officer:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    try:
        category = get_object_or_404(Category, id=category_id)
        
        # Check if category has grievances
        grievance_count = Grievance.objects.filter(category=category).count()
        if grievance_count > 0:
            return JsonResponse({
                'error': f'Cannot delete category. It has {grievance_count} associated grievances.'
            }, status=400)
        
        category_name = category.name
        category.delete()
        
        # Create audit log
        AuditLog.objects.create(
            user=request.user,
            action='category_delete',
            description=f'Deleted category: {category_name}',
            target_model='Category',
            target_id=str(category_id)
        )
        
        return JsonResponse({'success': True, 'message': f'Category "{category_name}" deleted successfully'})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

