from django.core.management.base import BaseCommand
from django.utils import timezone
from api.models import User, UserStreak
import requests

class Command(BaseCommand):
    help = 'Send study reminders to users via Telegram'

    def handle(self, *args, **kwargs):
        # Time check (Optional: only run at 18:00 or 21:00 if scheduled via cron)
        # For now, we assume this is run by a scheduler
        
        now = timezone.now()
        print(f"Running reminder check at {now}")
        
        # Get users who have Telegram connected
        users = User.objects.filter(telegram_id__isnull=False)
        
        for user in users:
            # Check if studied today
            streak, _ = UserStreak.objects.get_or_create(user=user)
            if streak.last_activity_date != now.date():
                # Send Reminder
                self.send_telegram_message(user.telegram_id, self.get_message(user))
                
        self.stdout.write(self.style.SUCCESS('Successfully sent reminders'))

    def get_message(self, user):
        hour = timezone.localtime().hour
        if hour < 20: # 18:00 check
            return f"👋 Salom {user.first_name}! Bugun dars qilish esdan chiqmasin. 🔥 Streakingiz yonib ketishi mumkin!"
        else: # 21:00 check
            return f"🚨 Diqqat {user.first_name}! Kuni tugashiga oz qoldi. Hoziroq bitta darsni tugating va streakingizni saqlab qoling! ⚡️"

    def send_telegram_message(self, chat_id, text):
        # In production, use settings.TELEGRAM_BOT_TOKEN
        # BOT_TOKEN = settings.TELEGRAM_BOT_TOKEN
        # url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        # requests.post(url, json={'chat_id': chat_id, 'text': text})
        
        print(f"Mock Sending to {chat_id}: {text}")
