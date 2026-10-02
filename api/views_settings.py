# ============= SETTINGS VIEWSETS =============

import os
import signal
import subprocess

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from django.core.mail import send_mail
from django.conf import settings as django_settings
from .models import (
    PlatformSettings, SecuritySettings, NotificationSettings,
    PaymentProviderConfig, Permission, RolePermission, AuditLog
)
from .serializers_settings import (
    PlatformSettingsSerializer, SecuritySettingsSerializer,
    NotificationSettingsSerializer, PaymentProviderConfigSerializer,
    PermissionSerializer, RolePermissionSerializer, AuditLogSerializer
)


class PlatformSettingsViewSet(viewsets.ModelViewSet):
    """Platform Settings Management"""
    queryset = PlatformSettings.objects.all()
    serializer_class = PlatformSettingsSerializer
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]
    
    def get_queryset(self):
        return PlatformSettings.objects.all()

    def list(self, request, *args, **kwargs):
        # Ensure at least one settings object exists
        if not PlatformSettings.objects.exists():
            PlatformSettings.objects.create(platform_name="Hogwords Olimpiada")
            
        return super().list(request, *args, **kwargs)
    
    @action(detail=False, methods=['post'])
    def upload_logo(self, request):
        """Upload platform logo"""
        settings_obj, created = PlatformSettings.objects.get_or_create(id=1)
        
        if 'logo' in request.FILES:
            settings_obj.logo = request.FILES['logo']
            settings_obj.save()
            serializer = self.get_serializer(settings_obj)
            return Response(serializer.data)
        
        return Response({'error': 'No logo file provided'}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def upload_favicon(self, request):
        """Upload platform favicon"""
        settings_obj, created = PlatformSettings.objects.get_or_create(id=1)
        
        if 'favicon' in request.FILES:
            settings_obj.favicon = request.FILES['favicon']
            settings_obj.save()
            serializer = self.get_serializer(settings_obj)
            return Response(serializer.data)
        
        return Response({'error': 'No favicon file provided'}, status=status.HTTP_400_BAD_REQUEST)


class SecuritySettingsViewSet(viewsets.ModelViewSet):
    """Security Settings Management"""
    queryset = SecuritySettings.objects.all()
    serializer_class = SecuritySettingsSerializer
    permission_classes = [IsAdminUser]
    
    def list(self, request, *args, **kwargs):
        if not SecuritySettings.objects.exists():
            SecuritySettings.objects.create()
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        return SecuritySettings.objects.all()[:1]


class NotificationSettingsViewSet(viewsets.ModelViewSet):
    """Notification Settings Management"""
    queryset = NotificationSettings.objects.all()
    serializer_class = NotificationSettingsSerializer
    permission_classes = [IsAdminUser]
    
    def list(self, request, *args, **kwargs):
        if not NotificationSettings.objects.exists():
            NotificationSettings.objects.create()
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        return NotificationSettings.objects.all()[:1]
    
    @action(detail=False, methods=['post'])
    def test_email(self, request):
        """Send a test email to verify SMTP configuration"""
        try:
            settings_obj = NotificationSettings.objects.first()
            if not settings_obj or not settings_obj.enable_email_notifications:
                return Response({'error': 'Email notifications are not enabled'}, 
                              status=status.HTTP_400_BAD_REQUEST)
            
            test_email = request.data.get('test_email', request.user.email)
            
            # Send test email
            send_mail(
                subject='Hogwords Platform - Test Email',
                message='This is a test email from Hogwords Platform. Your SMTP configuration is working correctly!',
                from_email=settings_obj.smtp_username,
                recipient_list=[test_email],
                fail_silently=False,
            )
            
            return Response({'message': f'Test email sent successfully to {test_email}'})
        
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PaymentProviderViewSet(viewsets.ModelViewSet):
    """Payment Provider Configuration"""
    queryset = PaymentProviderConfig.objects.all()
    serializer_class = PaymentProviderConfigSerializer
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAdminUser()]
    
    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        """Toggle payment provider active status"""
        provider = self.get_object()
        provider.is_active = not provider.is_active
        provider.save()
        
        serializer = self.get_serializer(provider)
        return Response(serializer.data)


