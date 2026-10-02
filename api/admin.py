from django.contrib import admin
from .models import (
    User, Course, Lesson, Enrollment, Olympiad, Question,
    OlympiadRegistration, TestResult, Certificate, SupportTicket,
    TicketMessage, Payment, BotConfig, TeacherProfile, Subject,
    Profession, ProfessionSubject, ProfessionRoadmapStep,
    ProfessionLevel, ProfessionNode, UserProfessionState, UserNodeProgress,
    AIAssistantFAQ, AIConversation, AIMessage, AIUnansweredQuestion,
    PlatformSettings, SecuritySettings, NotificationSettings,
    PaymentProviderConfig, Permission, RolePermission, AuditLog
)

@admin.register(AIAssistantFAQ)
class AIAssistantFAQAdmin(admin.ModelAdmin):
    list_display = ['question_uz', 'category', 'priority', 'order', 'is_active']
    list_filter = ['category', 'is_active']
    search_fields = ['question_uz', 'question_ru', 'search_tags']

class AIMessageInline(admin.TabularInline):
    model = AIMessage
    extra = 0
    readonly_fields = ['role', 'content', 'source', 'rating', 'created_at']

@admin.register(AIConversation)
class AIConversationAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'session_id', 'context_url', 'last_active']
    list_filter = ['last_active']
    inlines = [AIMessageInline]

@admin.register(AIUnansweredQuestion)
class AIUnansweredQuestionAdmin(admin.ModelAdmin):
    list_display = ['question', 'user', 'context_url', 'is_resolved', 'created_at']
    list_filter = ['is_resolved', 'created_at']
    search_fields = ['question']





class TeacherProfileInline(admin.StackedInline):
    model = TeacherProfile
    fk_name = 'user'
    can_delete = False
    verbose_name_plural = 'Teacher Profile'


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    inlines = [TeacherProfileInline]
    list_display = ['username', 'email', 'role', 'xp', 'level', 'telegram_id', 'date_joined']
    list_filter = ['role', 'is_active']
    search_fields = ['username', 'email', 'first_name', 'last_name', 'telegram_id']

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'xp_reward', 'is_featured', 'order']
    list_filter = ['is_featured']
    search_fields = ['name']



class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 1


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['title', 'subject', 'level', 'price', 'students_count', 'is_active']
    list_filter = ['subject', 'level', 'is_active', 'is_featured']
    search_fields = ['title', 'description']
    inlines = [LessonInline]


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'order', 'is_free']
    list_filter = ['course', 'is_free']


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ['user', 'course', 'progress', 'created_at']
    list_filter = ['course']


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 1


@admin.register(Olympiad)
class OlympiadAdmin(admin.ModelAdmin):
    list_display = ['title', 'subject', 'status', 'start_date', 'duration', 'is_active']
    list_filter = ['subject', 'status', 'is_active']
    search_fields = ['title', 'description']
    inlines = [QuestionInline]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['olympiad', 'order', 'points']
    list_filter = ['olympiad']


@admin.register(OlympiadRegistration)
class OlympiadRegistrationAdmin(admin.ModelAdmin):
    list_display = ['user', 'olympiad', 'is_paid', 'registered_at']
    list_filter = ['olympiad', 'is_paid']


@admin.register(TestResult)
class TestResultAdmin(admin.ModelAdmin):
    list_display = ['user', 'olympiad', 'score', 'percentage', 'submitted_at']
    list_filter = ['olympiad']


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ['cert_number', 'user', 'grade', 'status', 'issued_at']
    list_filter = ['status']
    search_fields = ['cert_number', 'user__username']


class TicketMessageInline(admin.TabularInline):
    model = TicketMessage
    extra = 1


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ['ticket_number', 'user', 'subject', 'category', 'priority', 'status']
    list_filter = ['status', 'priority', 'category']
    search_fields = ['ticket_number', 'subject']
    inlines = [TicketMessageInline]


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['user', 'amount', 'type', 'method', 'status', 'created_at']
    list_filter = ['status', 'method', 'type']


@admin.register(BotConfig)
class BotConfigAdmin(admin.ModelAdmin):
    list_display = ['id', 'bot_token', 'admin_chat_id', 'is_active', 'updated_at']


class ProfessionSubjectInline(admin.TabularInline):
    model = ProfessionSubject
    extra = 1

class ProfessionRoadmapStepInline(admin.TabularInline):
    model = ProfessionRoadmapStep
    extra = 1

@admin.register(Profession)
class ProfessionAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'order', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name', 'description']
    inlines = [ProfessionSubjectInline, ProfessionRoadmapStepInline]


