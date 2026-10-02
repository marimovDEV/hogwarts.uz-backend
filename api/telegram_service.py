import requests
import random
import string
from django.conf import settings


class TelegramService:
    """
    Telegram Bot service for sending verification codes
    """
    
    @classmethod
    def get_config(cls):
        from .models import BotConfig
        return BotConfig.objects.filter(is_active=True).first()
    
    @classmethod
    def send_message(cls, chat_id: str, message: str) -> bool:
        """
        Send a message via Telegram Bot
        """
        config = cls.get_config()
        if not config or not config.bot_token:
            return False
            
        try:
            url = f"https://api.telegram.org/bot{config.bot_token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "HTML"
            }
            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200
        except Exception as e:
            return False
    
    @classmethod
    def send_to_admin(cls, message: str) -> bool:
        """
        Send message to all configured admin chats (supports multiple IDs)
        """
        config = cls.get_config()
        if not config or not config.admin_chat_id:
            return False
        
        admin_ids = [id.strip() for id in str(config.admin_chat_id).split(',') if id.strip()]
        success = True
        for admin_id in admin_ids:
            if not cls.send_message(admin_id, message):
                success = False
        return success


    @classmethod
    def edit_message_caption(cls, chat_id: str, message_id: str, caption: str) -> bool:
        """
        Edit message caption
        """
        config = cls.get_config()
        if not config or not config.bot_token:
            return False
            
        try:
            url = f"https://api.telegram.org/bot{config.bot_token}/editMessageCaption"
            payload = {
                "chat_id": chat_id,
                "message_id": message_id,
                "caption": caption,
                "parse_mode": "HTML",
                "reply_markup": {"inline_keyboard": []} # Remove buttons
            }
            requests.post(url, json=payload, timeout=10)
            return True
        except:
            return False


def generate_verification_code(length=6):
    """Generate a random numeric verification code"""
    return ''.join(random.choices(string.digits, k=length))


def format_phone_number(phone: str) -> str:
    """Format phone number for display"""
    # Remove non-digits
    digits = ''.join(filter(str.isdigit, phone))
    
    # Format as +998 XX XXX XX XX
    if len(digits) >= 9:
        if digits.startswith('998'):
            return f"+{digits[:3]} {digits[3:5]} {digits[5:8]} {digits[8:10]} {digits[10:12]}"
        else:
            return f"+998 {digits[:2]} {digits[2:5]} {digits[5:7]} {digits[7:9]}"
    return phone
