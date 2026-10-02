from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
import threading

class EmailService:
    @staticmethod
    def send_async_email(subject, message, recipient_list):
        """Send email in a separate thread to avoid blocking"""
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                recipient_list,
                html_message=message, # Send as HTML
                fail_silently=False,
            )
        except Exception as e:
            print(f"Error sending email: {e}")

    @classmethod
    def send_welcome_email(cls, user):
        """Send welcome email to new user"""
        subject = "Hogwords Olimpiada platformasiga xush kelibsiz!"
        message = f"""
        <h1>Assalomu alaykum, {user.first_name}!</h1>
        <p>Siz muvaffaqiyatli ro'yxatdan o'tdingiz.</p>
        <p>Login: {user.phone}</p>
        <br>
        <p>Platformadan foydalanishni boshlash uchun quyidagi havolani bosing:</p>
        <a href="https://hogwords.uz/dashboard">Kirish</a>
        """
        threading.Thread(target=cls.send_async_email, args=(subject, message, [user.email or user.username + "@example.com"])).start()

    @classmethod
    def send_receipt(cls, user, item, amount):
        """Send purchase receipt"""
        subject = f"To'lov qabul qilindi: {item.title}"
        message = f"""
        <h1>To'lov muvaffaqiyatli amalga oshirildi!</h1>
        <p>Hurmatli {user.first_name},</p>
        <p>Siz quyidagi xaridni amalga oshirdingiz:</p>
        <ul>
            <li><b>Mahsulot:</b> {item.title}</li>
            <li><b>Summa:</b> {amount} so'm</li>
            <li><b>Sana:</b> Bugun</li>
        </ul>
        <p>Xaridingiz uchun rahmat!</p>
        """
        # Ideally use user.email, fallback if not set
        if user.email:
            threading.Thread(target=cls.send_async_email, args=(subject, message, [user.email])).start()
