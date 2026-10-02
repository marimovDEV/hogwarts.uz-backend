from django.utils import timezone
from api.models import (
    Profession, ProfessionLevel, ProfessionNode,
    UserProfessionState, UserNodeProgress, User, Notification
)

class CareerEngineService:
    @staticmethod
    def get_or_create_state(user, profession):
        state, created = UserProfessionState.objects.get_or_create(
            user=user, profession=profession
        )
        if created:
            # Assign first level if exists
            first_level = profession.levels.order_by('order').first()
            if first_level:
                state.current_level = first_level
                state.status = 'active'
                state.save()
        return state

    @staticmethod
    def complete_node(user, node, score=0):
        """Marks a node as completed and triggers progression check"""
        state = CareerEngineService.get_or_create_state(user, node.level.profession)
        
        progress, created = UserNodeProgress.objects.get_or_create(
            user=user, node=node
        )
        
        if progress.status == 'completed':
            return progress, False # Already completed
            
        # Check if node can be unlocked
        if not CareerEngineService.can_unlock_node(user, node):
            raise ValueError("Tugunni ochish uchun shartlar bajarilmagan.")
            
        progress.status = 'completed'
        progress.score = score
        progress.completed_at = timezone.now()
        progress.save()
        
        # Grant XP
        xp_reward = node.xp_reward
        # Give prestige users 20% bonus XP
        # Depending on how prestige is tracked on User model, e.g. user.roles contains 'prestige' or user is in some vip logic
        has_prestige = hasattr(user, 'teacher_type') and user.teacher_type in ['VIP', 'INTERNAL']
        if has_prestige:
            xp_reward = int(xp_reward * 1.2)
            
        if xp_reward > 0:
            state.total_xp += xp_reward
            state.save()
            # Also add to generic user XP
            if hasattr(user, 'xp'):
                user.xp += xp_reward
                user.save()
            
        # Check level progression
        CareerEngineService.check_level_progression(user, state)
        
        return progress, True
        
    @staticmethod
    def can_unlock_node(user, node):
        """Evaluates JSON condition to check if node can be unlocked"""
        # If order > 0, check if previous nodes in the same level are completed (basic linearity)
        previous_nodes = ProfessionNode.objects.filter(
            level=node.level, order__lt=node.order, is_required=True
        )
        for p_node in previous_nodes:
            is_completed = UserNodeProgress.objects.filter(
                user=user, node=p_node, status='completed'
            ).exists()
            if not is_completed:
                return False
                
        # Custom JSON conditions (e.g. {"required_nodes": [id1, id2]})
        if node.unlock_condition and isinstance(node.unlock_condition, dict):
            req_nodes = node.unlock_condition.get('required_nodes', [])
            for n_id in req_nodes:
                is_completed = UserNodeProgress.objects.filter(
                    user=user, node_id=n_id, status='completed'
                ).exists()
                if not is_completed:
                    return False
                    
        return True

    @staticmethod
    def check_level_progression(user, state):
        current_level = state.current_level
        if not current_level:
            return
            
        # Check if all required nodes in current level are completed
        required_nodes = current_level.nodes.filter(is_required=True)
        all_completed = True
        for node in required_nodes:
            is_completed = UserNodeProgress.objects.filter(
                user=user, node=node, status='completed'
            ).exists()
            if not is_completed:
                all_completed = False
                break
                
        if all_completed and state.total_xp >= current_level.unlock_xp:
            # Unlock next level
            next_level = ProfessionLevel.objects.filter(
                profession=state.profession, 
                order__gt=current_level.order
            ).order_by('order').first()
            
            if next_level:
                # Check prestige condition
                has_prestige = hasattr(user, 'teacher_type') and user.teacher_type in ['VIP', 'INTERNAL']
                if next_level.is_prestige_only and not has_prestige:
                    # User needs prestige to unlock next level
                    pass
                else:
                    state.current_level = next_level
                    state.save()
                    Notification.objects.create(
                        user=user,
                        title="Yangi bosqich! 🚀",
                        message=f"{state.profession.name} kasbida '{next_level.title}' bosqichiga o'tdingiz!",
                        notification_type='SYSTEM',
                        link=f"/profession/{state.profession.slug}" if getattr(state.profession, 'slug', None) else f"/profession/{state.profession.id}"
                    )
            else:
                # No more levels = Profession Completed
                if state.status != 'completed':
                    state.status = 'completed'
                    state.save()
                    Notification.objects.create(
                        user=user,
                        title="Kasb to'liq o'zlashtirildi! 🏆",
                        message=f"Tabriklaymiz! Siz {state.profession.name} kasbini to'liq tugatdingiz.",
                        notification_type='ACHIEVEMENT',
                        link=f"/profession/{state.profession.slug}" if getattr(state.profession, 'slug', None) else f"/profession/{state.profession.id}"
                    )
