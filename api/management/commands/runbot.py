import time
import requests
import json
import logging
import traceback
from decimal import Decimal, ROUND_HALF_UP
from django.core.management.base import BaseCommand
from django.conf import settings
from api.models import BotConfig, User, Olympiad, OlympiadRegistration, Payment, WinnerPrize, PrizeAddress
from api.models_settings import PlatformSettings, PaymentProviderConfig
from api.bot_service import BotService
from django.core.files.base import ContentFile
from django.db.models import Q
from django.utils import timezone

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# STATES
STATE_NONE = 0
STATE_WAIT_PHONE = 1 # Not used if contact is shared directly
STATE_WAIT_AMOUNT = 2
STATE_WAIT_RECEIPT = 3
STATE_WAIT_ADDRESS = 4

class Command(BaseCommand):
    help = 'Runs the Telegram Bot via Long Polling (Interactive)'
    
    # Store user states in memory: {chat_id: {"state": STATE_..., "data": {...}}}
    user_states = {}

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🚀 Starting Hogwords Olimpiada Interactive Bot...'))
        
        # 1. Load Configuration
        config = BotConfig.objects.filter(is_active=True).first()
        if not config or not config.bot_token:
            self.stdout.write(self.style.ERROR('❌ Bot configuration missing or inactive in DB.'))
            return

        token = config.bot_token
        self.bot_token = token
        self.api_url = f"https://api.telegram.org/bot{token}"
        self.admin_chat_ids = [chat_id.strip() for chat_id in config.admin_chat_id.split(',')] if config.admin_chat_id else []
        
        self.stdout.write(f"ℹ️ Token: {token[:10]}...******")
        self.stdout.write(f"ℹ️ Admins: {self.admin_chat_ids}")

        # 2. Verify Bot Identity
        try:
            me = self.send_request("getMe")
            if not me or not me.get('ok'):
                self.stdout.write(self.style.ERROR(f'❌ Invalid Token or API Error: {me}'))
                return
            
            bot_info = me['result']
            self.stdout.write(self.style.SUCCESS(f"✅ Connected as @{bot_info['username']} ({bot_info['first_name']})"))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Connection Error: {e}'))
            return

        # 3. Start Polling Loop
        offset = 0
        self.stdout.write(self.style.SUCCESS('📡 Polling started...'))

        while True:
            try:
                # Long polling with timeout
                params = {'offset': offset + 1, 'timeout': 30, 'limit': 100}
                response = requests.get(f"{self.api_url}/getUpdates", params=params, timeout=40)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('ok'):
                        updates = data.get('result', [])
                        
                        for update in updates:
                            update_id = update.get('update_id')
                            if update_id > offset:
                                offset = update_id
                            
                            try:
                                self.process_update(update)
                            except Exception as pe:
                                self.stdout.write(self.style.ERROR(f"⚠️ Error processing update {update_id}: {pe}"))
                    else:
                        self.stdout.write(self.style.WARNING(f"⚠️ API Error: {data}"))
                else:
                    self.stdout.write(self.style.WARNING(f"⚠️ HTTP Error: {response.status_code}"))
                    time.sleep(5)

            except requests.exceptions.Timeout:
                continue
            except requests.exceptions.ConnectionError as e:
                self.stdout.write(self.style.ERROR(f"❌ Connection lost: {e}. Retrying in 5s..."))
                time.sleep(5)
            except KeyboardInterrupt:
                self.stdout.write(self.style.SUCCESS("🛑 Bot stopped by user."))
                break
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Unexpected Error: {e}"))
                time.sleep(5)

    def send_request(self, method, payload=None):
        """Helper to send requests to Telegram API"""
        url = f"{self.api_url}/{method}"
        try:
            if payload:
                # remove None values
                payload = {k: v for k, v in payload.items() if v is not None}
                response = requests.post(url, json=payload, timeout=20)
            else:
                response = requests.get(url, timeout=20)
            return response.json()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Request Error ({method}): {e}"))
            return None

    def send_message(self, chat_id, text, reply_markup=None):
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "reply_markup": reply_markup
        }
        return self.send_request("sendMessage", payload)

    def send_photo(self, chat_id, photo_url_or_id, caption=None, reply_markup=None):
        payload = {
            "chat_id": chat_id,
            "photo": photo_url_or_id,
            "caption": caption,
            "parse_mode": "HTML",
            "reply_markup": reply_markup
        }
        return self.send_request("sendPhoto", payload)

    def process_update(self, update):
        # Handle Callback Queries (Admin Actions)
        if 'callback_query' in update:
            self.handle_callback(update['callback_query'])
            return

        # Handle Messages
        if 'message' not in update:
            return

        message = update['message']
        chat_id = message['chat']['id']
        text = message.get('text', '').strip()
        location = message.get('location')
        user_name = message['from'].get('first_name', 'User')

        # Check Active State
        state = self.user_states.get(chat_id, {}).get("state", STATE_NONE)
        
        # Handle Location specifically for prizes
        if location:
            self.handle_location(chat_id, location)
            return
        
        # --- COMMANDS ---

        if text.startswith('/start pay_'):
            try:
                payment_id = int(text.split('pay_')[1])
                payment = Payment.objects.filter(id=payment_id, status='PENDING').first()
                
                if not payment:
                    self.send_message(chat_id, "❌ To'lov topilmadi yoki allaqachon yakunlangan.")
                    return

                # Get Manual Payment Config for Card Number
                manual_config = PaymentProviderConfig.objects.filter(type='MANUAL', is_active=True).first()
                card_number = manual_config.config.get('card_number', '----') if manual_config else "Admin so'rang"
                card_holder = manual_config.config.get('holder_name', '') if manual_config else ""
                
                msg = (
                    f"🆔 <b>To'lov ID:</b> #{payment.id}\n"
                    f"💰 <b>Summa:</b> {int(payment.amount):,} UZS\n\n"
                    f"💳 <b>Karta:</b> <code>{card_number}</code>\n"
                    f"👤 <b>Ega:</b> {card_holder}\n\n"
                    f"📸 Iltimos, to'lovni amalga oshirib, <b>chekni (skrinshot)</b> ushbu botga yuboring."
                )
                
                self.send_message(chat_id, msg)
                self.user_states[chat_id] = {"state": STATE_WAIT_RECEIPT, "data": {"payment_id": payment.id}}
                return

                return
            except Exception as e:
                self.send_message(chat_id, "❌ Xatolik yuz berdi.")
                logger.error(f"Pay Start Error: {e}")
                return

        elif text.startswith('/start topup_'):
            try:
                # Format: /start topup_50000
                amount_uzs = int(text.split('topup_')[1])
                
                rate = self.get_rate()
                coins = int(amount_uzs / rate)
                
                if coins < 10:
                    self.send_message(chat_id, "⚠️ Minimal miqdor: 10 Coin")
                    return

                # Check Manual Provider
                manual_config = PaymentProviderConfig.objects.filter(type='MANUAL', is_active=True).first()
                if not manual_config:
                    self.send_message(chat_id, "⚠️ Tachim to'lov tizimida xatolik. Admin bilan bog'laning.")
                    return

                card_number = manual_config.config.get('card_number', '----')
                card_holder = manual_config.config.get('holder_name', '')
                
                msg = (
                    f"💳 <b>To'lov uchun ma'lumot:</b>\n\n"
                    f"🪙 <b>Miqdor:</b> {coins} AC\n"
                    f"💵 <b>To'lanadigan summa:</b> {amount_uzs:,.0f} so'm\n\n"
                    f"🏦 <b>Karta:</b> <code>{card_number}</code>\n"
                    f"👤 <b>Ega:</b> {card_holder}\n\n"
                    f"❗️ Iltimos, to'lovni amalga oshirib, <b>CHEK RASMINI</b> shu yerga yuboring."
                )
                
                # Set State
                self.user_states[chat_id] = {
                    "state": STATE_WAIT_RECEIPT, 
                    "data": {
                        "amount": coins,
                        "sum": amount_uzs
                    }
                }
                
                self.send_message(chat_id, msg)
                return

            except Exception as e:
                self.send_message(chat_id, "❌ Noto'g'ri summa formati.")
                logger.error(f"Topup Start Error: {e}")
                return

        elif text == '/start':
            # Reset state
            self.user_states[chat_id] = {"state": STATE_NONE, "data": {}}
            
            user = User.objects.filter(telegram_id=chat_id).first()
            if user:
                self.show_main_menu(chat_id, f"👋 Salom, <b>{user.first_name}</b>!\n\nPlatforma botiga xush kelibsiz.")
            else:
                welcome_text = (
                    "👋 <b>Assalomu alaykum!</b>\n\n"
                    "Bu <b>Hogwords Olimpiada</b> rasmiy boti.\n"
                    "Hisobingizga kirish uchun telefon raqamingizni yuboring:"
                )
                
                keyboard = {
                    "keyboard": [
                        [{"text": "📱 Telefon raqamni yuborish", "request_contact": True}]
                    ],
                    "resize_keyboard": True,
                    "one_time_keyboard": True
                }
                self.send_message(chat_id, welcome_text, reply_markup=keyboard)
            return
            
        elif message.get('contact'):
             # Handle contact sharing
             contact = message['contact']
             phone = contact.get('phone_number')
             if phone:
                 self.handle_contact_login(chat_id, phone, message['from'].get('first_name'))
             return

        elif text == '/cancel' or text == '❌ Bekor qilish':
            self.user_states[chat_id] = {"state": STATE_NONE, "data": {}}
            self.show_main_menu(chat_id, "❌ Bekor qilindi.")
            return

        # Handle Photos (Payment Receipts)
        if 'photo' in message:
            state_data = self.user_states.get(chat_id, {})
            if state_data.get("state") == STATE_WAIT_RECEIPT:
                try:
                    # Get data from state
                    coins = state_data['data'].get("amount")
                    total_sum = state_data['data'].get("sum")
                    
                    if not coins or not total_sum:
                        self.send_message(chat_id, "❌ Ma'lumotlar eskirgan. Iltimos qaytadan /start bosib urinib ko'ring.")
                        self.user_states[chat_id] = {"state": STATE_NONE}
                        return

                    # Get User
                    user = User.objects.filter(telegram_id=chat_id).first()
                    if not user:
                        self.send_message(chat_id, "⚠️ Iltimos, avval ro'yxatdan o'ting (/start).")
                        return

                    photo = message['photo'][-1] # Get largest
                    file_id = photo['file_id']
                    
                    # Delegate to common method
                    self.create_payment_request(chat_id, user, coins, total_sum, file_id)
                    return

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"❌ Photo Handler Error: {e}"))
                    self.send_message(chat_id, "❌ Tizim xatosi. Qaytadan urinib ko'ring.")
            
            return

        # --- LOGGED IN USER MENU ---
        
        # Verify User Login for protected commands
        user = User.objects.filter(telegram_id=chat_id).first()
        if not user:
            if state == STATE_NONE:
                self.send_message(chat_id, "⚠️ Iltimos, /start ni bosib telefon raqamingizni yuboring.")
            return

        if text == "👤 Profil":
            msg = (
                f"👤 <b>Profil:</b> {user.first_name} {user.last_name or ''}\n"
                f"📞 <b>Tel:</b> {user.phone}\n"
                f"🆔 <b>ID:</b> {user.username}\n"
                f"📅 <b>Ro'yxatdan o'tgan:</b> {user.date_joined.strftime('%d.%m.%Y')}"
            )
            self.send_message(chat_id, msg)
            return
            
        elif text == "💰 Hisobim":
            msg = (
                f"💰 <b>Sizning Hisobingiz:</b>\n\n"
                f"🪙 <b>Coin:</b> {int(user.balance)} AC\n"
                f"💵 <b>Tahminiy qiymat:</b> {int(user.balance * self.get_rate())} so'm"
            )
            self.send_message(chat_id, msg)
            return

        elif text == "➕ Hisob to'ldirish":
            self.user_states[chat_id] = {"state": STATE_WAIT_AMOUNT, "data": {}}
            rate = self.get_rate()
            msg = (
                f"💸 <b>Hisobni to'ldirish</b>\n\n"
                f"Joriy kurs: <b>1 AC = {rate} so'm</b>\n\n"
                f"Necha Coin sotib olmoqchisiz? (Raqam yozing):"
            )
            keyboard = {
                "keyboard": [[{"text": "❌ Bekor qilish"}]], 
                "resize_keyboard": True
            }
            self.send_message(chat_id, msg, reply_markup=keyboard)
            return
        
        # --- STATE HANDLERS ---

        if state == STATE_WAIT_AMOUNT:
            try:
                coins = int(text)
                if coins < 10:
                    self.send_message(chat_id, "⚠️ Minimal miqdor: 10 Coin")
                    return
                
                rate = self.get_rate()
                total_sum = coins * rate
                
                # Manual Provider Config
                provider_config = PaymentProviderConfig.objects.filter(type='MANUAL', is_active=True).first()
                if not provider_config:
                    self.send_message(chat_id, "⚠️ Hozircha karta orqali to'lov ishlamayapti. Keyinroq urinib ko'ring.")
                    self.user_states[chat_id] = {"state": STATE_NONE}
                    return

                card_number = provider_config.config.get('card_number', "ADMIN SO'RANG")
                holder = provider_config.config.get('holder_name', '')
                
                msg = (
                    f"💳 <b>To'lov uchun ma'lumot:</b>\n\n"
                    f"🪙 <b>Miqdor:</b> {coins} AC\n"
                    f"💵 <b>To'lanadigan summa:</b> {total_sum:,.0f} so'm\n\n"
                    f"🏦 <b>Karta:</b> <code>{card_number}</code>\n"
                    f"👤 <b>Ega:</b> {holder}\n\n"
                    f"❗️ Iltimos, to'lovni amalga oshirib, <b>CHEK RASMINI</b> shu yerga yuboring."
                )
                
                self.user_states[chat_id]["data"]["amount"] = coins
                self.user_states[chat_id]["data"]["sum"] = total_sum
                self.user_states[chat_id]["state"] = STATE_WAIT_RECEIPT
                self.send_message(chat_id, msg)
                
            except ValueError:
                self.send_message(chat_id, "⚠️ Iltimos, faqat raqam kiriting (masalan: 100).")
            return

        elif state == STATE_WAIT_RECEIPT:
            if 'photo' not in message:
                self.send_message(chat_id, "⚠️ Iltimos, chek rasmini yuboring yoki /cancel ni bosing.")
                return
            
            # Get largest photo
            photo = message['photo'][-1]
            file_id = photo['file_id']
            
            # Create Payment Record
            amount = self.user_states[chat_id]["data"]["amount"]
            total_sum = self.user_states[chat_id]["data"]["sum"]
            
            self.create_payment_request(chat_id, user, amount, total_sum, file_id)
            return

        # Handle Address Text if in STATE_WAIT_ADDRESS
        if state == STATE_WAIT_ADDRESS and text and not text.startswith('/'):
            self.handle_address_text(chat_id, text)
            return


    def create_payment_request(self, chat_id, user, coins, total_sum, file_id):
        try:
            # 1. Download Photo
            file_info = self.send_request("getFile", {"file_id": file_id})
            if file_info and file_info.get('ok'):
                file_path = file_info['result']['file_path']
                download_url = f"https://api.telegram.org/file/bot{self.bot_token}/{file_path}"
                
                r = requests.get(download_url)
                if r.status_code == 200:
                    # Save Payment DB
                    payment = Payment.objects.create(
                        user=user,
                        amount=total_sum, # Final Amount in UZS 
                        original_amount=total_sum,
                        type='TOPUP',
                        method='BOT',
                        status='PENDING',
                        transaction_id=f"BOT-{int(time.time())}"
                    )
                    
                    # Save Image
                    file_name = f"receipt_{payment.id}.jpg"
                    payment.receipt_image.save(file_name, ContentFile(r.content))
                    
                    # Notify User
                    self.send_message(chat_id, "✅ <b>To'lov qabul qilindi!</b>\n\nAdmin tasdiqlashini kuting. Tasdiqlangach hisobingiz to'ldiriladi.")
                    self.user_states[chat_id] = {"state": STATE_NONE}
                    self.show_main_menu(chat_id, "Bosh menyu:")
                    
                    # Notify Admins
                    self.notify_admins(payment, coins, total_sum, file_id, user)
                    return
                else:
                    error_msg = f"❌ Image Download Failed. Status: {r.status_code}"
                    self.stdout.write(self.style.ERROR(error_msg))
                    self.send_message(chat_id, f"⚠️ {error_msg}")
                    return
            
            else:
                 error_msg = f"❌ getFile Failed. Info: {file_info}"
                 self.stdout.write(self.style.ERROR(error_msg))
                 self.send_message(chat_id, "⚠️ Telegram fayl ma'lumotlarini bermadi. Qaytadan urinib ko'ring.")
                 return

        except Exception as e:
            logger.error(f"Payment Creation Error: {e}")
            self.stdout.write(self.style.ERROR(f"❌ Payment Creation Exception: {e}"))
            self.send_message(chat_id, f"❌ Tizim xatosi: {str(e)[:50]}")


    def get_admin_ids(self):
        """Fetch current admin IDs from DB to ensure hot-reload"""
        config = BotConfig.objects.filter(is_active=True).first()
        if config and config.admin_chat_id:
            return [chat_id.strip() for chat_id in config.admin_chat_id.split(',') if chat_id.strip()]
        return []

    def notify_admins(self, payment, coins, total_sum, file_id, user):
        msg = (
            f"🔔 <b>Yangi To'lov!</b>\n\n"
            f"👤 <b>User:</b> {user.first_name} ({user.phone})\n"
            f"🪙 <b>Coin:</b> {coins} AC\n"
            f"💵 <b>Summa:</b> {total_sum:,.0f} so'm\n"
            f"📅 <b>Sana:</b> {timezone.localtime(payment.created_at).strftime('%d.%m.%Y %H:%M')}\n"
        )
        
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "✅ Tasdiqlash", "callback_data": f"confirm_{payment.id}"},
                    {"text": "❌ Rad etish", "callback_data": f"reject_{payment.id}"}
                ]
            ]
        }
        
        # Send to all connected admins (fetch fresh list)
        admin_chat_ids = self.get_admin_ids()
        
        admin_messages = []
        for admin_id in admin_chat_ids:
            try:
                sent_msg = self.send_photo(admin_id, file_id, caption=msg, reply_markup=keyboard)
                if sent_msg and sent_msg.get('ok'):
                    msg_data = sent_msg.get('result')
                    admin_messages.append({
                        'chat_id': str(msg_data['chat']['id']),
                        'message_id': str(msg_data['message_id'])
                    })
            except Exception as e:
                logger.error(f"Failed to send to admin {admin_id}: {e}")
        
        if admin_messages:
            payment.admin_message_ids = admin_messages
            payment.save()

    def handle_callback(self, callback):
        data = callback.get('data')
        msg = callback.get('message')
        chat_id = msg['chat']['id']
        message_id = msg['message_id']
        
        if not data: return

        try:
            action, payment_id = data.split('_')
            payment = Payment.objects.get(id=payment_id)
            
            if payment.status != 'PENDING':
                self.send_request("answerCallbackQuery", {"callback_query_id": callback['id'], "text": "Bu to'lov allaqachon yakunlangan."})
                return

            user = payment.user
            rate = Decimal(str(self.get_rate()))
            # Safe Decimal calc with rounding
            coins_amount = (Decimal(payment.amount) / rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            coins_amount_int = int(coins_amount)

            new_caption = msg.get('caption', '') + "\n\n"

            if action == 'confirm':
                from django.db import transaction
                with transaction.atomic():
                    payment.refresh_from_db()
                    if payment.status != 'PENDING':
                         self.send_request("answerCallbackQuery", {"callback_query_id": callback['id'], "text": "Bu to'lov allaqachon yakunlangan."})
                         return

                    payment.status = 'COMPLETED'
                    payment.completed_at = timezone.now()
                    payment.save()
                    
                    # Add Balance with locking to prevent race conditions
                    user = User.objects.select_for_update().get(pk=payment.user.pk)
                    old_balance = user.balance
                    
                    user.balance += coins_amount
                    user.save()
                    
                    logger.info(f"💰 [PAYMENT CONFIRM] User ID: {user.id} | Username: {user.username}")
                    logger.info(f"💰 Balance Change: {old_balance} -> {user.balance} (+{coins_amount})")
                    print(f"DEBUG: Balance Updated for {user.username}: {old_balance} -> {user.balance} (+{coins_amount})")
                
                new_caption += "✅ <b>TASDIQLANDI</b>"
                
                # Notify User
                if user.telegram_id:
                    self.send_message(user.telegram_id, f"✅ <b>To'lov tasdiqlandi!</b>\n\nHisobingizga {coins_amount_int} Coin qo'shildi.")

            elif action == 'reject':
                payment.status = 'FAILED'
                payment.save()
                
                new_caption += "❌ <b>RAD ETILDI</b>"
                
                if user.telegram_id:
                    self.send_message(user.telegram_id, "❌ <b>To'lov rad etildi.</b>\n\nChekda muammo bo'lishi mumkin. Qayta urinib ko'ring.")
            
            # Update Admin Message
            self.send_request("editMessageCaption", {
                "chat_id": chat_id,
                "message_id": message_id,
                "caption": new_caption,
                "parse_mode": "HTML",
                "reply_markup": {"inline_keyboard": []} # Properly remove buttons
            })

            self.send_request("answerCallbackQuery", {"callback_query_id": callback['id'], "text": "Bajarildi"})

        except Exception as e:
            logger.error(f"Callback Error: {e}")
            logger.error(traceback.format_exc())
            self.send_request("answerCallbackQuery", {"callback_query_id": callback['id'], "text": f"Xatolik: {str(e)[:50]}"})

    # --- HELPERS ---

    def get_rate(self):
        """Get current ArdCoin exchange rate from settings"""
        settings = PlatformSettings.objects.first()
        if settings and settings.ardcoin_exchange_rate:
            return float(settings.ardcoin_exchange_rate)
        return 1.0  # Default to 1 so'm if not set

    def handle_contact_login(self, chat_id, phone, first_name):
        """Handle contact sharing for quick login"""
        # Normalize phone
        phone = phone.replace('+', '').replace(' ', '')
        if len(phone) == 9: phone = "998" + phone
        
        # Try to find user
        user = User.objects.filter(phone__icontains=phone[-9:]).first() # Loose match
        
        if user:
            user.telegram_id = chat_id
            from django.utils import timezone
            user.telegram_connected_at = timezone.now()
            user.save()
            self.show_main_menu(chat_id, f"✅ <b>Hisob topildi va ulandi!</b>\n\nXush kelibsiz, {user.first_name}!")
        else:
            self.send_message(chat_id, f"❌ <b>Bunday raqam topilmadi ({phone}).</b>\n\nIltimos, avval saytdan ro'yxatdan o'ting.")

    def show_main_menu(self, chat_id, text):
        keyboard = {
            "keyboard": [
                [{"text": "💰 Hisobim"}, {"text": "➕ Hisob to'ldirish"}],
                [{"text": "👤 Profil"}, {"text": "Tranzaksiyalar"}]
            ],
            "resize_keyboard": True
        }
        self.send_message(chat_id, text, reply_markup=keyboard)

    def handle_location(self, chat_id, location):
        """Handle incoming location message for prizes"""
        user = User.objects.filter(telegram_id=chat_id).first()
        if not user: return

        # Find any pending or contacted winner prize
        winner_prize = WinnerPrize.objects.filter(student=user, status__in=['PENDING', 'CONTACTED']).order_by('-awarded_at').first()
        if winner_prize:
            try:
                address, _ = PrizeAddress.objects.get_or_create(prize=winner_prize)
                address.latitude = Decimal(str(location['latitude']))
                address.longitude = Decimal(str(location['longitude']))
                address.save()
                
                winner_prize.status = 'ADDRESS_RECEIVED'
                winner_prize.save()
                
                self.send_message(chat_id, "✅ <b>Lokatsiyangiz qabul qilindi!</b>\n\nSovrinni yetkazib berish jarayoni boshlandi. Adminlarimiz siz bilan bog'lanishadi.")
                self.user_states[chat_id] = {"state": STATE_NONE}
                self.show_main_menu(chat_id, "Bosh menyu:")
            except Exception as e:
                logger.error(f"Error handling location: {e}")
                self.send_message(chat_id, "❌ Lokatsiyani saqlashda xatolik yuz berdi.")
        else:
            # If no pending prize, maybe they just sent a location for no reason
            pass

    def handle_address_text(self, chat_id, text):
        """Handle incoming text address for prizes"""
        user = User.objects.filter(telegram_id=chat_id).first()
        if not user: return

        winner_prize = WinnerPrize.objects.filter(student=user, status__in=['PENDING', 'CONTACTED']).order_by('-awarded_at').first()
        if winner_prize:
            try:
                address, _ = PrizeAddress.objects.get_or_create(prize=winner_prize)
                address.address_text = text
                address.save()
                
                winner_prize.status = 'ADDRESS_RECEIVED'
                winner_prize.save()
                
                self.send_message(chat_id, "✅ <b>Manzilingiz qabul qilindi!</b>\n\nSovrinni yetkazib berish jarayoni boshlandi. Adminlarimiz siz bilan bog'lanishadi.")
                self.user_states[chat_id] = {"state": STATE_NONE}
                self.show_main_menu(chat_id, "Bosh menyu:")
            except Exception as e:
                logger.error(f"Error handling address text: {e}")
                self.send_message(chat_id, "❌ Manzilni saqlashda xatolik yuz berdi.")
        else:
            self.send_message(chat_id, "⚠️ Hozirda sizdan manzil so'ralmagan.")
            self.user_states[chat_id] = {"state": STATE_NONE}
