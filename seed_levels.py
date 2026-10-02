
import os
import django
import sys

# Setup django
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from api.models import LevelReward

def seed_levels():
    levels = [
        {
            'level': 1,
            'xp_threshold': 0,
            'reward_description': "50 AC + Boshlovchi nishoni",
            'icon': 'Award'
        },
        {
            'level': 2,
            'xp_threshold': 500,
            'reward_description': "50 AC",
            'icon': 'Zap'
        },
        {
            'level': 3,
            'xp_threshold': 1200,
            'reward_description': "Maxsus Sertifikat Dizayni",
            'icon': 'Gift'
        },
        {
            'level': 4,
            'xp_threshold': 2000,
            'reward_description': "Bilimdon Badge",
            'icon': 'Star'
        },
        {
            'level': 5,
            'xp_threshold': 3500,
            'reward_description': "Bepul Olimpiada Ishtiroki",
            'icon': 'Trophy'
        },
        {
            'level': 6,
            'xp_threshold': 5000,
            'reward_description': "10,000 AC Bonus",
            'icon': 'Coins'
        },
        {
            'level': 7,
            'xp_threshold': 7500,
            'reward_description': "Yopiq darslarga ruxsat",
            'icon': 'Unlock'
        },
        {
            'level': 10,
            'xp_threshold': 20000,
            'reward_description': "Afsonaviy sertifikat 👑",
            'icon': 'Crown'
        },
    ]

    print("🚀 Seeding Level Rewards...")
    for lvl_data in levels:
        reward, created = LevelReward.objects.get_or_create(
            level=lvl_data['level'],
            defaults={
                'xp_threshold': lvl_data['xp_threshold'],
                'reward_description': lvl_data['reward_description'],
                'icon': lvl_data['icon']
            }
        )
        if created:
            print(f"✅ Created Level {reward.level}")
        else:
            reward.xp_threshold = lvl_data['xp_threshold']
            reward.reward_description = lvl_data['reward_description']
            reward.icon = lvl_data['icon']
            reward.save()
            print(f"ℹ️ Updated Level {reward.level}")

    print("✨ Seeding Complete!")

if __name__ == "__main__":
    seed_levels()