@admin.register(ProfessionRoadmapStep)
class ProfessionRoadmapStepAdmin(admin.ModelAdmin):
    list_display = ['profession', 'order', 'title', 'step_type']
    list_filter = ['profession', 'step_type']
    search_fields = ['title', 'description']
    search_fields = ['title', 'description']


@admin.register(ProfessionLevel)
class ProfessionLevelAdmin(admin.ModelAdmin):
    list_display = ['profession', 'level_number', 'title', 'unlock_xp', 'order', 'is_prestige_only']
    list_filter = ['profession', 'is_prestige_only']
    search_fields = ['title']

@admin.register(ProfessionNode)
class ProfessionNodeAdmin(admin.ModelAdmin):
    list_display = ['level', 'title', 'node_type', 'is_required', 'xp_reward', 'order']
    list_filter = ['level__profession', 'node_type', 'is_required']
    search_fields = ['title']

@admin.register(UserProfessionState)
class UserProfessionStateAdmin(admin.ModelAdmin):
    list_display = ['user', 'profession', 'current_level', 'total_xp', 'status']
    list_filter = ['profession', 'status']
    search_fields = ['user__username', 'user__email']

@admin.register(UserNodeProgress)
class UserNodeProgressAdmin(admin.ModelAdmin):
    list_display = ['user', 'node', 'status', 'score', 'completed_at']
    list_filter = ['status']
    search_fields = ['user__username', 'node__title']


# ===== SETTINGS ADMIN =====

@admin.register(PlatformSettings)
class PlatformSettingsAdmin(admin.ModelAdmin):
    list_display = ['platform_name', 'support_email', 'currency', 'default_language', 'updated_at']
    fieldsets = (
        ('Basic Information', {
            'fields': ('platform_name', 'support_email', 'currency', 'default_language')
        }),
        ('Branding', {
            'fields': ('logo', 'favicon', 'platform_description')
        }),
        ('Contact', {
            'fields': ('contact_phone', 'contact_address')
        }),
        ('Social Media', {
            'fields': ('telegram_url', 'instagram_url', 'facebook_url', 'youtube_url')
        }),
        ('System', {
            'fields': ('timezone', 'date_format', 'time_format')
        }),
    )


@admin.register(SecuritySettings)
class SecuritySettingsAdmin(admin.ModelAdmin):
    list_display = ['min_password_length', 'max_login_attempts', 'enable_2fa', 'enable_audit_log', 'updated_at']
    fieldsets = (
        ('Password Requirements', {
            'fields': ('min_password_length', 'require_uppercase', 'require_numbers', 'require_special_chars')
        }),
        ('Login Security', {
            'fields': ('max_login_attempts', 'lockout_duration_minutes')
        }),
        ('Two-Factor Authentication', {
            'fields': ('enable_2fa', 'two_fa_method')
        }),
        ('Audit Logging', {
            'fields': ('enable_audit_log', 'audit_retention_days')
        }),
    )


@admin.register(NotificationSettings)
class NotificationSettingsAdmin(admin.ModelAdmin):
    list_display = ['enable_web_notifications', 'enable_telegram_notifications', 'enable_email_notifications', 'updated_at']
    fieldsets = (
        ('Automatic Notifications', {
            'fields': ('notify_on_registration', 'notify_on_course_enrollment', 'notify_on_payment_success', 
                      'notify_on_certificate_ready', 'notify_before_olympiad_hours')
        }),
        ('Channels', {
            'fields': ('enable_web_notifications', 'enable_telegram_notifications', 'enable_email_notifications')
        }),
        ('Email SMTP', {
            'fields': ('smtp_host', 'smtp_port', 'smtp_username', 'smtp_password', 'smtp_use_tls'),
            'classes': ('collapse',)
        }),
    )


@admin.register(PaymentProviderConfig)
class PaymentProviderConfigAdmin(admin.ModelAdmin):
    list_display = ['provider', 'is_active', 'test_mode', 'updated_at']
    list_filter = ['provider', 'is_active', 'test_mode']
    fieldsets = (
        (None, {
            'fields': ('provider', 'is_active', 'test_mode')
        }),
        ('Configuration', {
            'fields': ('merchant_id', 'secret_key', 'extra_config')
        }),
    )


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'category']
    list_filter = ['category']
    search_fields = ['code', 'name', 'description']


@admin.register(RolePermission)
class RolePermissionAdmin(admin.ModelAdmin):
    list_display = ['role', 'permission', 'created_at']
    list_filter = ['role', 'permission__category']
    search_fields = ['permission__code', 'permission__name']


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'action', 'model_name', 'object_id', 'ip_address', 'timestamp']
    list_filter = ['action', 'model_name', 'timestamp']
    search_fields = ['user__username', 'model_name']
    readonly_fields = ['user', 'action', 'model_name', 'object_id', 'changes', 'ip_address', 'user_agent', 'timestamp']
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
