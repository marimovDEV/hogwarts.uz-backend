
import os
import django
from django.utils import timezone
from datetime import timedelta

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from api.models import Olympiad, Question, Subject

def create_test_olympiad():
    # 1. Get Subject
    subject = Subject.objects.filter(name='Matematika').first()
    if not subject:
        print("Subject 'Matematika' not found. Creating it...")
        subject = Subject.objects.create(name='Matematika')

    # 2. Create Olympiad
    olympiad, created = Olympiad.objects.update_or_create(
        slug='matematika-sinov-test',
        defaults={
            'title': "Matematika Bo'yicha Sinov Olimpiadasi",
            'description': "Tizimni test qilish uchun maxsus yaratilgan matematika olimpiadasi. Bu orqali savollar, vaqt cheklovi va natijalarni hisoblash funksiyalarini tekshirib ko'rishingiz mumkin.",
            'subject_id': subject,
            'subject': subject.name,
            'start_date': timezone.now() - timedelta(hours=1), # Started an hour ago
            'end_date': timezone.now() + timedelta(days=365), # Ends in a year
            'duration': 30,
            'status': 'ONGOING',
            'level': 'INTERMEDIATE',
            'difficulty': 'MEDIUM',
            'grade_range': "5-11",
            'format': 'ONLINE',
            'is_paid': False,
            'price': 0,
            'max_attempts': 3,
            'xp_reward': 100,
            'is_active': True,
            'rules': "1. Har bir savolga belgilangan vaqt ichida javob bering.\n2. Ko'chirib bosish (Copy/Paste) taqiqlanadi.\n3. Natija avtomatik hisoblanadi.",
            'prizes': "1. Sertifikat\n2. 100 XP",
            'evaluation_criteria': "To'g'ri javob uchun ball beriladi. Xato javob uchun ball ayirilmaydi."
        }
    )

    if created:
        print(f"Olympiad '{olympiad.title}' created.")
    else:
        print(f"Olympiad '{olympiad.title}' updated.")
        # Clear existing questions for fresh test
        olympiad.questions.all().delete()

    # 3. Create Questions
    questions_data = [
        {
            'text': "2 + 2 * 2 amali necha bo'ladi?",
            'type': 'MCQ',
            'options': ["4", "6", "8", "2"],
            'correct_answer': "1", # Index 1 (value "6")
            'points': 5,
            'explanation': "Amallar tartibiga ko'ra avval ko'paytirish, keyin qo'shish bajariladi: 2 * 2 = 4; 2 + 4 = 6."
        },
        {
            'text': "Uchtadan bitta narsa qolsa nima bo'ladi?",
            'type': 'MCQ',
            'options': ["Ikkitasi qoladi", "Hech nima qolmaydi", "Bitta qoladi", "Uchta qoladi"],
            'correct_answer': "2", # Index 2
            'points': 5,
            'explanation': "Savolning o'zida aytilgan: bitta narsa qolsa, bitta qoladi."
        },
        {
            'text': "Kvadratning tomoni 5 ga teng bo'lsa, uning yuzi necha?",
            'type': 'NUMERIC',
            'options': [],
            'correct_answer': "25",
            'points': 10,
            'explanation': "Kvadrat yuzi S = a^2 formulasi bilan hisoblanadi: 5 * 5 = 25."
        },
        {
            'text': "Qaysi son tub son (prime number)?",
            'type': 'MCQ',
            'options': ["9", "15", "17", "21"],
            'correct_answer': "2", # Index 2 (value "17")
            'points': 5,
            'explanation': "17 soni faqat 1 ga va o'ziga bo'linadi."
        },
        {
            'text': "Tenglamani yeching: 2x + 10 = 20",
            'type': 'NUMERIC',
            'options': [],
            'correct_answer': "5",
            'points': 10,
            'explanation': "2x = 10, x = 5."
        }
    ]

    for idx, q in enumerate(questions_data):
        Question.objects.create(
            olympiad=olympiad,
            text=q['text'],
            type=q['type'],
            options=q['options'],
            correct_answer=q['correct_answer'],
            points=q['points'],
            explanation=q['explanation'],
            order=idx + 1,
            time_limit=60 # 60 seconds per question
        )

    print(f"Successfully added {len(questions_data)} questions.")

if __name__ == "__main__":
    create_test_olympiad()
