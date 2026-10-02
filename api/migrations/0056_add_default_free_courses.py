# Generated migration to add default free courses

from django.db import migrations

def create_default_free_courses(apps, schema_editor):
    Course = apps.get_model('api', 'Course')
    Subject = apps.get_model('api', 'Subject')
    
    # Get or create subjects
    programming, _ = Subject.objects.get_or_create(
        name="Dasturlash",
        defaults={
            'slug': 'dasturlash',
            'description': 'Dasturlash asoslari',
            'is_active': True
        }
    )
    
    design, _ = Subject.objects.get_or_create(
        name="Dizayn",
        defaults={
            'slug': 'dizayn',
            'description': 'Grafik dizayn',
            'is_active': True
        }
    )
    
    marketing, _ = Subject.objects.get_or_create(
        name="Marketing",
        defaults={
            'slug': 'marketing',
            'description': 'SMM va Marketing',
            'is_active': True
        }
    )
    
    # Create default free courses if they don't exist
    courses_data = [
        {
            'title': 'Dasturlashga kirish',
            'description': 'Dasturlash asoslarini o\'rganing. Python, JavaScript va boshqa tillar bilan tanishing.',
            'subject': programming,
            'level': 'BEGINNER',
            'duration': '45',
            'price': 0,
            'is_active': True,
            'status': 'APPROVED',
            'lessons_count': 10,
        },
        {
            'title': 'Grafik Dizayn asoslari',
            'description': 'Grafik dizayn asoslarini o\'rganing. Adobe Photoshop, Illustrator va boshqa dasturlar.',
            'subject': design,
            'level': 'BEGINNER',
            'duration': '30',
            'price': 0,
            'is_active': True,
            'status': 'APPROVED',
            'lessons_count': 8,
        },
        {
            'title': 'SMM nima?',
            'description': 'Ijtimoiy tarmoqlarda marketing asoslarini o\'rganing. Instagram, Facebook, TikTok strategiyalari.',
            'subject': marketing,
            'level': 'BEGINNER',
            'duration': '20',
            'price': 0,
            'is_active': True,
            'status': 'APPROVED',
            'lessons_count': 5,
        },
    ]
    
    for course_data in courses_data:
        Course.objects.get_or_create(
            title=course_data['title'],
            defaults=course_data
        )

def reverse_func(apps, schema_editor):
    # Optional: remove the default courses
    Course = apps.get_model('api', 'Course')
    Course.objects.filter(
        title__in=[
            'Dasturlashga kirish',
            'Grafik Dizayn asoslari',
            'SMM nima?'
        ]
    ).delete()

class Migration(migrations.Migration):

    dependencies = [
        ('api', '0055_freecourselessoncard'),
    ]

    operations = [
        migrations.RunPython(create_default_free_courses, reverse_func),
    ]
