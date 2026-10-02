from django.core.management.base import BaseCommand
from django.utils import timezone
from api.models import TeacherProfile, VIPLog

class Command(BaseCommand):
    help = 'Check and expire VIP statuses for teachers'

    def handle(self, *args, **options):
        now = timezone.now()
        expired_vips = TeacherProfile.objects.filter(
            teacher_type='VIP',
            vip_expire_date__lt=now
        )
        
        count = expired_vips.count()
        for profile in expired_vips:
            old_type = profile.teacher_type
            profile.teacher_type = 'NORMAL'
            profile.save()
            
            # Log the change
            VIPLog.objects.create(
                teacher=profile.user,
                prev_type=old_type,
                new_type='NORMAL',
                reason='VIP status expired (scheduled check)'
            )
            
            self.stdout.write(self.style.SUCCESS(f'Expired VIP for {profile.user.username}'))
            
        self.stdout.write(self.style.SUCCESS(f'Successfully processed {count} expired VIPs'))
