
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from api.models import LevelReward

rewards = [
    (1, 500, "Boshlang'ich", "Award"),
    (2, 1000, "Bronza Nishoni", "Medal"),
    (3, 1500, "5% Chegirma Kupon", "Ticket"),
    (4, 2000, "Kumush Nishoni", "Medal"),
    (5, 2500, "1000 ArdCoin Bonus", "Coins"),
    (6, 3000, "Oltin Nishoni", "Trophy"),
    (7, 3500, "Premium Kursga Kirish", "Unlock"),
    (8, 4000, "Ekspert Maqomi", "Star"),
    (9, 4500, "10% Chegirma Kupon", "Ticket"),
    (10, 5000, "Grandmaster Kubogi", "Crown"),
]

for level, xp, desc, icon in rewards:
    LevelReward.objects.get_or_create(
        level=level,
        defaults={
            'xp_threshold': xp,
            'reward_description': desc,
            'icon': icon
        }
    )
    print(f"Level {level} reward set: {desc}")

print("Done!")
