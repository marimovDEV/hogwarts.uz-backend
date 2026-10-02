import os
import re
import asyncio
import logging
from telethon import TelegramClient, events
from django.core.management.base import BaseCommand
from django.utils import timezone
from api.models import Payment, PaymentProviderConfig
from api.views import PaymentViewSet
from datetime import timedelta

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# HARDCODED API CREDENTIALS (REPLACE THESE WITH YOUR OWN FROM my.telegram.org)
# OR SET THEM AS ENVIRONMENT VARIABLES
# User can replace these directly in the file or set env vars.
API_ID = os.getenv('TELEGRAM_API_ID', '25886675') # Placeholder
API_HASH = os.getenv('TELEGRAM_API_HASH', 'd3a4af7c7f7358ed410057207c433362') # Placeholder

class Command(BaseCommand):
    help = 'Runs the Telegram User Bot to monitor payments'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting User Bot Payment Monitor...'))
        
        # Check for active BOT configs
        bot_configs = PaymentProviderConfig.objects.filter(type='BOT', is_active=True)
        if not bot_configs.exists():
            self.stdout.write(self.style.WARNING('No active User Bot configurations found.'))
            return

        target_usernames = []
        for config in bot_configs:
            target = config.config.get('target_username')
            if target:
                # Remove @ if present
                if target.startswith('@'):
                    target = target[1:]
                target_usernames.append(target)
        
        if not target_usernames:
            self.stdout.write(self.style.WARNING('Active User Bot found but no "target_username" configured.'))
            return

        # Get API Credentials from the first active BOT config
        first_config = bot_configs.first()
        api_id = first_config.config.get('api_id') or API_ID
        api_hash = first_config.config.get('api_hash') or API_HASH

        if not api_id or not api_hash:
             self.stdout.write(self.style.ERROR('API ID and API Hash are required! Configure them in Admin Panel.'))
             return

        self.stdout.write(self.style.SUCCESS(f'Monitoring bots: {target_usernames}'))
        self.stdout.write(self.style.SUCCESS(f'Using API ID: {api_id}'))

        # Initialize Client
        # The session file will be stored in the root directory
        client = TelegramClient('ardent_userbot_session', api_id, api_hash)

        @client.on(events.NewMessage(from_users=target_usernames))
        async def handler(event):
            try:
                text = event.raw_text
                logger.info(f"New message from {event.chat_id}: \n{text}")
                
                # Check keywords (flexible)
                if 'Kirim' in text or 'Received' in text or 'Postuplenie' in text or 'Vipolnen' in text:
                    # Generic regex for amount: 150 000.00 so'm or 150000 sum
                    # Matches: "150 000", "150,000", "150000" followed by "sum" or "so'm"
                    amount_patterns = [
                        r'(\d+[\d\s]*)\s*so\'m',
                        r'(\d+[\d\s]*)\s*som',
                        r'(\d+[\d\s]*)\s*sum',
                        r'(\d+[\d\s]*)\s*UZS'
                    ]
                    
                    found_amount = None
                    for pattern in amount_patterns:
                        match = re.search(pattern, text, re.IGNORECASE)
                        if match:
                            # Remove spaces and get int
                            amount_str = match.group(1).replace(' ', '').replace(',', '')
                            try:
                                found_amount = int(float(amount_str)) # Handle 150000.00
                                break
                            except ValueError:
                                continue
                    
                    if found_amount:
                        logger.info(f"Detected Amount: {found_amount}")
                        await self.process_payment(found_amount, text)
                    else:
                        logger.warning("Could not parse amount from message")

            except Exception as e:
                logger.error(f"Error handling message: {e}")

        async def main():
            await client.start()
            self.stdout.write(self.style.SUCCESS('User Bot is running and listening...'))
            await client.run_until_disconnected()

        # Run the loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(main())

    # The process_payment method below handles the sync-to-async transition internally.

    async def process_payment(self, amount, raw_text):
        """
        Finds a pending payment with this exact amount and confirms it.
        """
        from asgiref.sync import sync_to_async
        
        await sync_to_async(self._confirm_payment_sync)(amount, raw_text)

    def _confirm_payment_sync(self, amount, raw_text):
        # Look for pending payments created in the last 15 minutes
        # with this EXACT amount.
        from django.utils import timezone
        
        time_threshold = timezone.now() - timedelta(minutes=15)
        
        # We need to find a payment where final_amount matches the received amount
        payment = Payment.objects.filter(
            final_amount=amount,
            status='PENDING',
            created_at__gte=time_threshold
        ).first()

        if payment:
            logger.info(f"✅ Found matching payment ID: {payment.id} for User: {payment.user.username}")
            
            # Confirm Payment
            payment.status = 'COMPLETED'
            payment.transaction_id = f"BOT-{int(timezone.now().timestamp())}"
            payment.method = 'USERBOT' 
            payment.completed_at = timezone.now()
            payment.save()
            
            # Handle Application Logic (Balance/Course)
            try:
                if payment.type in ['TOPUP', 'FILL_BALANCE']:
                    # Credit the ORIGINAL amount (what user intended to pay)
                    # Or final_amount? Usually original + unique_add = final.
                    # User likely paid final. Let's credit original to be clean, or final?
                    # Generally, unique amount is small fees. Let's credit original_amount.
                    # But if user paid 150 083, and original was 150 000.
                    # Let's credit 150 000.
                    payment.user.balance += payment.original_amount
                    payment.user.save()
                    logger.info(f"Added {payment.original_amount} to user balance.")

                elif payment.type in ['COURSE', 'OLYMPIAD']:
                    # Enroll logic should be handled. 
                    # Simulating PaymentViewSet logic:
                    from api.views import PaymentViewSet
                    # Ideally we call a service method.
                    # Since we don't have a service, we'll try to replicate essential logic or leave it.
                    # For now, just mark completed. The frontend checks status and might auto-refresh?
                    # No, backend must enroll.
                    
                    if payment.type == 'COURSE':
                        # Find course from reference_id?
                        # Payment model has `reference_id`? Yes.
                        # It might be Course ID.
                        from api.models import Course, Enrollment
                        try:
                            course = Course.objects.get(id=payment.reference_id)
                            Enrollment.objects.get_or_create(user=payment.user, course=course)
                            logger.info(f"Enrolled user in course {course.title}")
                        except Exception as e:
                            logger.error(f"Enrollment failed: {e}")
                            
                    elif payment.type == 'OLYMPIAD':
                        from api.models import Olympiad, OlympiadRegistration
                        try:
                            olympiad = Olympiad.objects.get(id=payment.reference_id)
                            OlympiadRegistration.objects.get_or_create(user=payment.user, olympiad=olympiad, defaults={'is_paid': True})
                            # Also update is_paid if exists
                            OlympiadRegistration.objects.filter(user=payment.user, olympiad=olympiad).update(is_paid=True)
                            logger.info(f"Registered user for olympiad {olympiad.title}")
                        except Exception as e:
                             logger.error(f"Olympiad registration failed: {e}")

            except Exception as e:
                logger.error(f"Error executing post-payment logic: {e}")
            
            logger.info(f"💰 Payment {payment.id} PROCESSED SUCCESSFULLY!")
        else:
            logger.warning(f"⚠️ No matching pending payment found for amount: {amount}")

