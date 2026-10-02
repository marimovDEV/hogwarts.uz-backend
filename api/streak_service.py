from django.utils import timezone
from datetime import timedelta
from .models import UserStreak, ActivityLog

class StreakService:
    @staticmethod
    def get_user_streak(user):
        """Get or create user streak"""
        streak, created = UserStreak.objects.get_or_create(user=user)
        return streak

    @staticmethod
    def record_activity(user, activity_type, description="", points=0):
        """
        Record user activity and update streak.
        Returns: (is_streak_updated: bool, streak_info: dict)
        """
        # Log activity
        ActivityLog.objects.create(
            user=user,
            activity_type=activity_type,
            description=description,
            points_earned=points
        )

        streak = StreakService.get_user_streak(user)
        today = timezone.localdate()
        last_date = streak.last_activity_date
        
        updated = False
        message = ""

        # Logic
        if last_date == today:
            # Already active today
            return False, {"streak": streak.current_streak, "message": "Already active today"}
        
        if last_date == today - timedelta(days=1):
            # Consecutive day
            streak.current_streak += 1
            updated = True
            message = "Streak extended!"
        elif last_date is None:
            # First ever activity
            streak.current_streak = 1
            updated = True
            message = "Streak started!"
        else:
            # Missed a day
            days_missed = (today - last_date).days
            
            # Use freezes if available
            needed_freezes = days_missed - 1
            
            if 0 < needed_freezes <= streak.freeze_count:
                streak.freeze_count -= needed_freezes
                streak.current_streak += 1 # Extend streak as if no break
                updated = True
                message = f"Streak saved! Used {needed_freezes} streak freeze(s)."
            else:
                # Reset
                streak.current_streak = 1
                updated = True
                message = "Streak reset."

        # Update max streak
        if streak.current_streak > streak.max_streak:
            streak.max_streak = streak.current_streak

        streak.last_activity_date = today
        streak.save()
        
        # Check for Freezes reward (e.g. every 7 days)
        if streak.current_streak % 7 == 0 and updated:
             streak.freeze_count += 1
             streak.save()
             message += " +1 Streak Freeze earned!"

        return updated, {
            "streak": streak.current_streak,
            "max_streak": streak.max_streak,
            "freeze_count": streak.freeze_count,
            "message": message
        }
