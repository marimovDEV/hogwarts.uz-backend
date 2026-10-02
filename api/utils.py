import random
import string

def generate_unique_id(prefix, length=6):
    """Generate unique ID like CRT-123456"""
    chars = string.digits
    random_part = ''.join(random.choices(chars, k=length))
    return f"{prefix}-{random_part}"

def extract_youtube_id(url):
    """Extract YouTube video ID from URL"""
    if not url:
        return None
    import re
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
        r'(?:embed\/|v\/|youtu.be\/)([0-9A-Za-z_-]{11})',
        r'watch\?v=([0-9A-Za-z_-]{11})',
        r'youtube.com/shorts/([0-9A-Za-z_-]{11})',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None
