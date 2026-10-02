
import os
import django
import sys

# Setup Django environment
sys.path.append('/Users/ogabek/Documents/projects/ardent olimpiada/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from api.models import Lesson, Course

def run():
    # Find Python course or First course
    course = Course.objects.filter(title__icontains="python").first()
    if not course:
        print("Python course not found, using first available course.")
        course = Course.objects.first()
        
    if not course:
        print("No courses found!")
        return

    print(f"Using Course: {course.title}")

    # Find first lesson
    lesson = Lesson.objects.filter(course=course).first()
    if not lesson:
        # Create a dummy lesson if none
        from api.models import Module
        module = Module.objects.filter(course=course).first()
        if not module:
            module = Module.objects.create(course=course, title="Introduction", order=0)
            
        lesson = Lesson.objects.create(
            course=course,
            module=module,
            title="Python Kirish",
            description="Python dasturlash tiliga kirish darsi",
            order=0,
            is_free=True
        )
        print("Created new lesson.")
    
    # Update with YouTube ID
    lesson.youtube_id = "_GjgFMGQg40"
    lesson.video_type = "YOUTUBE"
    lesson.save()
    
    print(f"Updated Lesson '{lesson.title}' (ID: {lesson.id}) with YouTube ID: {lesson.youtube_id}")

if __name__ == "__main__":
    run()
