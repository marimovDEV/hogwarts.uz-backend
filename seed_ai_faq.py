#!/usr/bin/env python
"""
Seed script for AI Assistant FAQ data
Run with: python seed_ai_faq.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from api.models import AIAssistantFAQ

def seed_ai_faq():
    """Populate AI Assistant FAQ with initial data"""
    
    faqs = [
        {
            'question_uz': "Qaysi kursni tanlashim kerak?",
            'question_ru': "Какой курс мне выбрать?",
            'answer_uz': "Kurs tanlash uchun avval qiziqishlaringiz va maqsadlaringizni aniqlang. Bizda dasturlash, dizayn, marketing va boshqa yo'nalishlar bo'yicha kurslar mavjud. Bepul konsultatsiya olish uchun biz bilan bog'laning.",
            'answer_ru': "Для выбора курса сначала определите свои интересы и цели. У нас есть курсы по программированию, дизайну, маркетингу и другим направлениям. Свяжитесь с нами для бесплатной консультации.",
            'category': 'COURSES',
            'priority': 10,
            'order': 1,
            'search_tags': 'kurs, tanlash, yo\'nalish, dasturlash, dizayn, курс, выбор, направление',
            'action_label_uz': 'Kurslarni ko\'rish',
            'action_label_ru': 'Посмотреть курсы',
            'action_link': '/courses'
        },
        {
            'question_uz': "Narxlar qanday?",
            'question_ru': "Какие цены?",
            'answer_uz': "Kurslarimizning narxlari turli xil. Bepul darslar ham mavjud. To'liq narxlar ro'yxati va chegirmalar haqida ma'lumot olish uchun kurslar sahifasiga o'ting yoki biz bilan bog'laning.",
            'answer_ru': "Цены на наши курсы различаются. Также доступны бесплатные уроки. Для получения полного прайс-листа и информации о скидках перейдите на страницу курсов или свяжитесь с нами.",
            'category': 'PAYMENTS',
            'priority': 9,
            'order': 2,
            'search_tags': 'narx, to\'lov, chegirma, bepul, цена, оплата, скидка, бесплатно',
            'action_label_uz': 'Narxlarni ko\'rish',
            'action_label_ru': 'Посмотреть цены',
            'action_link': '/courses'
        },
        {
            'question_uz': "Bepul darslar bormi?",
            'question_ru': "Есть ли бесплатные уроки?",
            'answer_uz': "Ha, bizda ko'plab bepul darslar mavjud! Siz ro'yxatdan o'tmasdan ham ularni ko'rishingiz mumkin. Bepul darslar bo'limiga o'ting va o'rganishni boshlang.",
            'answer_ru': "Да, у нас много бесплатных уроков! Вы можете смотреть их даже без регистрации. Перейдите в раздел бесплатных уроков и начните обучение.",
            'category': 'COURSES',
            'priority': 8,
            'order': 3,
            'search_tags': 'bepul, dars, ro\'yxat, бесплатно, урок, регистрация',
            'action_label_uz': 'Bepul darslar',
            'action_label_ru': 'Бесплатные уроки',
            'action_link': '/#free-courses'
        },
        {
            'question_uz': "Sertifikat beriladimi?",
            'question_ru': "Выдается ли сертификат?",
            'answer_uz': "Ha, kursni muvaffaqiyatli tugatganingizdan so'ng sizga rasmiy sertifikat beriladi. Sertifikat elektron shaklda bo'lib, uni LinkedIn va boshqa platformalarda baham ko'rishingiz mumkin.",
            'answer_ru': "Да, после успешного завершения курса вам выдается официальный сертификат. Сертификат в электронном виде, и вы можете поделиться им в LinkedIn и других платформах.",
            'category': 'COURSES',
            'priority': 7,
            'order': 4,
            'search_tags': 'sertifikat, diplom, tasdiqnoma, сертификат, диплом',
            'action_label_uz': 'Sertifikatlar haqida',
            'action_label_ru': 'О сертификатах',
            'action_link': '/certificates'
        },
        {
            'question_uz': "Olimpiadalar qanday o'tkaziladi?",
            'question_ru': "Как проводятся олимпиады?",
            'answer_uz': "Olimpiadalar onlayn formatda o'tkaziladi. Siz ro'yxatdan o'tib, belgilangan vaqtda testni topshirasiz. Natijalar shaffof tarzda e'lon qilinadi va eng yaxshi ishtirokchilar sovg'alar oladi.",
            'answer_ru': "Олимпиады проводятся в онлайн формате. Вы регистрируетесь и сдаете тест в назначенное время. Результаты публикуются прозрачно, и лучшие участники получают призы.",
            'category': 'OLYMPIADS',
            'priority': 8,
            'order': 5,
            'search_tags': 'olimpiada, test, natija, sovg\'a, олимпиада, тест, результат, приз',
            'action_label_uz': 'Olimpiadalar',
            'action_label_ru': 'Олимпиады',
            'action_link': '/olympiads'
        },
        {
            'question_uz': "Qanday to'lash mumkin?",
            'question_ru': "Как можно оплатить?",
            'answer_uz': "To'lovni Click, Payme, Uzcard va boshqa to'lov tizimlari orqali amalga oshirishingiz mumkin. Barcha to'lovlar xavfsiz va shifrlangan.",
            'answer_ru': "Оплату можно произвести через Click, Payme, Uzcard и другие платежные системы. Все платежи безопасны и зашифрованы.",
            'category': 'PAYMENTS',
            'priority': 6,
            'order': 6,
            'search_tags': 'to\'lov, click, payme, uzcard, оплата, платеж',
            'action_label_uz': 'To\'lov usullari',
            'action_label_ru': 'Способы оплаты',
            'action_link': '/courses'
        },
        {
            'question_uz': "Qanday ro'yxatdan o'tish mumkin?",
            'question_ru': "Как зарегистрироваться?",
            'answer_uz': "Ro'yxatdan o'tish juda oson! Saytning yuqori qismidagi 'Kirish' tugmasini bosing va telefon raqamingiz yoki email orqali ro'yxatdan o'ting. Jarayon bir necha daqiqa davom etadi.",
            'answer_ru': "Регистрация очень простая! Нажмите кнопку 'Войти' в верхней части сайта и зарегистрируйтесь через номер телефона или email. Процесс занимает несколько минут.",
            'category': 'GENERAL',
            'priority': 7,
            'order': 7,
            'search_tags': 'ro\'yxat, kirish, registratsiya, регистрация, вход',
            'action_label_uz': 'Ro\'yxatdan o\'tish',
            'action_label_ru': 'Зарегистрироваться',
            'action_link': '/login'
        },
        {
            'question_uz': "Kurs davomiyligi qancha?",
            'question_ru': "Какова продолжительность курса?",
            'answer_uz': "Kurslar davomiyligi turlicha - 1 oydan 6 oygacha. Har bir kursning batafsil ma'lumotida aniq davomiylik ko'rsatilgan. Siz o'z vaqtingizga mos kursni tanlashingiz mumkin.",
            'answer_ru': "Продолжительность курсов различна - от 1 до 6 месяцев. В подробной информации каждого курса указана точная продолжительность. Вы можете выбрать курс, подходящий вашему графику.",
            'category': 'COURSES',
            'priority': 6,
            'order': 8,
            'search_tags': 'davomiylik, vaqt, muddat, продолжительность, время, срок',
            'action_label_uz': 'Kurslar',
            'action_label_ru': 'Курсы',
            'action_link': '/courses'
        },
        {
            'question_uz': "Mentorlar kim?",
            'question_ru': "Кто наши менторы?",
            'answer_uz': "Bizning mentorlarimiz - o'z sohasida tajribali mutaxassislar. Ular xalqaro kompaniyalarda ishlagan va ko'plab muvaffaqiyatli loyihalarda qatnashgan. Har bir mentor haqida batafsil ma'lumotni saytda topishingiz mumkin.",
            'answer_ru': "Наши менторы - опытные специалисты в своей области. Они работали в международных компаниях и участвовали во многих успешных проектах. Подробную информацию о каждом менторе можно найти на сайте.",
            'category': 'GENERAL',
            'priority': 5,
            'order': 9,
            'search_tags': 'mentor, o\'qituvchi, ustoz, ментор, учитель, преподаватель',
            'action_label_uz': 'Mentorlar',
            'action_label_ru': 'Менторы',
            'action_link': '/#teachers'
        },
        {
            'question_uz': "Yordam kerak bo'lsa kim bilan bog'lanaman?",
            'question_ru': "С кем связаться, если нужна помощь?",
            'answer_uz': "Yordam uchun siz bizning qo'llab-quvvatlash xizmatimiz bilan bog'lanishingiz mumkin. Telefon: +998 90 123 45 67, Email: support@ardent.uz. Shuningdek, saytdagi chat orqali ham savol berishingiz mumkin.",
            'answer_ru': "Для помощи вы можете связаться с нашей службой поддержки. Телефон: +998 90 123 45 67, Email: support@ardent.uz. Также можете задать вопрос через чат на сайте.",
            'category': 'GENERAL',
            'priority': 9,
            'order': 10,
            'search_tags': 'yordam, qo\'llab-quvvatlash, aloqa, помощь, поддержка, контакт',
            'action_label_uz': 'Bog\'lanish',
            'action_label_ru': 'Связаться',
            'action_link': '/contact'
        }
    ]
    
    print("🤖 Seeding AI Assistant FAQ data...")
    
    # Clear existing data (optional)
    # AIAssistantFAQ.objects.all().delete()
    
    created_count = 0
    updated_count = 0
    
    for faq_data in faqs:
        faq, created = AIAssistantFAQ.objects.update_or_create(
            question_uz=faq_data['question_uz'],
            defaults=faq_data
        )
        if created:
            created_count += 1
            print(f"✅ Created: {faq.question_uz}")
        else:
            updated_count += 1
            print(f"🔄 Updated: {faq.question_uz}")
    
    print(f"\n✨ Seeding complete!")
    print(f"   Created: {created_count}")
    print(f"   Updated: {updated_count}")
    print(f"   Total: {AIAssistantFAQ.objects.count()} FAQs in database")

if __name__ == '__main__':
    seed_ai_faq()
