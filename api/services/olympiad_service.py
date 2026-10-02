from django.utils import timezone
from api.models import Olympiad, OlympiadRegistration, TestResult, Question, User

from django.db import transaction
from rest_framework.exceptions import ValidationError

class OlympiadService:
    
    @staticmethod
    def register_user(user, olympiad):
        """Register user for olympiad (handle payment & limits)"""
        if OlympiadRegistration.objects.filter(user=user, olympiad=olympiad).exists():
            raise ValidationError("error.already_registered")
            
        if olympiad.max_participants and olympiad.participants_count >= olympiad.max_participants:
            raise ValidationError("error.full")
            
        if olympiad.price > 0:
            if user.balance < olympiad.price:
                raise ValidationError("error.insufficient_balance")
            pass
            
        registration = OlympiadRegistration.objects.create(
            user=user, 
            olympiad=olympiad,
            is_paid=(olympiad.price == 0)
        )
        
        # Telegram Notification
        if user.telegram_id:
            from api.telegram_service import TelegramService
            msg = (
                f"✅ <b>Muvaffaqiyatli ro'yxatdan o'tdingiz!</b>\n\n"
                f"🏆 Olimpiada: {olympiad.title}\n"
                f"📅 Boshlanish vaqti: {olympiad.start_date.strftime('%Y-%m-%d %H:%M')}\n\n"
                f"Olimpiada boshlanishidan 1 soat oldin eslatma yuboramiz."
            )
            TelegramService.send_message(str(user.telegram_id), msg)
            
        return registration

    @staticmethod
    def start_test(user, olympiad_id):
        """Start the test attempt"""
        olympiad = Olympiad.objects.get(id=olympiad_id)
        
        # Check active window (skip if admin set status to ONGOING manually)
        now = timezone.now()
        if olympiad.status != 'ONGOING':
            if now < olympiad.start_date:
                raise ValidationError("error.not_started")
            if olympiad.end_date and now > olympiad.end_date:
                raise ValidationError("error.finished")
            
        # Check registration
        if not OlympiadRegistration.objects.filter(user=user, olympiad=olympiad).exists():
            raise ValidationError("error.not_registered")
            
        # Check existing attempt
        attempt = TestResult.objects.filter(user=user, olympiad=olympiad).first()
        
        if attempt:
            if attempt.status == 'COMPLETED':
                if olympiad.max_attempts > 1:
                    # Allow re-take by deleting old result (satisfies unique_together)
                    attempt.delete()
                    attempt = TestResult.objects.create(user=user, olympiad=olympiad, status='IN_PROGRESS')
                else:
                    raise ValidationError("error.already_submitted")
            else:
                # IN_PROGRESS: check if timer expired and reset if needed
                duration_minutes = olympiad.duration if isinstance(olympiad.duration, (int, float)) else 120
                duration_seconds = duration_minutes * 60
                elapsed = (timezone.now() - attempt.submitted_at).total_seconds()
                if elapsed > duration_seconds:
                    # Timer expired — delete old and create fresh attempt
                    attempt.delete()
                    attempt = TestResult.objects.create(user=user, olympiad=olympiad, status='IN_PROGRESS')
        else:
            attempt = TestResult.objects.create(user=user, olympiad=olympiad, status='IN_PROGRESS')
            
        return attempt

    @staticmethod
    def submit_answer(user, olympiad_id, question_id, answer_value):
        """Submit single answer (incremental save)"""
        attempt = TestResult.objects.get(user=user, olympiad_id=olympiad_id)
        
        if attempt.status == 'COMPLETED':
            raise ValidationError("error.already_submitted")
            
        attempt.answers[str(question_id)] = answer_value
        attempt.save()
        return attempt

    @staticmethod
    def finish_test(user, olympiad_id, reason="manual"):
        """Finish test and calculate score"""
        attempt = TestResult.objects.get(user=user, olympiad_id=olympiad_id)
        
        if attempt.status == 'COMPLETED':
            return attempt
            
        olympiad = attempt.olympiad
        questions = olympiad.questions.all()
        
        score = 0
        total_points = 0
        
        for q in questions:
            total_points += q.points
            user_ans = attempt.answers.get(str(q.id))
            
            if not user_ans:
                continue
                
            if q.type == 'MCQ':
                if str(user_ans) == str(q.correct_answer):
                    score += q.points
            elif q.type == 'NUMERIC':
                 if str(user_ans).strip() == str(q.correct_answer).strip():
                    score += q.points
                
        # Calculate stats
        percentage = round((score / total_points * 100), 2) if total_points > 0 else 0
        attempt.score = score
        attempt.percentage = percentage
        attempt.time_taken = (timezone.now() - attempt.submitted_at).seconds # Approximate
        attempt.status = 'COMPLETED'
        attempt.save()
        
        # Rewards (XP, Coins)
        if olympiad.xp_reward > 0:
            user.add_xp(olympiad.xp_reward, 'OLYMPIAD_PARTICIPATION', f"Olimpiada yakunlandi: {olympiad.title}")
        
        # Bonus XP for high performance (optional, keeping it as 2x score if preferred, 
        # but user asked for 150 fixed for participation. Let's stick to user's 150)
        # user.add_xp(int(score) * 2, ...)  # Removed this to strictly follow requested values
        
        # Record Streak Activity
        from api.streak_service import StreakService
        StreakService.record_activity(user, 'OLYMPIAD_PARTICIPATION', f"Olimpiada topshirildi: {olympiad.title}")

        # Update Career Progress
        from api.services.profession_service import ProfessionService
        ProfessionService.update_all_active_professions(user)

        # 🚀 HOGWORDS CAREER ENGINE HOOK: Auto-complete Olympiad Nodes
        try:
            from api.models import ProfessionNode, UserProfessionState
            from api.services.career_engine_service import CareerEngineService
            
            # Get all active profession states for the user
            active_states = UserProfessionState.objects.filter(user=user, status='active')
            for state in active_states:
                if state.current_level:
                    # Find if there's an olympiad node in the current level for this olympiad
                    nodes = state.current_level.nodes.filter(
                        node_type='olympiad', 
                        reference_id=olympiad.id
                    )
                    for node in nodes:
                        try:
                            # Pass the actual score percentage achieved as the node score
                            CareerEngineService.complete_node(user, node, score=int(percentage))
                        except Exception as e:
                            print(f"CareerEngine Error completing olympiad node: {e}")
        except Exception as e:
            print(f"CareerEngine Error: {e}")

        # Telegram Notification
        if user.telegram_id:
            from api.telegram_service import TelegramService
            msg = (
                f"🏁 <b>{olympiad.title} yakunlandi!</b>\n\n"
                f"📊 Natijangiz: {score} ball ({percentage:.1f}%)\n"
                f"⏱ Vaqt: {attempt.time_taken // 60} daqiqa\n\n"
                f"Batafsil tahlilni saytda ko'rishingiz mumkin."
            )
            TelegramService.send_message(str(user.telegram_id), msg)

        return attempt

    @staticmethod
    def notify_participants_olympiad_start(olympiad):
        """Notify all registered participants that the olympiad has started"""
        from api.bot_service import BotService
        
        registrations = OlympiadRegistration.objects.filter(olympiad=olympiad)
        count = 0
        for reg in registrations:
            if reg.user.telegram_id:
                if BotService.notify_olympiad(reg.user, olympiad, message_type="start"):
                    count += 1
        return count

    @staticmethod
    def publish_results(olympiad_id):
        """
        Publish results and distribute rewards if auto_reward is enabled.
        """
        from api.services.reward_service import RewardService
        
        olympiad = Olympiad.objects.get(id=olympiad_id)
        olympiad.status = 'PUBLISHED'
        olympiad.result_time = timezone.now()
        olympiad.save()
        
        if olympiad.auto_reward:
            # Trigger reward distribution
            RewardService.distribute_rewards(olympiad.id)
            
        return olympiad
