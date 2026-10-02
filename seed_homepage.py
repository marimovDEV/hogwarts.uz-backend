
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from api.models import HomePageConfig, HomeStat, HomeAdvantage, Winner, Subject, Testimonial, User, TeacherProfile

def seed_homepage():
    # 1. Hero
    HomePageConfig.objects.get_or_create(id=1)
    
    # 2. Stats
    stats = [
        {'label': "O'quvchilar", 'value': '10,000+', 'icon': 'Users', 'order': 1},
        {'label': 'Olimpiadalar', 'value': '50+', 'icon': 'Trophy', 'order': 2},
        {'label': "O'qituvchilar", 'value': '100+', 'icon': 'GraduationCap', 'order': 3},
        {'label': 'Kurslar', 'value': '20+', 'icon': 'BookOpen', 'order': 4},
    ]
    for s in stats:
        HomeStat.objects.get_or_create(label=s['label'], defaults=s)

    # 3. Advantages
    advantages = [
        {'title': 'Sifatli Ta\'lim', 'description': 'Eng malakali o\'qituvchilar tomonidan tayyorlangan darslar', 'icon': 'ShieldCheck', 'order': 1},
        {'title': 'Amaliyot', 'description': 'Nazariya va amaliyotning uyg\'unligi', 'icon': 'Zap', 'order': 2},
        {'title': 'Sertifikat', 'description': 'Xalqaro darajadagi sertifikatlarga ega bo\'ling', 'icon': 'FileCheck', 'order': 3},
    ]
    for a in advantages:
        HomeAdvantage.objects.get_or_create(title=a['title'], defaults=a)

    # 4. Winners
    subject = Subject.objects.first()
    if subject:
        Winner.objects.get_or_create(
            student_name='Jasur Alimov',
            defaults={
                'subject': subject,
                'stage': 'REPUBLIC',
                'region': 'Toshkent',
                'score': 95,
                'position': 1,
                'is_featured': True
            }
        )

    # 5. Testimonials
    Testimonial.objects.get_or_create(
        name='Madina Karimova',
        defaults={
            'profession': 'O\'quvchi',
            'text_uz': 'Hogwords Olimpiada bilan o\'z bilimimni sezilarli darajada oshirdim.',
            'text_ru': 'С Hogwords Olimpiada я значительно улучшила свои знания.',
            'rating': 5
        }
    )

    print("✅ Homepage seed data created!")

if __name__ == '__main__':
    seed_homepage()
