from django.utils import timezone
from api.models import (
    Profession, ProfessionRoadmapStep, UserProfessionProgress,
    Enrollment, TestResult, User, Certificate
)
from django.db.models import Count

class ProfessionService:
    @staticmethod
    def update_user_profession_progress(user, profession):
        """
        Recalculates progress for a specific profession roadmap.
        Progress is based on:
        1. Mandatory roadmap steps (Courses completed, Olympiads participated)
        2. Required XP for the profession
        """
        progress_obj, _ = UserProfessionProgress.objects.get_or_create(
            user=user,
            profession=profession
        )
        
        if progress_obj.status == 'COMPLETED':
            return progress_obj

        steps = profession.roadmap_steps.all().order_by('order')
        if not steps.exists():
            return progress_obj

        mandatory_steps = steps.filter(is_mandatory=True)
        total_mandatory = mandatory_steps.count()
        completed_mandatory = 0
        
        for step in mandatory_steps:
            if step.step_type == 'LEARN' and step.course:
                # Check if course is 100% completed
                is_done = Enrollment.objects.filter(
                    user=user, 
                    course=step.course, 
                    progress__gte=100
                ).exists()
                if is_done:
                    completed_mandatory += 1
            
            elif step.step_type == 'COMPETE' and step.olympiad:
                # Check if participated/finished olympiad
                is_done = TestResult.objects.filter(
                    user=user, 
                    olympiad=step.olympiad, 
                    status='COMPLETED'
                ).exists()
                if is_done:
                    completed_mandatory += 1
                    
            elif step.step_type == 'PROJECT':
                # For now, just placeholder or check specific project submission
                # (Assuming manual/other logic marks it done)
                pass

        # Calculate percentage from steps
        step_progress = (completed_mandatory / total_mandatory * 100) if total_mandatory > 0 else 100
        
        # Check XP requirement
        xp_progress = 100
        if profession.required_xp > 0:
            user_xp_in_subject = user.xp # Or filter by subject if we track per-subject XP
            xp_progress = (user_xp_in_subject / profession.required_xp * 100)
            xp_progress = min(100, xp_progress)

        # Final progress is a blend (e.g. 80% steps, 20% total subject XP)
        # Or just min() to ensure both are met
        final_progress = int(min(step_progress, xp_progress))
        
        progress_obj.progress_percent = final_progress
        
        if final_progress >= 100 and progress_obj.status != 'COMPLETED':
            progress_obj.status = 'COMPLETED'
            progress_obj.save()
            ProfessionService._on_profession_unlocked(user, profession)
        else:
            progress_obj.save()
            
        return progress_obj

    @staticmethod
    def _on_profession_unlocked(user, profession):
        """logic to run when a user unlocks a profession"""
        from api.models import Notification
        
        # 1. Create Certificate/Badge (Placeholder for now)
        # 2. Reward bonus?
        # 3. Notify
        Notification.objects.create(
            user=user,
            title="Karyerada yangi bosqich! 🚀",
            message=f"Tabriklaymiz! Siz '{profession.name}' mutaxassisligi talablarini muvaffaqiyatli bajardingiz.",
            notification_type='ACHIEVEMENT',
            link=f"/profession/{profession.id}"
        )

    @staticmethod
    def update_all_active_professions(user):
        """Update progress for all professions the user is following"""
        active_professions = UserProfessionProgress.objects.filter(user=user, status='FOLLOWING')
        for prog in active_professions:
            ProfessionService.update_user_profession_progress(user, prog.profession)
