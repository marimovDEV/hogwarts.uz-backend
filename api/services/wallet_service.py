from django.conf import settings
from django.utils import timezone
from django.db import transaction
from datetime import timedelta
from decimal import Decimal

from ..models import TeacherWallet, Transaction, Payout, Course, User


class WalletService:
    """Service for managing teacher wallet operations"""
    
    @staticmethod
    def get_or_create_wallet(teacher):
        """Get or create teacher wallet"""
        wallet, created = TeacherWallet.objects.get_or_create(teacher=teacher)
        return wallet
    
    @staticmethod
    def calculate_commission(amount):
        """
        Split amount into admin and teacher shares
        Returns: (admin_share, teacher_share)
        """
        admin_rate = getattr(settings, 'PLATFORM_COMMISSION_RATE', Decimal('0.30'))
        teacher_rate = getattr(settings, 'TEACHER_COMMISSION_RATE', Decimal('0.70'))
        
        amount = Decimal(str(amount))
        admin_share = amount * admin_rate
        teacher_share = amount * teacher_rate
        
        return (admin_share, teacher_share)
    
    @staticmethod
    @transaction.atomic
    def add_pending_balance(teacher, amount, course, description):
        """
        Add amount to teacher's pending balance after course sale
        Funds will be locked for PENDING_BALANCE_DAYS before becoming available
        """
        wallet = WalletService.get_or_create_wallet(teacher)
        
        amount = Decimal(str(amount))
        wallet.pending_balance += amount
        wallet.total_earned += amount
        wallet.save()
        
        # Create transaction record
        trans = Transaction.objects.create(
            transaction_type='COURSE_SALE',
            user=teacher,
            course=course,
            amount=amount,
            status='SUCCESS',
            description=description
        )
        
        return trans
    
    @staticmethod
    @transaction.atomic
    def release_pending_balance():
        """
        Cron job: Move pending balance to available balance
        after PENDING_BALANCE_DAYS have passed
        
        Returns: Number of wallets updated
        """
        pending_days = getattr(settings, 'PENDING_BALANCE_DAYS', 7)
        cutoff_date = timezone.now() - timedelta(days=pending_days)
        
        # Find transactions that are old enough
        old_transactions = Transaction.objects.filter(
            transaction_type='COURSE_SALE',
            status='SUCCESS',
            created_at__lte=cutoff_date
        ).select_related('user', 'user__teacher_wallet')
        
        updated_count = 0
        
        for trans in old_transactions:
            if hasattr(trans.user, 'teacher_wallet'):
                wallet = trans.user.teacher_wallet
                
                # Move from pending to available
                if wallet.pending_balance >= trans.amount:
                    wallet.pending_balance -= trans.amount
                    wallet.balance += trans.amount
                    wallet.save()
                    updated_count += 1
        
        return updated_count
    
    @staticmethod
    @transaction.atomic
    def process_payout(payout_id, admin):
        """
        Process payout request - deduct from teacher balance
        and mark payout as approved
        """
        payout = Payout.objects.select_for_update().get(id=payout_id)
        
        if payout.status != 'REQUESTED':
            raise ValueError(f"Payout is already {payout.status}")
        
        wallet = WalletService.get_or_create_wallet(payout.teacher)
        
        if wallet.balance < payout.amount:
            raise ValueError("Insufficient balance")
        
        # Deduct from balance
        wallet.balance -= payout.amount
        wallet.total_withdrawn += payout.amount
        wallet.save()
        
        # Update payout status
        payout.status = 'APPROVED'
        payout.approved_by = admin
        payout.approved_at = timezone.now()
        payout.save()
        
        # Create transaction record
        Transaction.objects.create(
            transaction_type='PAYOUT',
            user=payout.teacher,
            amount=-payout.amount,  # Negative for withdrawal
            status='SUCCESS',
            description=f"Payout {payout.id} approved"
        )
        
        return payout
    
    @staticmethod
    def mark_payout_paid(payout_id):
        """Mark payout as paid (after manual bank transfer)"""
        payout = Payout.objects.get(id=payout_id)
        payout.status = 'PAID'
        payout.paid_at = timezone.now()
        payout.save()
        return payout
    
    @staticmethod
    def reject_payout(payout_id, admin, reason):
        """
        Reject payout request and return balance to teacher
        """
        with transaction.atomic():
            payout = Payout.objects.select_for_update().get(id=payout_id)
            
            if payout.status == 'APPROVED':
                # Return money to wallet if already deducted
                wallet = payout.teacher.teacher_wallet
                wallet.balance += payout.amount
                wallet.total_withdrawn -= payout.amount
                wallet.save()
            
            payout.status = 'REJECTED'
            payout.rejection_reason = reason
            payout.approved_by = admin
            payout.approved_at = timezone.now()
            payout.save()
            
            return payout
    
    @staticmethod
    @transaction.atomic
    def create_course_creation_transaction(teacher, course_id, payment_provider, payment_id):
        """
        Record course creation fee payment
        """
        creation_fee = getattr(settings, 'COURSE_CREATION_FEE', 50000)
        
        trans = Transaction.objects.create(
            transaction_type='COURSE_CREATION_FEE',
            user=teacher,
            course_id=course_id,
            amount=creation_fee,
            status='SUCCESS',
            payment_provider=payment_provider,
            payment_id=payment_id,
            description=f"Course creation fee for course {course_id}"
        )
        
        # Update course
        course = Course.objects.get(id=course_id)
        course.creation_fee_paid = True
        course.creation_fee_transaction = trans
        course.save()
        
        return trans
