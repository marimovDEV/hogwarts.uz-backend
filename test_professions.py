import os


def main():
    import django

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()

    from api.models import Profession
    from api.serializers import ProfessionSerializer

    professions = Profession.objects.all()
    try:
        ProfessionSerializer(professions, many=True).data
        print("Serialization successful!")
    except Exception:
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
