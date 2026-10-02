
import os
import sys
import django
from django.conf import settings

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from api.models import User

def check_env():
    print(f"DEBUG: {settings.DEBUG}")
    print(f"DATABASES: {settings.DATABASES['default']['ENGINE']}")

def ensure_user(username, password, role):
    user, created = User.objects.get_or_create(username=username)
    if created:
        user.set_password(password)
        user.role = role
        user.email = f"{username}@test.com"
        if role == 'ADMIN':
            user.is_superuser = True
            user.is_staff = True
        user.save()
        print(f"Created user: {username} ({role})")
    else:
        # Ensure role/password is correct even if user exists
        user.set_password(password)
        user.role = role
        if role == 'ADMIN':
            user.is_superuser = True
            user.is_staff = True
        user.save()
        print(f"Verified user: {username} ({role})")

if __name__ == "__main__":
    check_env()
    ensure_user('student', 'studentpassword', 'STUDENT')
    ensure_user('teacher', 'teacherpassword', 'TEACHER')
    ensure_user('admin', 'adminpassword', 'ADMIN')
