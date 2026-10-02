import logging
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from ..models import Notification, User, NotificationBroadcast, Enrollment, OlympiadRegistration
from ..bot_service import BotService

logger = logging.getLogger(__name__)

class NotificationService:
    """
    Central Service for sending notifications via multiple channels
    """

    @staticmethod
    def create_notification(user, title, message, notification_type='SYSTEM', channel='WEB', link=None, broadcast=None):
        """
        Create a notification (Web) and optionally send to other channels (Telegram, SMS)
        """
        try:
            # 1. Always create DB record (Web Notification)
            # Even if channel is TELEGRAM, we store history in DB
            notification = Notification.objects.create(
                user=user,
                title=title,
                message=message,
                notification_type=notification_type,
                channel=channel,
                link=link,
                broadcast=broadcast,
                is_read=False
            )

            # 2. Handle Telegram
            if channel in ['TELEGRAM', 'ALL'] or notification_type in ['STREAK', 'OLYMPIAD']:
                if user.telegram_id:
                    # Format message slightly for formatting
                    tg_text = f"<b>{title}</b>\n\n{message}"
                    if link:
                        tg_text += f"\n\n<a href='{link}'>Batafsil</a>"
                    
                    BotService.send_message(user.telegram_id, tg_text)
                else:
                    logger.warning(f"Cannot send Telegram notification to {user}: No Telegram ID linked.")

            # 3. Handle SMS (Stub)
            if channel in ['SMS', 'ALL']:
                if user.phone:
                    # SMS sending logic would go here
                    pass

            return notification

        except Exception as e:
            logger.error(f"Error creating notification for {user}: {e}")
            return None

    @staticmethod
    def mark_as_read(notification_id, user):
        try:
            notification = Notification.objects.get(id=notification_id, user=user)
            notification.is_read = True
            notification.save()
            return True
        except Notification.DoesNotExist:
            return False

    @staticmethod
    def mark_all_as_read(user):
        Notification.objects.filter(user=user, is_read=False).update(is_read=True)

    @staticmethod
    def broadcast_notification(broadcast_id):
        """
        Process a mass notification broadcast
        """
        try:
            broadcast = NotificationBroadcast.objects.get(id=broadcast_id)
            broadcast.status = 'IN_PROGRESS'
            broadcast.save(update_fields=['status'])

            targets = User.objects.filter(is_active=True)
            
            if broadcast.audience_type == 'STUDENTS':
                targets = targets.filter(role='STUDENT')
            elif broadcast.audience_type == 'TEACHERS':
                targets = targets.filter(role='TEACHER')
            elif broadcast.audience_type == 'COURSE_STUDENTS' and broadcast.course:
                user_ids = Enrollment.objects.filter(course=broadcast.course).values_list('user_id', flat=True)
                targets = targets.filter(id__in=user_ids)
            elif broadcast.audience_type == 'OLYMPIAD_PARTICIPANTS' and broadcast.olympiad:
                user_ids = OlympiadRegistration.objects.filter(olympiad=broadcast.olympiad).values_list('user_id', flat=True)
                targets = targets.filter(id__in=user_ids)
            elif broadcast.audience_type == 'INACTIVE':
                seven_days_ago = timezone.now() - timedelta(days=7)
                targets = targets.filter(last_active_at__lt=seven_days_ago)
            elif broadcast.audience_type == 'NEW':
                one_day_ago = timezone.now() - timedelta(days=1)
                targets = targets.filter(date_joined__gt=one_day_ago)

            count = 0
            for user in targets:
                # Check user preferences if implemented
                # if not user.notification_settings.get('web_enabled', True): continue

                NotificationService.create_notification(
                    user=user,
                    title=broadcast.title,
                    message=broadcast.message,
                    notification_type=broadcast.notification_type,
                    channel=broadcast.channel,
                    link=broadcast.link,
                    broadcast=broadcast
                )
                count += 1

            broadcast.status = 'SENT'
            broadcast.sent_at = timezone.now()
            broadcast.total_recipients = count
            broadcast.save(update_fields=['status', 'sent_at', 'total_recipients'])
            
            return count

        except Exception as e:
            logger.error(f"Error in broadcast {broadcast_id}: {e}")
            if 'broadcast' in locals():
                broadcast.status = 'FAILED'
                broadcast.save(update_fields=['status'])
            return 0
