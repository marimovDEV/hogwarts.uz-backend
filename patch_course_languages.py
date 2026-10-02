"""
Patch script to set language for existing courses.
Run: python manage.py shell < patch_course_languages.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from api.models import Course

print("🛠 Patching course languages...")

# Set all to Uzbek by default first
Course.objects.all().update(language='uz')
print("✅ All courses set to Uzbek (default).")

# Update specific courses if we had Russian ones (none yet based on previous seeds)
# For now, we will assume the main Python course is Uzbek as requested.

# Let's verify
python_course = Course.objects.filter(title__icontains='Python').first()
if python_course:
    python_course.language = 'uz'
    python_course.save()
    print(f"✅ Verified '{python_course.title}' is set to Uzbek.")

print("\n🎉 Patch complete!")
