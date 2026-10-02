from django.contrib.auth.models import AbstractUser
from django.db import models


class PlatformSettings(models.Model):
    """Comprehensive Platform Settings"""
    # Basic Info
    platform_name = models.CharField(max_length=255, default='Hogwords')
    support_email = models.EmailField(default='support@ardent.uz')
    currency = models.CharField(max_length=3, default='UZS')
    default_language = models.CharField(max_length=2, choices=[('uz', 'Uzbek'), ('ru', 'Russian')], default='uz')
    
    # Branding
    logo = models.ImageField(upload_to='branding/', null=True, blank=True)
    favicon = models.ImageField(upload_to='branding/', null=True, blank=True)
    platform_description = models.TextField(blank=True, help_text="SEO description")
    
    # Contact Information
    contact_phone = models.CharField(max_length=20, blank=True)
    contact_address = models.TextField(blank=True)
    
    # Social Media
    telegram_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    facebook_url = models.URLField(blank=True)
    youtube_url = models.URLField(blank=True)
    
    # System Configuration
    timezone = models.CharField(max_length=50, default='Asia/Tashkent')
    date_format = models.CharField(max_length=20, default='DD.MM.YYYY')
    time_format = models.CharField(max_length=20, default='HH:mm')
    
    # Payment Configuration
    ACTIVE_PAYMENT_TYPE_CHOICES = [
        ('INTEGRATION', 'Automatic Integration'),
        ('MANUAL', 'Manual Payment'),
        ('BOT', 'User Bot'),
    ]
    active_payment_type = models.CharField(
        max_length=20, 
        choices=ACTIVE_PAYMENT_TYPE_CHOICES, 
        default='INTEGRATION',
        help_text="Which payment method type is currently active for users."
    )
    
    # Currency Rate
    ardcoin_exchange_rate = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=100.00,
        help_text="1 ArdCoin = necha so'm?"
    )
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'platform_settings'
        verbose_name = 'Platform Settings'
        verbose_name_plural = 'Platform Settings'
    
    def __str__(self):
        return f"Settings for {self.platform_name}"


class SecuritySettings(models.Model):
    """Security and Authentication Settings"""
    # Password Requirements
    min_password_length = models.IntegerField(default=8)
    require_uppercase = models.BooleanField(default=True)
    require_numbers = models.BooleanField(default=True)
    require_special_chars = models.BooleanField(default=False)
    
    # Login Security
    max_login_attempts = models.IntegerField(default=5)
    lockout_duration_minutes = models.IntegerField(default=30)
    
    # Two-Factor Authentication
    enable_2fa = models.BooleanField(default=False)
    two_fa_method = models.CharField(
        max_length=10,
        choices=[('SMS', 'SMS'), ('EMAIL', 'Email')],
        default='EMAIL'
    )
    
    # Audit Logging
    enable_audit_log = models.BooleanField(default=True)
    audit_retention_days = models.IntegerField(default=90)
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'security_settings'
        verbose_name = 'Security Settings'
        verbose_name_plural = 'Security Settings'
    
    def __str__(self):
        return "Security Settings"


class NotificationSettings(models.Model):
    """Notification and Communication Settings"""
    # Automatic Notifications
    notify_on_registration = models.BooleanField(default=True)
    notify_on_course_enrollment = models.BooleanField(default=True)
    notify_on_payment_success = models.BooleanField(default=True)
    notify_on_certificate_ready = models.BooleanField(default=True)
    notify_before_olympiad_hours = models.IntegerField(default=24)
    
    # Notification Channels
    enable_web_notifications = models.BooleanField(default=True)
    enable_telegram_notifications = models.BooleanField(default=True)
    enable_email_notifications = models.BooleanField(default=False)
    
    # Email SMTP Configuration
    smtp_host = models.CharField(max_length=255, blank=True)
    smtp_port = models.IntegerField(default=587)
    smtp_username = models.CharField(max_length=255, blank=True)
    smtp_password = models.CharField(max_length=255, blank=True)
    smtp_use_tls = models.BooleanField(default=True)
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'notification_settings'
        verbose_name = 'Notification Settings'
        verbose_name_plural = 'Notification Settings'
    
    def __str__(self):
        return "Notification Settings"


class PaymentProviderConfig(models.Model):
    """Payment Provider Configuration"""
    TYPE_CHOICES = [
        ('INTEGRATION', 'Integration'),
        ('MANUAL', 'Manual'),
        ('BOT', 'Bot'),
    ]

    PROVIDER_CHOICES = [
        ('CLICK', 'Click'),
        ('PAYME', 'Payme'),
        ('UZUM', 'Uzum'),
        ('CARD', 'Card Transfer'),
        ('QR', 'QR Code'),
        ('USERBOT', 'User Bot'),
    ]
    
    name = models.CharField(max_length=100, default="Payment Provider")
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='INTEGRATION')
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    is_active = models.BooleanField(default=False)
    
    # Integration specific (Optional now)
    merchant_id = models.CharField(max_length=255, blank=True, null=True)
    secret_key = models.CharField(max_length=255, blank=True, null=True)
    test_mode = models.BooleanField(default=True)
    
    # Flexible configuration for all types
    # INTEGRATION: merchant_id, secret_key
    # MANUAL: card_number, holder_name, bank_name, qr_image_url
    # BOT: bot_token, bot_url
    config = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'payment_provider_configs'
        verbose_name = 'Payment Provider'
        verbose_name_plural = 'Payment Providers'
    
    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"


class Permission(models.Model):
    """Granular Permission Definitions"""
    code = models.CharField(max_length=50, unique=True, help_text="e.g., 'view_courses', 'edit_olympiads'")
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=50, help_text="e.g., 'courses', 'olympiads', 'users'")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'permissions'
        ordering = ['category', 'code']
    
    def __str__(self):
        return f"{self.category}.{self.code}"


class RolePermission(models.Model):
    """Maps Permissions to Roles"""
    ROLE_CHOICES = [
        ('ADMIN', 'Admin'),
        ('TEACHER', 'Teacher'),
        ('MODERATOR', 'Moderator'),
        ('SUPPORT', 'Support'),
    ]
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE, related_name='role_permissions')
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'role_permissions'
        unique_together = ['role', 'permission']
        ordering = ['role', 'permission__category']
    
    def __str__(self):
        return f"{self.role} -> {self.permission.code}"


class AuditLog(models.Model):
    """Audit Trail for Admin Actions"""
    ACTION_CHOICES = [
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
        ('LOGIN', 'Login'),
        ('LOGOUT', 'Logout'),
    ]
    
    user = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    model_name = models.CharField(max_length=50, blank=True)
    object_id = models.IntegerField(null=True, blank=True)
    changes = models.JSONField(default=dict, blank=True, help_text="JSON of what changed")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'audit_logs'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['model_name', '-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.user} - {self.action} {self.model_name} at {self.timestamp}"
