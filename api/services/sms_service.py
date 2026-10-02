import requests
import logging
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

class EskizSMSService:
    AUTH_URL = "https://notify.eskiz.uz/api/auth/login"
    SEND_URL = "https://notify.eskiz.uz/api/message/sms/send"

    @classmethod
    def get_token(cls):
        # Try to get from cache
        token = cache.get('eskiz_token')
        if token:
            return token
            
        email = getattr(settings, 'ESKIZ_EMAIL', None)
        password = getattr(settings, 'ESKIZ_PASSWORD', None)
        
        if not email or not password:
            logger.error("Eskiz credentials (ESKIZ_EMAIL, ESKIZ_PASSWORD) not found in settings.")
            return None
            
        try:
            response = requests.post(cls.AUTH_URL, data={'email': email, 'password': password}, timeout=10)
            if response.status_code == 200:
                token = response.json().get('data', {}).get('token')
                if token:
                    # Eskiz token is valid for 30 days, we cache it for 29 days
                    cache.set('eskiz_token', token, 60 * 60 * 24 * 29)
                    return token
            logger.error(f"Eskiz Auth failed: {response.text}")
        except Exception as e:
            logger.error(f"Eskiz Auth Error: {str(e)}")
            
        return None

    @classmethod
    def send_sms(cls, phone, message):
        """
        Sends SMS using Eskiz.uz.
        Phone should be in format '998901234567' (no plus sign).
        """
        # Format phone number: remove non-digits
        formatted_phone = ''.join(filter(str.isdigit, str(phone)))
        
        # In case phone does not have 998 prefix but is local
        if len(formatted_phone) == 9:
            formatted_phone = '998' + formatted_phone
            
        token = cls.get_token()
        if not token:
            logger.error("Failed to get Eskiz token, cannot send SMS.")
            return False
            
        headers = {
            'Authorization': f'Bearer {token}'
        }
        
        data = {
            'mobile_phone': formatted_phone,
            'message': message,
            'from': '4546' # Default Eskiz sender
        }
        
        try:
            response = requests.post(cls.SEND_URL, headers=headers, data=data, timeout=10)
            if response.status_code == 200:
                return True
            else:
                logger.error(f"Eskiz SMS send failed: {response.text}")
                # if token expired, invalidate cache and try once more
                if response.status_code == 401:
                    cache.delete('eskiz_token')
                return False
        except Exception as e:
            logger.error(f"Eskiz SMS Send Error: {str(e)}")
            return False
