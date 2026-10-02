import os
import requests
import logging
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

class EskizSMSService:
    AUTH_URL = "https://notify.eskiz.uz/api/auth/login"
    SEND_URL = "https://notify.eskiz.uz/api/message/sms/send"

    def __init__(self):
        self.email = getattr(settings, 'ESKIZ_EMAIL', None) or os.environ.get('ESKIZ_EMAIL')
        self.password = getattr(settings, 'ESKIZ_PASSWORD', None) or os.environ.get('ESKIZ_PASSWORD')

    @classmethod
    def get_token(cls):
        """Tokenni keshdan oladi yoki yangi so'rov yuboradi (29 kunga keshlaydi)"""
        token = cache.get('eskiz_token')
        if token:
            return token
            
        email = getattr(settings, 'ESKIZ_EMAIL', None) or os.environ.get('ESKIZ_EMAIL')
        password = getattr(settings, 'ESKIZ_PASSWORD', None) or os.environ.get('ESKIZ_PASSWORD')
        
        if not email or not password:
            logger.error("Eskiz credentials (ESKIZ_EMAIL, ESKIZ_PASSWORD) not found.")
            return None
            
        try:
            response = requests.post(cls.AUTH_URL, data={'email': email, 'password': password}, timeout=10)
            if response.status_code == 200:
                data = response.json()
                token = data.get('data', {}).get('token')
                if token:
                    # Eskiz token 30 kun amal qiladi, 29 kunga keshlaymiz (2505600 soniya)
                    cache.set('eskiz_token', token, 2505600)
                    return token
            logger.error(f"Eskiz Auth failed ({response.status_code}): {response.text}")
        except Exception as e:
            logger.error(f"Eskiz Auth Error: {str(e)}")
            
        return None

    @classmethod
    def send_sms(cls, phone_number, message, from_sender='4546'):
        """
        SMS yuborish.
        Telefon formati: 998XXXXXXXXX
        """
        # Raqamni faqat raqamlardan iborat qilish
        clean_phone = ''.join(filter(str.isdigit, str(phone_number)))
        if len(clean_phone) == 9:
            clean_phone = '998' + clean_phone

        token = cls.get_token()
        if not token:
            logger.error("Eskiz token olinmadi, SMS yuborilmadi.")
            return None

        headers = {
            'Authorization': f'Bearer {token}'
        }

        payload = {
            'mobile_phone': clean_phone,
            'message': message,
            'from': from_sender,
        }

        try:
            response = requests.post(cls.SEND_URL, headers=headers, data=payload, timeout=10)
            if response.status_code == 200:
                res_json = response.json()
                logger.info(f"Eskiz SMS yuborildi ({clean_phone}): {res_json}")
                return res_json
            elif response.status_code == 401:
                # Token eskirgan bo'lsa keshni tozalab, yana bir marta urinib ko'rish
                logger.warning("Eskiz token eskirgan (401), kesh tozalanmoqda va qayta urinilmoqda...")
                cache.delete('eskiz_token')
                token = cls.get_token()
                if token:
                    headers['Authorization'] = f'Bearer {token}'
                    retry_res = requests.post(cls.SEND_URL, headers=headers, data=payload, timeout=10)
                    if retry_res.status_code == 200:
                        return retry_res.json()
                logger.error(f"Eskiz SMS qayta yuborishda xatolik: {response.text}")
                return None
            else:
                logger.error(f"Eskiz SMS yuborishda xatolik ({response.status_code}): {response.text}")
                return None
        except Exception as e:
            logger.error(f"Eskiz SMS Send Exception: {str(e)}")
            return None

