from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q
from django.utils import timezone
from datetime import datetime, timedelta

from apps.grievances.models import Grievance, Category
from apps.students.models import StudentProfile


@login_required
def admin_dashboard_simple(request):
    """Simple admin dashboard view for testing"""
    if not hasattr(request.user, 'is_admin') or not request.user.is_admin:
        messages.error(request, 'Access denied - Admin privileges required')
        return redirect('authentication:login')
    
    try:
        # Get basic statistics with error handling
        total_grievances = Grievance.objects.count()
        pending_grievances = Grievance.objects.filter(status='pending').count()
        resolved_grievances = Grievance.objects.filter(status='resolved').count()
        rejected_grievances = Grievance.objects.filter(status='rejected').count()
        
        # Get recent grievances with proper error handling
        recent_grievances = []
        try:
            recent_grievances = Grievance.objects.select_related('student', 'category').order_by('-submitted_at')[:5]
        except Exception as e:
            print(f"Error getting recent grievances: {e}")
        
        # Get category statistics with error handling
        category_stats = []
        try:
            category_stats = Category.objects.annotate(
                count=Count('grievances')
            ).order_by('-count')[:5]
        except Exception as e:
            print(f"Error getting category stats: {e}")
        
        # Simple monthly stats
        monthly_stats = [
            {'month': 'January 2025', 'count': 10},
            {'month': 'February 2025', 'count': 15},
            {'month': 'March 2025', 'count': 8},
            {'month': 'April 2025', 'count': 12},
            {'month': 'May 2025', 'count': 18},
            {'month': 'June 2025', 'count': 14},
        ]
        
        context = {
            'total_grievances': total_grievances,
            'pending_grievances': pending_grievances,
            'resolved_grievances': resolved_grievances,
            'rejected_grievances': rejected_grievances,
            'recent_grievances': recent_grievances,
            'category_stats': category_stats,
            'monthly_stats': monthly_stats,
        }
        
        return render(request, 'admin_panel/dashboard.html', context)
        
    except Exception as e:
        print(f"Error in admin dashboard: {e}")
        messages.error(request, f'Error loading dashboard: {str(e)}')
        return render(request, 'admin_panel/dashboard.html', {
            'total_grievances': 0,
            'pending_grievances': 0,
            'resolved_grievances': 0,
            'rejected_grievances': 0,
            'recent_grievances': [],
            'category_stats': [],
            'monthly_stats': [],
        })
