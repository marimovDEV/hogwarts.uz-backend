"""
Seed script to populate database with a structured Python course (V2 Architecture)
Run: python manage.py shell < seed_python_v2.py
"""
import os
import django
import random

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.utils import timezone
from api.models import (
    User, Course, Lesson, Module, LessonPractice, LessonTest, 
    Question, Olympiad, LevelReward
)

print("🚀 Starting Python Course Seeding...")

# 1. Get Teacher
teacher, _ = User.objects.get_or_create(
    username='teacher_python',
    defaults={
        'email': 'python@ardent.uz',
        'first_name': 'Anvar',
        'last_name': 'Narshiyev',
        'role': 'TEACHER',
        'is_staff': True
    }
)
if _:
    teacher.set_password('teacher123')
    teacher.save()
    print("✅ Teacher created: teacher_python")

# 2. Create/Get Course
course, created = Course.objects.get_or_create(
    title='Python Dasturlash Asoslari',
    defaults={
        'description': "Python dasturlash tilini noldan professional darajagacha o'rganing. Video darslar, amaliy mashg'ulotlar va interaktiv testlar.",
        'price': 250000,
        'level': 'BEGINNER',
        'subject': 'Informatika',
        'duration': '48 soat',
        'rating': 5.0,
        'is_featured': True,
        'teacher': teacher,
        'xp_reward': 1000,
        'is_active': True,
        'lessons_count': 0 # Will update later
    }
)
if not created:
    print(f"ℹ️ Updating existing course: {course.title}")
else:
    print(f"✅ Course created: {course.title}")

# 3. Create Placeholder Olympiad for Questions (Technical Requirement)
question_bank, _ = Olympiad.objects.get_or_create(
    title='Python Question Bank',
    defaults={
        'description': 'System question bank for Python lessons',
        'subject': 'Informatika',
        'start_date': timezone.now(),
        'end_date': timezone.now(),
        'duration': 0,
        'status': 'COMPLETED',
        'is_active': False
    }
)

