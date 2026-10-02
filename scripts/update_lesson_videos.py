import os
import django
import sys

# Add the project root to sys.path
sys.path.append('/Users/ogabek/Documents/projects/ardent olimpiada/backend')

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from api.models import Lesson

def update_videos():
    DEFAULT_YOUTUBE_ID = '_GjgFMGQg40'
    
    print(f"Updating all lessons to use YouTube ID: {DEFAULT_YOUTUBE_ID}...")
    
    updated_count = Lesson.objects.all().update(
        youtube_id=DEFAULT_YOUTUBE_ID,
        video_type='YOUTUBE',
        video_url=None
    )
    
    print(f"Successfully updated {updated_count} lessons.")

if __name__ == "__main__":
    update_videos()
