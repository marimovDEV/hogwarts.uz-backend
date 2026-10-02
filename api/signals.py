"""
Certificate Signals - Auto-generate certificates
Triggers when course is completed or olympiad ends
"""
from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from django.utils import timezone

from .models import Certificate, Enrollment, TestResult
from .certificate_generator import generate_certificate_pdf, generate_qr_code


@receiver(post_save, sender=Certificate)
def generate_certificate_files(sender, instance, created, **kwargs):
    """
    Generate PDF and QR code when certificate is verified
    """
    # Only generate when status changes to VERIFIED and files don't exist
    if instance.status == 'VERIFIED' and not instance.pdf_file:
        try:
            # Generate PDF
            pdf_file = generate_certificate_pdf(instance)
            instance.pdf_file.save(pdf_file.name, pdf_file, save=False)
            
            # Generate QR Code
            qr_file = generate_qr_code(instance)
            instance.qr_code.save(qr_file.name, qr_file, save=False)
            
            # Save without triggering signal again
            Certificate.objects.filter(pk=instance.pk).update(
                pdf_file=instance.pdf_file,
                qr_code=instance.qr_code
            )
        except Exception as e:
            print(f"Error generating certificate files: {e}")


def create_course_certificate(enrollment):
    """
    Create a certificate when course is 100% completed
    Called from Enrollment progress update
    """
    # Check if certificate already exists
    if Certificate.objects.filter(
        user=enrollment.user,
        course=enrollment.course
    ).exists():
        return None
    
    # Calculate final grade
    from .models import LessonProgress, QuizAttempt
    from django.db.models import Avg
    
    # Average quiz score
    avg_score = QuizAttempt.objects.filter(
        user=enrollment.user,
        quiz__lesson__module__course=enrollment.course
    ).aggregate(avg=Avg('score'))['avg'] or 0
    
    grade = f"{int(avg_score)}%"
    
    # Create certificate (pending by default)
    certificate = Certificate.objects.create(
        user=enrollment.user,
        course=enrollment.course,
        cert_type='COURSE',
        grade=grade,
        score=int(avg_score),
        status='PENDING'  # Needs admin/teacher approval
    )
    
    return certificate


def create_olympiad_certificates(olympiad):
    """
    Create certificates for olympiad participants when olympiad ends
    Called when olympiad status changes to COMPLETED
    """
    from .models import TestResult, OlympiadRegistration
    
    # Get all participants with results
    results = TestResult.objects.filter(olympiad=olympiad, status='COMPLETED')
    
    certificates_created = []
    
    for result in results:
        # Skip if certificate already exists
        if Certificate.objects.filter(
            user=result.user,
            olympiad=olympiad
        ).exists():
            continue
        
        # Determine certificate type (simplified logic since rank is not in model)
        cert_type = 'OLYMPIAD'
        if result.percentage >= 90:
            cert_type = 'DIPLOMA'
        
        # Create grade text
        grade = f"{result.percentage}%"
        
        # Create certificate
        certificate = Certificate.objects.create(
            user=result.user,
            olympiad=olympiad,
            cert_type=cert_type,
            grade=grade,
            score=result.score,
            status='VERIFIED'  # Auto-verify for olympiad completion
        )
        
        certificates_created.append(certificate)
    
    # Also create participation certificates for those registered but without results
    registrations = OlympiadRegistration.objects.filter(
        olympiad=olympiad
    ).exclude(
        user__in=[r.user for r in results]
    )
    
    for reg in registrations:
        if Certificate.objects.filter(
            user=reg.user,
            olympiad=olympiad
        ).exists():
            continue
        
        certificate = Certificate.objects.create(
            user=reg.user,
            olympiad=olympiad,
            cert_type='OLYMPIAD',
            grade='Ishtirok etdi',
            score=0,
            status='VERIFIED'
        )
        certificates_created.append(certificate)
    
    return certificates_created


# ==================== ENROLLMENT COMPLETION TRACKING ====================

@receiver(post_save, sender='api.Enrollment')
def check_course_completion(sender, instance, **kwargs):
    """
    Check if course is completed and create certificate
    """
    if instance.progress >= 100:
        # Mark as completed
        if not instance.completed_at:
            from .models import Enrollment
            Enrollment.objects.filter(pk=instance.pk).update(
                completed_at=timezone.now()
            )
        
        # Create certificate
        create_course_certificate(instance)


@receiver(pre_save, sender='api.Olympiad')
def olympiad_status_change(sender, instance, **kwargs):
    """
    Detect if olympiad status changed to COMPLETED
    """
    if instance.pk:
        try:
            old_instance = sender.objects.get(pk=instance.pk)
            if old_instance.status != 'COMPLETED' and instance.status == 'COMPLETED':
                # Olympiad just finished
                # We use a bit of delay or call it directly
                # For safety in pre_save, we might want to use a transaction.on_commit
                # but for simplicity we call it here (assuming save succeeds)
                create_olympiad_certificates(instance)
        except sender.DoesNotExist:
            pass
    elif instance.status == 'COMPLETED':
        # Rare case of creating as completed
        create_olympiad_certificates(instance)


@receiver(post_save, sender='api.Lesson')
@receiver(post_delete, sender='api.Lesson')
def update_course_stats(sender, instance, **kwargs):
    """
    Update lessons_count and duration for a Course when a Lesson is added/deleted/updated
    """
    course = instance.course
    # Count lessons
    course.lessons_count = course.lessons.all().count()
    
    # Calculate duration
    from django.db.models import Sum
    total_sec = course.lessons.aggregate(total=Sum('video_duration'))['total'] or 0
    
    if total_sec > 0:
        hours = total_sec // 3600
        minutes = (total_sec % 3600) // 60
        if hours > 0:
            course.duration = f"{hours} soat {minutes} daqiqa"
        else:
            course.duration = f"{minutes} daqiqa"
    else:
        course.duration = "0 daqiqa"
    
    course.save(update_fields=['lessons_count', 'duration'])


@receiver(post_save, sender='api.Enrollment')
@receiver(post_delete, sender='api.Enrollment')
def update_course_students_count(sender, instance, **kwargs):
    """
    Update students_count for a Course when an Enrollment is added/deleted
    """
    course = instance.course
    course.students_count = course.enrollments.count()
    course.save(update_fields=['students_count'])
