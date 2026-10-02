"""
Fix script to migrate V2 content to the existing V1 Python Course
Run: python manage.py shell < fix_python_course_v2.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from api.models import Course, Module, Lesson

print("🛠 Fix script started...")

try:
    # 1. Get the courses
    old_course = Course.objects.filter(title='Python Dasturlash').first() # The one user is looking at
    new_course = Course.objects.filter(title='Python Dasturlash Asoslari').first() # The one we seeded

    if not old_course:
        print("❌ Old course 'Python Dasturlash' not found!")
        exit(1)

    if not new_course:
        print("❌ New course 'Python Dasturlash Asoslari' not found!")
        exit(1)

    print(f"🔄 Migrating content from '{new_course.title}' (ID: {new_course.id}) to '{old_course.title}' (ID: {old_course.id})...")

    # 2. Delete old lessons from old_course (the flat ones)
    old_lessons_count = old_course.lessons.filter(module__isnull=True).count()
    old_course.lessons.filter(module__isnull=True).delete()
    print(f"🗑 Deleted {old_lessons_count} old V1 lessons.")

    # 3. Move modules from new_course to old_course
    modules = new_course.modules.all()
    for module in modules:
        module.course = old_course
        module.save()
        
        # Also update lessons inside to point to old_course (just in case, though they link to module usually, but also have course FK)
        for lesson in module.lessons.all():
            lesson.course = old_course
            lesson.save()
            
    print(f"✅ Moved {modules.count()} modules to old course.")

    # 4. Update metadata of old_course
    old_course.description = new_course.description
    old_course.level = new_course.level
    old_course.duration = new_course.duration
    old_course.lessons_count = new_course.lessons_count
    old_course.xp_reward = new_course.xp_reward
    old_course.save()
    print("✅ Updated old course metadata.")

    # 5. Delete the empty new_course
    new_course.delete()
    print(f"🗑 Deleted temporary course '{new_course.title}'.")

    print("\n🎉 Fix complete! The user can now refresh the page.")

except Exception as e:
    print(f"❌ Error: {e}")
