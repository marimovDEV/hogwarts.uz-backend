"""
Seed script to populate database with sample data
Run: python manage.py shell < seed_data.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.hashers import make_password
from datetime import datetime, timedelta
from django.utils import timezone
from api.models import (
    User, Course, Lesson, Olympiad, Question, Certificate, 
    SupportTicket, TicketMessage, Module, LessonPractice, LessonTest
)

# Create Admin User
admin, created = User.objects.get_or_create(
    username='admin',
    defaults={
        'email': 'admin@olimpiada.uz',
        'password': make_password('admin123'),
        'first_name': 'Admin',
        'last_name': 'User',
        'role': 'ADMIN',
        'is_staff': True,
        'is_superuser': True,
    }
)
if created:
    print("✅ Admin user created: admin@olimpiada.uz / admin123")

# Create Sample Student
student, created = User.objects.get_or_create(
    username='student',
    defaults={
        'email': 'student@mail.uz',
        'password': make_password('student123'),
        'first_name': 'Azizbek',
        'last_name': 'Toshmatov',
        'role': 'STUDENT',
        'xp': 150,
        'level': 2,
    }
)
if created:
    print("✅ Student user created: student@mail.uz / student123")

# Create Courses
courses_data = [
    {
        'title': 'Matematika Pro',
        'description': 'Olimpiada matematikasi bo\'yicha to\'liq kurs. Algebra, geometriya, kombinatorika.',
        'price': 150000,
        'level': 'INTERMEDIATE',
        'subject': 'Matematika',
        'duration': '24 soat',
        'rating': 4.8,
        'is_featured': True,
    },
    {
        'title': 'Python Dasturlash',
        'description': 'Python dasturlash tilini noldan o\'rganing. Amaliy loyihalar bilan.',
        'price': 200000,
        'level': 'BEGINNER',
        'subject': 'Informatika',
        'duration': '36 soat',
        'rating': 4.9,
        'is_featured': True,
    },
    {
        'title': 'Fizika Olimpiada',
        'description': 'Fizika olimpiadalariga tayyorgarlik kursi. Nazariya va masalalar yechish.',
        'price': 180000,
        'level': 'ADVANCED',
        'subject': 'Fizika',
        'duration': '30 soat',
        'rating': 4.7,
    },
    {
        'title': 'Ingliz tili B2',
        'description': 'IELTS va CEFR B2 darajasiga tayyorgarlik.',
        'price': 250000,
        'level': 'INTERMEDIATE',
        'subject': 'Ingliz tili',
        'duration': '40 soat',
        'rating': 4.6,
    },
]

for course_data in courses_data:
    course, created = Course.objects.get_or_create(
        title=course_data['title'],
        defaults=course_data
    )
    if created:
        # Add some lessons
        for i in range(1, 6):
            Lesson.objects.create(
                course=course,
                title=f"{course.title} - {i}-dars",
                description=f"Bu {course.title} kursining {i}-darsi.",
                duration=f"{45 + i*5} daqiqa",
                order=i,
                is_free=(i == 1)
            )
        course.lessons_count = 5
        course.save()
        print(f"✅ Course created: {course.title}")

# Create Advanced Course (V2 Structure)
math_adv, created = Course.objects.get_or_create(
    title='Matematika: Olimpiada Master',
    defaults={
        'description': 'Advanced mathematics for international olympiads. Includes video lessons, coding practices, and rigorous tests.',
        'price': 450000,
        'level': 'ADVANCED',
        'subject': 'Matematika',
        'duration': '60 soat',
        'rating': 5.0,
        'is_featured': True,
        'xp_reward': 500
    }
)

if created:
    # 1. Create Modules
    m1 = Module.objects.create(course=math_adv, title="Algebra Asoslari", order=1)
    m2 = Module.objects.create(course=math_adv, title="Kombinatorika", order=2)

    # 2. Add Lessons to M1
    l1 = Lesson.objects.create(
        course=math_adv, module=m1, title="Ko'phadlar va ularning xossalari",
        video_url="https://www.youtube.com/watch?v=example1", video_type="YOUTUBE",
        video_duration=1200, order=1, is_free=True
    )
    
    # Add Practice to L1
    LessonPractice.objects.create(
        lesson=l1, type='TEXT', 
        problem_text="x^2 - 5x + 6 = 0 tenglamaning ildizlari yig'indisini toping.",
        correct_answer="5", points=20
    )

    l2 = Lesson.objects.create(
        course=math_adv, module=m1, title="Viyet teoremasi",
        video_url="https://www.youtube.com/watch?v=example2", video_type="YOUTUBE",
        video_duration=1500, order=2
    )

    # Add Test to L2
    test2 = LessonTest.objects.create(lesson=l2, min_pass_score=80)
    # We can link questions from the global pool or create new ones
    q1 = Question.objects.create(
        olympiad=Olympiad.objects.first(), # Hack for now since Question needs an Olympiad in models.py
        text="Viyet teoremasiga ko'ra x^2 + px + q = 0 x1*x2 nimaga teng?",
        options=['p', '-p', 'q', '-q'], correct_answer=2, points=5, order=1
    )
    test2.questions.add(q1)

    print(f"✅ Advanced Course created: {math_adv.title}")
olympiads_data = [
    {
        'title': 'Matematika Olimpiadasi 2024',
        'description': 'Respublika miqyosidagi matematika olimpiadasi.',
        'subject': 'Matematika',
        'start_date': timezone.now() + timedelta(days=7),
        'end_date': timezone.now() + timedelta(days=7, hours=3),
        'duration': 120,
        'price': 25000,
        'status': 'UPCOMING',
    },
    {
        'title': 'Informatika Challenge',
        'description': 'Dasturlash va algoritmlar bo\'yicha musobaqa.',
        'subject': 'Informatika',
        'start_date': timezone.now() + timedelta(days=14),
        'end_date': timezone.now() + timedelta(days=14, hours=2),
        'duration': 90,
        'price': 30000,
        'status': 'UPCOMING',
    },
    {
        'title': 'Fizika Kubogi',
        'description': 'Eng yaxshi fiziklar uchun qiziqarli musobaqa.',
        'subject': 'Fizika',
        'start_date': timezone.now() - timedelta(days=30),
        'end_date': timezone.now() - timedelta(days=30) + timedelta(hours=2),
        'duration': 90,
        'price': 20000,
        'status': 'COMPLETED',
    },
]

for olympiad_data in olympiads_data:
    olympiad, created = Olympiad.objects.get_or_create(
        title=olympiad_data['title'],
        defaults=olympiad_data
    )
    if created:
        # Add some questions
        for i in range(1, 11):
            Question.objects.create(
                olympiad=olympiad,
                text=f"Savol #{i}: Bu {olympiad.subject} bo'yicha {i}-savol.",
                options=['A varianti', 'B varianti', 'C varianti', 'D varianti'],
                correct_answer=(i % 4),
                points=1,
                order=i
            )
        print(f"✅ Olympiad created: {olympiad.title}")

# Create Sample Certificates
certificates_data = [
    {'cert_number': 'CRT-9001', 'grade': '98%', 'status': 'VERIFIED'},
    {'cert_number': 'CRT-9002', 'grade': '85%', 'status': 'VERIFIED'},
    {'cert_number': 'CRT-9003', 'grade': '72%', 'status': 'PENDING'},
    {'cert_number': 'CRT-9004', 'grade': '45%', 'status': 'REJECTED'},
]

olympiad = Olympiad.objects.first()
for cert_data in certificates_data:
    cert, created = Certificate.objects.get_or_create(
        cert_number=cert_data['cert_number'],
        defaults={
            'user': student,
            'olympiad': olympiad,
            'grade': cert_data['grade'],
            'status': cert_data['status'],
        }
    )
    if created:
        print(f"✅ Certificate created: {cert.cert_number}")

# Create Sample Support Ticket
ticket, created = SupportTicket.objects.get_or_create(
    ticket_number='TCK-1024',
    defaults={
        'user': student,
        'subject': 'To\'lov muammosi',
        'category': 'Payment',
        'priority': 'HIGH',
        'status': 'OPEN',
    }
)
if created:
    TicketMessage.objects.create(
        ticket=ticket,
        sender_id=str(student.id),
        sender_name=student.get_full_name(),
        message='Salom, to\'lovni amalga oshirdim lekin kurs ochilmayapti.'
    )
    print(f"✅ Support ticket created: {ticket.ticket_number}")

print("\n🎉 Seed data created successfully!")
