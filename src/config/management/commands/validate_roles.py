"""
Management command to validate and fix role-related issues
"""
from django.core.management.base import BaseCommand
from apps.authentication.role_validator import RoleValidator


class Command(BaseCommand):
    help = 'Validate and fix role-related issues in the system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Fix role inconsistencies automatically',
        )
        parser.add_argument(
            '--check-only',
            action='store_true', 
            help='Only check for issues without fixing',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🔍 Validating role-based system integrity...')
        )

        # Validate system integrity
        issues = RoleValidator.validate_system_integrity()
        
        if issues:
            self.stdout.write(
                self.style.WARNING(f'⚠️  Found {len(issues)} issues:')
            )
            for issue in issues:
                self.stdout.write(f'  - {issue}')
        else:
            self.stdout.write(
                self.style.SUCCESS('✅ No role integrity issues found!')
            )

        # Fix issues if requested
        if options['fix'] and issues:
            self.stdout.write(
                self.style.SUCCESS('\n🔧 Attempting to fix role inconsistencies...')
            )
            
            fixed_issues = RoleValidator.fix_role_inconsistencies()
            
            if fixed_issues:
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Fixed {len(fixed_issues)} issues:')
                )
                for fix in fixed_issues:
                    self.stdout.write(f'  + {fix}')
            else:
                self.stdout.write(
                    self.style.WARNING('⚠️  No issues could be automatically fixed.')
                )

        elif options['check_only']:
            self.stdout.write(
                self.style.SUCCESS('\n✅ Check completed. Use --fix to automatically fix issues.')
            )

        # Re-validate after fixes
        if options['fix'] and issues:
            self.stdout.write(
                self.style.SUCCESS('\n🔍 Re-validating system after fixes...')
            )
            new_issues = RoleValidator.validate_system_integrity()
            
            if new_issues:
                self.stdout.write(
                    self.style.WARNING(f'⚠️  {len(new_issues)} issues still remain:')
                )
                for issue in new_issues:
                    self.stdout.write(f'  - {issue}')
            else:
                self.stdout.write(
                    self.style.SUCCESS('✅ All role integrity issues have been resolved!')
                )

        # Show role summary
        self.show_role_summary()

    def show_role_summary(self):
        """Show summary of roles in the system"""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS('📊 ROLE DISTRIBUTION SUMMARY'))
        self.stdout.write('='*50)
        
        role_counts = {}
        for choice in User.ROLE_CHOICES:
            role_code = choice[0]
            role_name = choice[1]
            count = User.objects.filter(role=role_code).count()
            role_counts[role_code] = {'name': role_name, 'count': count}
        
        for role_code, info in role_counts.items():
            icon = {'superadmin': '🔴', 'admin': '🟠', 'officer': '🔵', 'student': '🟢'}.get(role_code, '⚪')
            self.stdout.write(f"{icon} {info['name']}: {info['count']} users")
        
        total_users = User.objects.count()
        self.stdout.write(f"\n📈 Total Users: {total_users}")
        self.stdout.write('='*50)
