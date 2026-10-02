import os
import sys


def main():
    import django

    sys.path.append(os.getcwd())
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()

    from api.models import Olympiad
    from api.serializers import OlympiadSerializer
    from rest_framework.test import APIRequestFactory

    factory = APIRequestFactory()
    request = factory.get('/')

    olympiads = Olympiad.objects.all()
    print(f"Total olympiads: {olympiads.count()}")

    for oly in olympiads:
        try:
            print(f"Testing Olympiad ID: {oly.id} - {oly.title}")
            serializer = OlympiadSerializer(oly, context={'request': request})
            serializer.data
            print(f"Successfully serialized ID {oly.id}")
        except Exception as exc:
            print(f"FAILED for ID {oly.id}: {str(exc)}")
            import traceback
            traceback.print_exc()


if __name__ == '__main__':
    main()
