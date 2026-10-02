
import os
import django
import sys

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from api.models import Olympiad
from django.utils import timezone

print(f"Current Time: {timezone.now()}")
print("-" * 50)
print(f"{'ID':<4} | {'Title':<30} | {'Status':<12} | {'Start Date':<25} | {'End Date':<25} | {'Is Active':<10}")
print("-" * 80)

olympiads = Olympiad.objects.all().order_by('-created_at')

for olym in olympiads:
    print(f"{olym.id:<4} | {olym.title[:30]:<30} | {olym.status:<12} | {str(olym.start_date):<25} | {str(olym.end_date):<25} | {olym.is_active:<10}")

print("-" * 50)
print("Possible Statuses:", ['DRAFT', 'PUBLISHED', 'UPCOMING', 'ONGOING', 'COMPLETED', 'CANCELED', 'PAUSED'])
