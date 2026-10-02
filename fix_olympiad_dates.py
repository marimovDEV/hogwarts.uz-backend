
import os
import django
import sys
from datetime import timedelta

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from api.models import Olympiad
from django.utils import timezone

# IDs from debug output: 1 and 9 are CHECKING
ids_to_fix = [1, 9]

print(f"Current Time: {timezone.now()}")

for oid in ids_to_fix:
    try:
        olym = Olympiad.objects.get(id=oid)
        print(f"Updating Olympiad {oid}: {olym.title}")
        print(f"  Old Status: {olym.status}")
        print(f"  Old End Date: {olym.end_date}")
        
        # Extend to Feb 20, 2026 (or just +20 days from now)
        new_end_date = timezone.now() + timedelta(days=20)
        olym.end_date = new_end_date
        olym.status = 'ONGOING' # Force status update
        olym.is_active = True
        olym.save()
        
        print(f"  New Status: {olym.status}")
        print(f"  New End Date: {olym.end_date}")
        print("-" * 30)
        
    except Olympiad.DoesNotExist:
        print(f"Olympiad {oid} not found!")

print("Done. Please check the Home Page.")
