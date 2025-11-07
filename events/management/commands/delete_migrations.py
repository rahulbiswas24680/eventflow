import os
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'Delete all migration files except initial ones for specific apps'

    TARGET_APPS = [
        'events',
        'payments', 
        'qr_codes',
        'analytics',
        'communication',
        'user_profiles',
        'support',
        'registration'
    ]

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting'
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        
        apps_to_process = []
        for app in settings.INSTALLED_APPS:
            app_name = app.split('.')[-1]
            if app_name in self.TARGET_APPS:
                apps_to_process.append(app_name)
        
        if not apps_to_process:
            self.stdout.write(self.style.WARNING('No target apps found in INSTALLED_APPS'))
            return
        
        self.stdout.write(f'Target apps: {", ".join(apps_to_process)}')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No files will be deleted'))
        
        confirmed = input(f"\n{'DRY RUN: Would delete' if dry_run else 'Do you want to delete'} all migrations except initial ones? (y/N): ")
        if confirmed.lower() != 'y':
            self.stdout.write(self.style.WARNING('Operation cancelled.'))
            return
        
        deleted_count = 0
        
        for app_name in apps_to_process:
            migrations_path = os.path.join(settings.BASE_DIR, app_name, 'migrations')
            
            if os.path.exists(migrations_path):
                migration_files = os.listdir(migrations_path)
                files_to_delete = [f for f in migration_files if f != '__init__.py' and f != '__pycache__']
                
                if files_to_delete:
                    self.stdout.write(f'\n{app_name}:')
                    for file in files_to_delete:
                        file_path = os.path.join(migrations_path, file)
                        if dry_run:
                            self.stdout.write(f'  Would delete: {file_path}')
                        else:
                            os.remove(file_path)
                            deleted_count += 1
                            self.stdout.write(f'  Deleted: {file_path}')
                else:
                    self.stdout.write(f'{app_name}: No files to delete')
            else:
                self.stdout.write(self.style.WARNING(f'{app_name}: Migrations directory not found'))
        
        if not dry_run:
            self.stdout.write(self.style.SUCCESS(f'Successfully processed {deleted_count} migration files'))
        else:
            self.stdout.write(self.style.WARNING(f'DRY RUN: Would process {deleted_count} files'))
