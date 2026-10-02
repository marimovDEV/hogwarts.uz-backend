import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ardent.settings')
django.setup()

from api.models import User, Payment

def debug():
    print("--- Checking Latest Completed Payments ---")
    latest_payments = Payment.objects.filter(status='COMPLETED').order_by('-completed_at')[:5]
    for p in latest_payments:
        print(f"Payment ID: {p.id}")
        print(f"User: {p.user.username} (ID: {p.user.id})")
        print(f"Amount: {p.amount}")
        print(f"Balance: {p.user.balance}")
        print(f"Completed At: {p.completed_at}")
        print("-" * 30)

if __name__ == "__main__":
    debug()
