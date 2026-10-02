# ============= SETTINGS SERIALIZERS =============

from rest_framework import serializers
from .models import (
    PlatformSettings, SecuritySettings, NotificationSettings,
    PaymentProviderConfig, Permission, RolePermission, AuditLog
)


class PlatformSettingsSerializer(serializers.ModelSerializer):
    logo_url = serializers.SerializerMethodField()
    favicon_url = serializers.SerializerMethodField()
    
    class Meta:
        model = PlatformSettings
        fields = '__all__'
    
    def get_logo_url(self, obj):
        if obj.logo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.logo.url)
        return None
    
    def get_favicon_url(self, obj):
        if obj.favicon:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.favicon.url)
        return None


class SecuritySettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SecuritySettings
        fields = '__all__'


class NotificationSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationSettings
        fields = '__all__'
        extra_kwargs = {
            'smtp_password': {'write_only': True}
        }


class PaymentProviderConfigSerializer(serializers.ModelSerializer):
    provider_display = serializers.CharField(source='get_provider_display', read_only=True)
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    
    class Meta:
        model = PaymentProviderConfig
        fields = '__all__'
        extra_kwargs = {
            'secret_key': {'write_only': True, 'required': False},
            'merchant_id': {'required': False},
        }


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = '__all__'


class RolePermissionSerializer(serializers.ModelSerializer):
    permission_details = PermissionSerializer(source='permission', read_only=True)
    
    class Meta:
        model = RolePermission
        fields = '__all__'


class AuditLogSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    
    class Meta:
        model = AuditLog
        fields = '__all__'
        read_only_fields = ['user', 'action', 'model_name', 'object_id', 'changes', 
                           'ip_address', 'user_agent', 'timestamp']