# 4. Content Structure
modules_data = [
    {
        "title": "1-Modul: Kirish va O'rnatish",
        "lessons": [
            {
                "title": "Python Dasturlash Tili Haqida",
                "video_url": "https://www.youtube.com/embed/_uQrJ0TkZlc", # Placeholder ID
                "duration": 600,
                "is_free": True,
                "description": "Python nima? Nega aynan Python? Ushbu darsda biz Python dasturlash tilining imkoniyatlari va kelajagi haqida gaplashamiz.",
                "practice": None,
                "test": None
            },
            {
                "title": "Ilk Dasturimiz: Hello World",
                "video_url": "https://www.youtube.com/embed/kqtD5dpn9C8",
                "duration": 900,
                "is_free": True,
                "description": "An'anaga ko'ra, har bir dasturchi faoliyatini 'Salom Dunyo' dasturini yozishdan boshlaydi.",
                "practice": {
                    "type": "CODE",
                    "text": "Ekranga 'Salom Dunyo' so'zini chiqaruvchi dastur yozing.",
                    "correct": 'print("Salom Dunyo")',
                    "test_cases": [{"input": "", "output": "Salom Dunyo"}]
                },
                "test": None
            }
        ]
    },
    {
        "title": "2-Modul: O'zgaruvchilar va Ma'lumot Turlari",
        "lessons": [
            {
                "title": "O'zgaruvchilar (Variables)",
                "video_url": "https://www.youtube.com/embed/cKzP6yiFBUs", # Mosh Hamedani Python
                "duration": 1200,
                "is_free": False,
                "description": "O'zgaruvchilar - xotiradagi qutichalar. Ularni qanday yaratish va ishlatishni o'rganamiz.",
                "practice": {
                    "type": "TEXT",
                    "text": "O'zgaruvchi nomida bo'sh joy (space) ishlatish mumkinmi? (Ha/Yo'q)",
                    "correct": "Yo'q"
                },
                "test": None
            },
            {
                "title": "String va Integer",
                "video_url": "https://www.youtube.com/embed/k9TUPpGqYTo",
                "duration": 1400,
                "is_free": False,
                "description": "Matnli va sonli ma'lumotlar bilan ishlash.",
                "practice": None,
                "test": [
                    {
                        "text": "Python-da butun sonlar uchun qaysi tur ishlatiladi?",
                        "options": ["float", "int", "str", "bool"],
                        "correct": 1
                    },
                    {
                        "text": "type('Salom') natijasi nima bo'ladi?",
                        "options": ["<class 'int'>", "<class 'str'>", "<class 'float'>", "Error"],
                        "correct": 1
                    }
                ]
            }
        ]
    },
    {
        "title": "3-Modul: Shart Operatlari va Sikllar",
        "lessons": [
            {
                "title": "If, Elif va Else",
                "video_url": "https://www.youtube.com/embed/ZCd33jY2d9w",
                "duration": 1500,
                "is_free": False,
                "description": "Dasturimizga 'aql' kiritamiz. Shartlarga qarab turli ishlarni bajarish.",
                "practice": {
                    "type": "CODE",
                    "text": "Foydalanuvchi yoshini kiritadi. Agar yosh 18 dan katta yoki teng bo'lsa 'Kirish mumkin', aks holda 'Kirish taqiqlanadi' deb chiqaring. O'zgaruvchi nomi: age",
                    "correct": "if age >= 18:\n    print('Kirish mumkin')\nelse:\n    print('Kirish taqiqlanadi')",
                    "test_cases": [{"input": "", "context": {"age": 20}, "output": "Kirish mumkin"}, {"input": "", "context": {"age": 15}, "output": "Kirish taqiqlanadi"}]
                },
                "test": None
            },
            {
                "title": "For va While Sikllari",
                "video_url": "https://www.youtube.com/embed/6iF8Xb7Z3wQ",
                "duration": 1800,
                "is_free": False,
                "description": "Takrorlanuvchi jarayonlarni avtomatlashtirish.",
                "test": [
                    {
                        "text": "range(5) qanday qiymatlarni qaytaradi?",
                        "options": ["0, 1, 2, 3, 4, 5", "1, 2, 3, 4, 5", "0, 1, 2, 3, 4", "1, 2, 3, 4"],
                        "correct": 2
                    },
                    {
                        "text": "Siklni to'xtatish uchun qaysi kalit so'z ishlatiladi?",
                        "options": ["stop", "exit", "break", "continue"],
                        "correct": 2
                    }
                ],
                "practice": None
            }
        ]
    }
]

# 5. Populate DB
total_lessons = 0

# Clear existing modules for this course to avoid duplicates if re-run
course.modules.all().delete()
course.lessons.all().delete()

for m_idx, m_data in enumerate(modules_data, 1):
    module = Module.objects.create(
        course=course,
        title=m_data['title'],
        order=m_idx
    )
    print(f"  📂 Module created: {module.title}")

    for l_idx, l_data in enumerate(m_data['lessons'], 1):
        total_lessons += 1
        lesson = Lesson.objects.create(
            course=course,
            module=module,
            title=l_data['title'],
            description=l_data['description'],
            video_url=l_data['video_url'],
            video_type='YOUTUBE',
            video_duration=l_data['duration'],
            is_free=l_data['is_free'],
            order=l_idx,
            is_published=True
        )
        print(f"    🎬 Lesson: {lesson.title}")

        # Add Practice
        if l_data.get('practice'):
            p_data = l_data['practice']
            LessonPractice.objects.create(
                lesson=lesson,
                type=p_data['type'],
                problem_text=p_data['text'],
                correct_answer=p_data['correct'],
                test_cases=p_data.get('test_cases', []),
                points=20
            )
            print("      ✏️ Practice added")

        # Add Test
        if l_data.get('test'):
            test = LessonTest.objects.create(
                lesson=lesson,
                min_pass_score=60
            )
            for q_idx, q_data in enumerate(l_data['test'], 1):
                question = Question.objects.create(
                    olympiad=question_bank,
                    text=q_data['text'],
                    options=q_data['options'],
                    correct_answer=q_data['correct'],
                    points=10,
                    order=q_idx,
                    type='MCQ'
                )
                test.questions.add(question)
            print("      ❓ Test added")

# Update course counts
course.lessons_count = total_lessons
course.save()

print(f"\n✅ Successfully seeded '{course.title}' with {course.modules.count()} modules and {total_lessons} lessons.")
