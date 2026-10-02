from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

router = DefaultRouter()
router.register(r'courses', views.CourseViewSet)
router.register(r'olympiads', views.OlympiadViewSet, basename='olympiads')
router.register(r'questions', views.QuestionViewSet, basename='questions')
router.register(r'olympiad-prizes', views.OlympiadPrizeViewSet, basename='olympiad-prizes')
router.register(r'winner-prizes', views.WinnerPrizeViewSet, basename='winner-prizes')
router.register(r'subjects', views.SubjectViewSet)
router.register(r'lessons', views.LessonViewSet)
router.register(r'modules', views.ModuleViewSet)
router.register(r'lesson-practices', views.LessonPracticeViewSet)
router.register(r'lesson-tests', views.LessonTestViewSet)
router.register(r'certificates', views.CertificateViewSet, basename='certificates')
router.register(r'support', views.SupportTicketViewSet, basename='support')
router.register(r'payments', views.PaymentViewSet, basename='payments')
router.register(r'users', views.UserViewSet, basename='users')
router.register(r'bot/config', views.BotConfigViewSet, basename='bot-config')
router.register(r'admin/dashboard', views.AdminDashboardViewSet, basename='admin-dashboard')
router.register(r'wallet', views.WalletViewSet, basename='wallet')
router.register(r'level-rewards', views.LevelRewardViewSet, basename='level-rewards')
router.register(r'streak', views.StreakViewSet, basename='streak')
router.register(r'gamification', views.GamificationViewSet, basename='gamification')
router.register(r'homepage', views.HomePageViewSet, basename='homepage')
router.register(r'home-stats', views.HomeStatViewSet, basename='home-stats')
router.register(r'home-steps', views.HomeStepViewSet, basename='home-steps')
router.register(r'home-advantages', views.HomeAdvantageViewSet, basename='home-advantages')
router.register(r'free-course-section', views.FreeCourseSectionViewSet, basename='free-course-section')
router.register(r'free-course-cards', views.FreeCourseLessonCardViewSet, basename='free-course-cards')
router.register(r'teacher', views.TeacherViewSet, basename='teacher')
router.register(r'notifications', views.NotificationViewSet, basename='notifications')
router.register(r'notification-templates', views.NotificationTemplateViewSet, basename='notification-templates')
router.register(r'notification-broadcasts', views.NotificationBroadcastViewSet, basename='notification-broadcasts')
router.register(r'professions', views.ProfessionViewSet, basename='professions')
router.register(r'test-results', views.TestResultViewSet, basename='test-results')
router.register(r'leads', views.LeadViewSet, basename='leads')
router.register(r'banners', views.BannerViewSet, basename='banners')
router.register(r'testimonials', views.TestimonialViewSet, basename='testimonials')
router.register(r'ai-assistant-faq', views.AIAssistantFAQViewSet, basename='ai-assistant-faq')
router.register(r'ai-conversations', views.AIConversationViewSet, basename='ai-conversations')
router.register(r'ai-unanswered', views.AIUnansweredQuestionViewSet, basename='ai-unanswered')

# Monetization & Content
router.register(r'payouts', views.PayoutViewSet, basename='payouts')
router.register(r'lesson-content', views.LessonContentViewSet, basename='lesson-content')
router.register(r'homeworks', views.HomeworkViewSet, basename='homeworks')
router.register(r'homework-submissions', views.HomeworkSubmissionViewSet, basename='homework-submissions')

# Settings ViewSets
from .views_settings import (
    PlatformSettingsViewSet, SecuritySettingsViewSet, NotificationSettingsViewSet,
    PaymentProviderViewSet, PermissionViewSet, RolePermissionViewSet, AuditLogViewSet
)
router.register(r'settings/platform', PlatformSettingsViewSet, basename='platform-settings')
router.register(r'settings/security', SecuritySettingsViewSet, basename='security-settings')
router.register(r'settings/notifications', NotificationSettingsViewSet, basename='notification-settings')
router.register(r'settings/payment-providers', PaymentProviderViewSet, basename='payment-providers')
router.register(r'settings/permissions', PermissionViewSet, basename='permissions')
router.register(r'settings/role-permissions', RolePermissionViewSet, basename='role-permissions')
router.register(r'settings/audit-logs', AuditLogViewSet, basename='audit-logs')
from .views_settings import BotControlViewSet
router.register(r'settings/bot-control', BotControlViewSet, basename='bot-control')

from .views_analytics import AnalyticsViewSet
router.register(r'analytics', AnalyticsViewSet, basename='analytics')

urlpatterns = [
    # Auth endpoints
    path('auth/register/', views.register, name='register'),
    path('auth/login/', views.login, name='login'),
    path('auth/me/', views.me, name='me'),
    path('auth/profile/', views.update_profile, name='update-profile'),
    path('auth/change-password/', views.change_password, name='change-password'),
    path('auth/upload-avatar/', views.upload_avatar, name='upload-avatar'),
    path('auth/check-username/', views.check_username, name='check-username'),
    
    # Telegram Verification endpoints
    path('auth/send-code/', views.send_verification_code, name='send-code'),
    path('auth/verify-code/', views.verify_code, name='verify-code'),
    path('auth/resend-code/', views.resend_code, name='resend-code'),
    path('auth/complete-registration/', views.complete_registration, name='complete-registration'),
    path('auth/reset-password/', views.reset_password, name='reset-password'),
    path('auth/forgot-password/', views.forgot_password, name='forgot-password'),
    path('auth/verify-reset-code/', views.verify_reset_code, name='verify-reset-code'),
    
    # Admin endpoints
    path('admin/stats/', views.admin_stats, name='admin-stats'),
    path('admin/settings/commissions/', views.manage_commission_settings, name='manage-commissions'),
    
    # Public Statistics endpoints
    path('stats/public/', views.public_statistics, name='public-statistics'),
    path('courses/featured/', views.featured_courses, name='featured-courses'),
    path('olympiads/upcoming/', views.upcoming_olympiads, name='upcoming-olympiads'),
    
    # Telegram Bot & Linking
    path('bot/link-token/', views.get_telegram_linking_token, name='bot-link-token'),
    path('bot/webhook/', views.telegram_webhook, name='bot-webhook'),
    
    # Include router URLs
    path('', include(router.urls)),

    # Swagger/OpenAPI endpoints
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]
