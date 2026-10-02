# Create Initial Settings Data
# Run this in Django shell: python manage.py shell < create_initial_settings.py

from api.models import (
    PlatformSettings, SecuritySettings, NotificationSettings,
    PaymentProviderConfig, Permission
)

# Create Platform Settings
platform_settings, created = PlatformSettings.objects.get_or_create(
    id=1,
    defaults={
        'platform_name': 'Hogwords',
        'support_email': 'support@ardent.uz',
        'currency': 'UZS',
        'default_language': 'uz',
        'platform_description': 'Hogwords - O\'zbekistondagi eng yaxshi ta\'lim platformasi',
        'contact_phone': '+998 90 123 45 67',
        'contact_address': 'Toshkent, O\'zbekiston',
        'telegram_url': 'https://t.me/ardent_uz',
        'instagram_url': 'https://instagram.com/ardent_uz',
        'facebook_url': 'https://facebook.com/ardent.uz',
        'youtube_url': 'https://youtube.com/@ardent_uz',
        'timezone': 'Asia/Tashkent',
        'date_format': 'DD.MM.YYYY',
        'time_format': 'HH:mm'
    }
)
print(f"Platform Settings: {'Created' if created else 'Already exists'}")

# Create Security Settings
security_settings, created = SecuritySettings.objects.get_or_create(
    id=1,
    defaults={
        'min_password_length': 8,
        'require_uppercase': True,
        'require_numbers': True,
        'require_special_chars': False,
        'max_login_attempts': 5,
        'lockout_duration_minutes': 30,
        'enable_2fa': False,
        'two_fa_method': 'EMAIL',
        'enable_audit_log': True,
        'audit_retention_days': 90
    }
)
print(f"Security Settings: {'Created' if created else 'Already exists'}")

# Create Notification Settings
notification_settings, created = NotificationSettings.objects.get_or_create(
    id=1,
    defaults={
        'notify_on_registration': True,
        'notify_on_course_enrollment': True,
        'notify_on_payment_success': True,
        'notify_on_certificate_ready': True,
        'notify_before_olympiad_hours': 24,
        'enable_web_notifications': True,
        'enable_telegram_notifications': True,
        'enable_email_notifications': False,
        'smtp_host': '',
        'smtp_port': 587,
        'smtp_username': '',
        'smtp_password': '',
        'smtp_use_tls': True
    }
)
print(f"Notification Settings: {'Created' if created else 'Already exists'}")

# Create Payment Providers
providers = [
    {
        'provider': 'CLICK',
        'is_active': True,
        'merchant_id': 'merchant_click_123',
        'secret_key': 'secret_click_key',
        'test_mode': True
    },
    {
        'provider': 'PAYME',
        'is_active': True,
        'merchant_id': 'merchant_payme_456',
        'secret_key': 'secret_payme_key',
        'test_mode': True
    },
    {
        'provider': 'UZUM',
        'is_active': False,
        'merchant_id': 'merchant_uzum_789',
        'secret_key': 'secret_uzum_key',
        'test_mode': True
    }
]

for provider_data in providers:
    provider, created = PaymentProviderConfig.objects.get_or_create(
        provider=provider_data['provider'],
        defaults=provider_data
    )
    print(f"Payment Provider {provider_data['provider']}: {'Created' if created else 'Already exists'}")

# Create Basic Permissions
permissions = [
    # Courses
    {'code': 'view_courses', 'name': 'View Courses', 'category': 'courses', 'description': 'Can view all courses'},
    {'code': 'create_courses', 'name': 'Create Courses', 'category': 'courses', 'description': 'Can create new courses'},
    {'code': 'edit_courses', 'name': 'Edit Courses', 'category': 'courses', 'description': 'Can edit existing courses'},
    {'code': 'delete_courses', 'name': 'Delete Courses', 'category': 'courses', 'description': 'Can delete courses'},
    
    # Olympiads
    {'code': 'view_olympiads', 'name': 'View Olympiads', 'category': 'olympiads', 'description': 'Can view all olympiads'},
    {'code': 'create_olympiads', 'name': 'Create Olympiads', 'category': 'olympiads', 'description': 'Can create new olympiads'},
    {'code': 'edit_olympiads', 'name': 'Edit Olympiads', 'category': 'olympiads', 'description': 'Can edit existing olympiads'},
    {'code': 'delete_olympiads', 'name': 'Delete Olympiads', 'category': 'olympiads', 'description': 'Can delete olympiads'},
    
    # Users
    {'code': 'view_users', 'name': 'View Users', 'category': 'users', 'description': 'Can view all users'},
    {'code': 'edit_users', 'name': 'Edit Users', 'category': 'users', 'description': 'Can edit user profiles'},
    {'code': 'delete_users', 'name': 'Delete Users', 'category': 'users', 'description': 'Can delete users'},
    
    # Finance
    {'code': 'view_payments', 'name': 'View Payments', 'category': 'finance', 'description': 'Can view payment transactions'},
    {'code': 'process_refunds', 'name': 'Process Refunds', 'category': 'finance', 'description': 'Can process refund requests'},
    
    # Settings
    {'code': 'manage_settings', 'name': 'Manage Settings', 'category': 'settings', 'description': 'Can manage platform settings'},
]

for perm_data in permissions:
    perm, created = Permission.objects.get_or_create(
        code=perm_data['code'],
        defaults=perm_data
    )
    print(f"Permission {perm_data['code']}: {'Created' if created else 'Already exists'}")

print("\n✅ Initial settings data created successfully!")
