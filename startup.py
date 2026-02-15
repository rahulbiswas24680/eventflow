import django
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rsvp.settings')
django.setup()

from user_profiles.models import Role, CustomUser as User


class EventFlowDataFeed:

    def __init__(self):
        pass

    def create_roles(self):
        roles = [
            Role(name='attendee', description='Who attends events'),
            Role(name='organizer', description='Who creates and manages events')
        ]
        
        # Delete existing roles if you want a clean setup (optional)
        Role.objects.all().delete()
        
        # Create roles
        created_roles = Role.objects.bulk_create(roles)
        print(f"Created {len(created_roles)} roles: {[role.name for role in created_roles]}")
        
        return created_roles


if __name__ == "__main__":
    feed = EventFlowDataFeed()
    feed.create_roles()