class PermissionViewSet(viewsets.ModelViewSet):
    """Permission Management"""
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    permission_classes = [IsAdminUser]
    
    @action(detail=False, methods=['get'])
    def by_category(self, request):
        """Get permissions grouped by category"""
        categories = {}
        for permission in Permission.objects.all():
            if permission.category not in categories:
                categories[permission.category] = []
            categories[permission.category].append(PermissionSerializer(permission).data)
        
        return Response(categories)


class RolePermissionViewSet(viewsets.ModelViewSet):
    """Role Permission Management"""
    queryset = RolePermission.objects.all()
    serializer_class = RolePermissionSerializer
    permission_classes = [IsAdminUser]
    
    @action(detail=False, methods=['get'])
    def by_role(self, request):
        """Get permissions for a specific role"""
        role = request.query_params.get('role')
        if not role:
            return Response({'error': 'Role parameter is required'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        role_permissions = RolePermission.objects.filter(role=role)
        serializer = self.get_serializer(role_permissions, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def assign(self, request):
        """Assign a permission to a role"""
        role = request.data.get('role')
        permission_id = request.data.get('permission_id')
        
        if not role or not permission_id:
            return Response({'error': 'Both role and permission_id are required'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        try:
            permission = Permission.objects.get(id=permission_id)
            role_permission, created = RolePermission.objects.get_or_create(
                role=role,
                permission=permission
            )
            
            serializer = self.get_serializer(role_permission)
            return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
        
        except Permission.DoesNotExist:
            return Response({'error': 'Permission not found'}, status=status.HTTP_404_NOT_FOUND)


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Audit Log (Read-only)"""
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsAdminUser]
    
    def get_queryset(self):
        queryset = AuditLog.objects.all()
        
        # Filter by user
        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        # Filter by action
        action = self.request.query_params.get('action')
        if action:
            queryset = queryset.filter(action=action)
        
        # Filter by model
        model_name = self.request.query_params.get('model_name')
        if model_name:
            queryset = queryset.filter(model_name=model_name)
        
        return queryset


class BotControlViewSet(viewsets.ViewSet):
    permission_classes = [IsAdminUser]
    
    PID_FILE = django_settings.BASE_DIR / 'bot_monitor.pid'

    def _get_pid(self):
        if self.PID_FILE.exists():
            try:
                return int(self.PID_FILE.read_text().strip())
            except ValueError:
                return None
        return None

    def _is_running(self, pid):
        if not pid:
            return False
        try:
            # Check if process exists. sending signal 0 does no harm
            os.kill(pid, 0)
            return True
        except OSError:
            return False

    @action(detail=False, methods=['get'])
    def status(self, request):
        pid = self._get_pid()
        is_running = self._is_running(pid)
        return Response({
            'is_running': is_running,
            'pid': pid if is_running else None
        })

    @action(detail=False, methods=['post'])
    def start(self, request):
        pid = self._get_pid()
        if self._is_running(pid):
            return Response({'message': 'Bot is already running', 'is_running': True})

        import sys
        manage_py = django_settings.BASE_DIR / 'manage.py'
        
        try:
            log_file = open(django_settings.BASE_DIR / 'bot_monitor.log', 'a')
            process = subprocess.Popen(
                [sys.executable, str(manage_py), 'run_payment_monitor'],
                stdout=log_file,
                stderr=log_file,
                stdin=subprocess.DEVNULL,
                cwd=str(django_settings.BASE_DIR)
            )
            
            self.PID_FILE.write_text(str(process.pid))
            
            return Response({'message': 'Bot started successfully', 'is_running': True, 'pid': process.pid})
        except Exception as e:
            return Response({'error': str(e)}, status=500)

    @action(detail=False, methods=['post'])
    def stop(self, request):
        pid = self._get_pid()
        if not self._is_running(pid):
            if self.PID_FILE.exists():
                self.PID_FILE.unlink() # Clean up stale file
            return Response({'message': 'Bot is not running', 'is_running': False})

        try:
            os.kill(pid, signal.SIGTERM) 
            if self.PID_FILE.exists():
                self.PID_FILE.unlink()
            return Response({'message': 'Bot stopped successfully', 'is_running': False})
        except Exception as e:
            return Response({'error': str(e)}, status=500)
