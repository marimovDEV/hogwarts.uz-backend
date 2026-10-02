from django.db import transaction
from django.utils import timezone
from decimal import Decimal
import logging

from ..models import (
    Olympiad, 
    TestResult, 
    OlympiadPrize, 
    WinnerPrize, 
    Transaction, 
    User,
    PrizeAddress
)
from ..bot_service import BotService

logger = logging.getLogger(__name__)

class RewardService:
    """
    Service for automated Olympiad ranking calculation and reward distribution.
    """

    @staticmethod
    def calculate_rankings(olympiad):
        """
        Sort participants by score (desc) and time taken (asc).
        Returns list of (User, TestResult, position)
        """
        # Get only completed results that are not disqualified
        results = TestResult.objects.filter(
            olympiad=olympiad,
            status='COMPLETED'
        ).select_related('user').order_by('-score', 'time_taken')

        rankings = []
        for i, result in enumerate(results):
            rankings.append({
                'user': result.user,
                'result': result,
                'position': i + 1
            })
        
        return rankings

    @classmethod
    @transaction.atomic
    def distribute_rewards(cls, olympiad_id):
        """
        Main runner for distributing rewards for a finished olympiad.
        """
        try:
            olympiad = Olympiad.objects.get(id=olympiad_id)
            
            if olympiad.reward_distribution_status == 'COMPLETED':
                logger.warning(f"Rewards already distributed for Olympiad {olympiad_id}")
                return False

            olympiad.reward_distribution_status = 'IN_PROGRESS'
            olympiad.save()

            rankings = cls.calculate_rankings(olympiad)
            prizes = olympiad.prizes.all()

            if not prizes.exists():
                logger.info(f"No prizes defined for Olympiad {olympiad_id}")
                olympiad.reward_distribution_status = 'COMPLETED'
                olympiad.save()
                return True

            distributed_count = 0

            # Determine distribution logic based on strategy
            if olympiad.reward_strategy == 'TOP_N':
                for rank in rankings:
                    # Find prizes for this position
                    pos_prizes = prizes.filter(target_value=rank['position'])
                    for prize in pos_prizes:
                        cls.award_prize(rank['user'], prize, olympiad, rank['position'])
                        distributed_count += 1
            
            elif olympiad.reward_strategy == 'THRESHOLD':
                for rank in rankings:
                    # Find prizes where person's score percentage >= target_value
                    # e.g. prize target_value=90 means 90% and above
                    eligible_prizes = prizes.filter(target_value__lte=rank['result'].percentage)
                    for prize in eligible_prizes:
                        cls.award_prize(rank['user'], prize, olympiad, rank['position'])
                        distributed_count += 1

            olympiad.reward_distribution_status = 'COMPLETED'
            olympiad.save()
            
            logger.info(f"Successfully distributed {distributed_count} rewards for Olympiad {olympiad_id}")
            return True

        except Exception as e:
            logger.error(f"Error distributing rewards for Olympiad {olympiad_id}: {e}")
            if 'olympiad' in locals():
                olympiad.reward_distribution_status = 'FAILED'
                olympiad.save()
            return False

    @classmethod
    def award_prize(cls, user, prize, olympiad, position):
        """
        Award a specific prize to a user.
        """
        if prize.prize_type == 'COIN':
            cls._award_coin(user, prize.amount, olympiad)
        elif prize.prize_type == 'XP':
            cls._award_xp(user, int(prize.amount), olympiad)
        elif prize.prize_type == 'PHYSICAL':
            cls._award_physical(user, prize, olympiad, position)

    @staticmethod
    def _award_coin(user, amount, olympiad):
        """Add balance and record transaction"""
        amount = Decimal(str(amount))
        user.balance += amount
        user.save()

        Transaction.objects.create(
            user=user,
            transaction_type='OLYMPIAD_REWARD',
            amount=amount,
            status='SUCCESS',
            description=f"Reward for {olympiad.title}"
        )
        
        # Notify via Telegram if possible
        if user.telegram_id:
            text = f"🎉 <b>Tabriklaymiz!</b>\n\nSiz <b>{olympiad.title}</b> olimpiadasida g'olib bo'ldingiz va <b>{int(amount)} Coin</b> yutib oldingiz! 🪙\n\nHisobingiz to'ldirildi."
            BotService.send_message(user.telegram_id, text)

    @staticmethod
    def _award_xp(user, amount, olympiad):
        """Add XP to user"""
        user.xp += amount
        # Simple level up logic if needed, but assuming user model handles it or it's simple
        user.save()
        
        # Notify via Telegram if possible
        if user.telegram_id:
            text = f"🎉 <b>Tabriklaymiz!</b>\n\nSiz <b>{olympiad.title}</b> olimpiadasida muvaffaqiyatli qatnashdingiz va <b>{amount} XP</b> tajriba balliga ega bo'ldingiz! 🚀"
            BotService.send_message(user.telegram_id, text)

    @staticmethod
    def _award_physical(user, prize_item, olympiad, position):
        """Create WinnerPrize and trigger bot location request"""
        # check if already awarded
        if WinnerPrize.objects.filter(olympiad=olympiad, student=user).exists():
            return

        winner_prize = WinnerPrize.objects.create(
            olympiad=olympiad,
            student=user,
            position=position,
            prize_item=prize_item,
            status='PENDING'
        )
        
        # Initialize address
        PrizeAddress.objects.create(prize=winner_prize)

        # Notify via Telegram and request location
        BotService.notify_winner(winner_prize)
