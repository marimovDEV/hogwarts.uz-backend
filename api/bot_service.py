import requests
from django.conf import settings
from .models import BotConfig, User
import logging

logger = logging.getLogger(__name__)

class BotService:
    """
    Centralized service for Telegram Bot interaction
    """
    
    @staticmethod
    def get_config():
        """Get active bot configuration"""
        return BotConfig.objects.filter(is_active=True).first()

    @classmethod
    def send_message(cls, chat_id, text, parse_mode="HTML", reply_markup=None):
        """Send message via the configured bot"""
        config = cls.get_config()
        if not config or not config.bot_token:
            logger.error("Bot configuration missing or inactive")
            return False
            
        url = f"https://api.telegram.org/bot{config.bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
            
        try:
            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error sending telegram message: {e}")
            print(f"DEBUG: Error sending telegram message: {e}")
            return False

    @classmethod
    def send_to_admin(cls, text):
        """Send message to all configured admin chats (supports multiple IDs)"""
        config = cls.get_config()
        if config and config.admin_chat_id:
            # Support multiple admin IDs separated by comma
            admin_ids = [id.strip() for id in str(config.admin_chat_id).split(',') if id.strip()]
            success = True
            for admin_id in admin_ids:
                result = cls.send_message(admin_id, text)
                if not result:
                    success = False
                    logger.warning(f"Failed to send message to admin ID: {admin_id}")
            return success
        return False

    @classmethod
    def link_user(cls, telegram_id, linking_token):
        """Link a Telegram ID to a platform User via token"""
        try:
            user = User.objects.get(telegram_linking_token=linking_token)
            user.telegram_id = telegram_id
            user.telegram_linking_token = None # Clear token after use
            from django.utils import timezone
            user.telegram_connected_at = timezone.now()
            user.save()
            return user
        except User.DoesNotExist:
            return None

    @classmethod
    def notify_olympiad(cls, user, olympiad, message_type="reminder"):
        """Send olympiad related notification"""
        if not user.telegram_id:
            return False
            
        emoji = "⏰" if message_type == "reminder" else "🚀"
        title = "Olimpiada yaqinlashmoqda!" if message_type == "reminder" else "Olimpiada boshlandi!"
        
        text = f"""
{emoji} <b>{title}</b>

🏆 <b>{olympiad.title}</b>
📚 Fan: {olympiad.subject}
🕒 Vaqt: {olympiad.start_date.strftime('%H:%M')}

<a href="https://ardent.uz/olympiad/{olympiad.id}">Platformada qatnashish</a>
"""
        return cls.send_message(user.telegram_id, text)

    @classmethod
    def notify_meeting(cls, user, course, meeting_time, meeting_url):
        """Send Google Meet notification"""
        if not user.telegram_id:
            return False
            
        text = f"""
🎥 <b>Jonli dars (Meeting) yaqinlashmoqda!</b>

📘 Kurs: {course.title}
🕒 Vaqt: {meeting_time}

<a href="{meeting_url}">Google Meet'ga qo'shilish</a>
"""
        return cls.send_message(user.telegram_id, text)

    @classmethod
    def notify_result(cls, user, result):
        """Send Olympiad Result notification"""
        if not user.telegram_id:
            return False
            
        emoji = "🎉" if result.status == 'COMPLETED' else "🚫"
        title = "Natijalar e'lon qilindi!" if result.status == 'COMPLETED' else "Siz chetlatildingiz!"
        
        text = f"""
{emoji} <b>{title}</b>

📝 <b>{result.olympiad.title}</b>
✅ Ball: {result.score} ({result.percentage:.1f}%)
⏱ Vaqt: {result.time_taken} sek
        
<a href="https://ardent.uz/olympiad/{result.olympiad.id}/result">Batafsil ko'rish</a>
"""
        return cls.send_message(user.telegram_id, text)
    
    @classmethod
    def notify_new_lead(cls, lead):
        """Send notification about new lead from contact form"""
        telegram_line = f'📱 Telegram: @{lead.telegram_username}' if lead.telegram_username else ''
        note_text = lead.note if lead.note else "Yo'q"
        
        text = f"""
🆕 <b>Yangi murojaat!</b>

👤 Ism: {lead.name}
📞 Telefon: {lead.phone}
{telegram_line}

📝 Izoh: {note_text}

⏰ Vaqt: {lead.created_at.strftime('%d.%m.%Y %H:%M')}

<a href="http://localhost:3000/admin/leads">Admin panelda ko'rish</a>
"""
        return cls.send_to_admin(text)

    @classmethod
    def notify_winner(cls, winner_prize):
        """Send notification to the olympiad winner and request address"""
        user = winner_prize.student
        if not user.telegram_id:
            return False
            
        olympiad = winner_prize.olympiad
        position = winner_prize.position
        
        pos_emoji = {1: "🥇", 2: "🥈", 3: "🥉"}.get(position, "🏆")
        pos_text = f"{position}-o'rin"
        
        text = f"""
{pos_emoji} <b>Tabriklaymiz! Siz g'olib bo'ldingiz!</b>

Siz <b>{olympiad.title}</b> olimpiadasida <b>{pos_text}</b>ni qo'lga kiritdingiz! 🎊

Sovrinni yetkazib berishimiz uchun, iltimos, manzilingizni yuboring:
📍 <b>Lokatsiya yuboring</b> (pastdagi tugma orqali)
yoki
📦 <b>To'liq manzilingizni yozib yuboring.</b>
"""
        keyboard = {
            "keyboard": [
                [{"text": "📍 Lokatsiyani yuborish", "request_location": True}],
                [{"text": "❌ Bekor qilish"}]
            ],
            "resize_keyboard": True,
            "one_time_keyboard": True
        }
        return cls.send_message(user.telegram_id, text, reply_markup=keyboard)
