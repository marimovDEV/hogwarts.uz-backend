from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom User Model"""
    ROLE_CHOICES = [
        ('STUDENT', 'Student'),
        ('TEACHER', 'Teacher'),
        ('ADMIN', 'Admin'),
    ]
    
    GRADE_CHOICES = [
        ('1', '1-sinf'),
        ('2', '2-sinf'),
        ('3', '3-sinf'),
        ('4', '4-sinf'),
        ('5', '5-sinf'),
        ('6', '6-sinf'),
        ('7', '7-sinf'),
        ('8', '8-sinf'),
        ('9', '9-sinf'),
        ('10', '10-sinf'),
        ('11', '11-sinf'),
        ('STUDENT', 'Talaba'),
        ('GRADUATE', 'Bitiruvchi'),
    ]
    
    phone = models.CharField(max_length=20, blank=True, null=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='STUDENT')
    xp = models.IntegerField(default=0)
    level = models.IntegerField(default=1)
    
    # Wallet
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0) # ArdCoins
    
    # New student fields
    birth_date = models.DateField(blank=True, null=True)
    region = models.CharField(max_length=100, blank=True, null=True)  # Viloyat/Shahar
    school = models.CharField(max_length=200, blank=True, null=True)  # Maktab nomi
    grade = models.CharField(max_length=10, choices=GRADE_CHOICES, blank=True, null=True)  # Sinf
    
    # Telegram integration
    telegram_id = models.BigIntegerField(null=True, blank=True, unique=True)
    telegram_linking_token = models.CharField(max_length=100, null=True, blank=True, unique=True)
    telegram_connected_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'users'
    
    def __str__(self):
        return self.email or self.username


class Subject(models.Model):
    """Subject/Category Model for CMS"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, default="BookOpen", help_text="Lucide icon name")
    color = models.CharField(max_length=50, default="bg-blue-600", help_text="Tailwind class")
    xp_reward = models.IntegerField(default=50)
    is_featured = models.BooleanField(default=True)
    order = models.IntegerField(default=0)
    teachers = models.ManyToManyField('User', related_name='subjects', limit_choices_to={'role': 'TEACHER'})
    
    class Meta:
        db_table = 'subjects'
        ordering = ['order', 'name']
        
    def __str__(self):
        return self.name

class Course(models.Model):
    """Course Model"""
    LEVEL_CHOICES = [
        ('BEGINNER', 'Boshlang\'ich'),
        ('INTERMEDIATE', 'O\'rta'),
        ('ADVANCED', 'Murakkab'),
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    thumbnail = models.ImageField(upload_to='courses/', blank=True, null=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    level = models.CharField(max_length=15, choices=LEVEL_CHOICES, default='BEGINNER')
    subject = models.CharField(max_length=100)
    duration = models.CharField(max_length=50, blank=True, null=True)
    lessons_count = models.IntegerField(default=0)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    students_count = models.IntegerField(default=0)
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    xp_reward = models.IntegerField(default=50, help_text="XP given upon completion")
    show_on_home = models.BooleanField(default=False)
    home_order = models.IntegerField(default=0)
    teacher = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, related_name='courses', limit_choices_to={'role': 'TEACHER'})
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'courses'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title


class Lesson(models.Model):
    """Lesson Model"""
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    video_url = models.URLField(blank=True, null=True)
    pdf_url = models.URLField(blank=True, null=True)
    duration = models.CharField(max_length=20, blank=True, null=True)
    order = models.IntegerField(default=0)
    is_free = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'lessons'
        ordering = ['order']
    
    def __str__(self):
        return f"{self.course.title} - {self.title}"


class Enrollment(models.Model):
    """Course Enrollment"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='enrollments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    progress = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    completed_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'enrollments'
        unique_together = ['user', 'course']
    
    def __str__(self):
        return f"{self.user.username} - {self.course.title}"


class Olympiad(models.Model):
    """Olympiad Model"""
    STATUS_CHOICES = [
        ('UPCOMING', 'Kutilmoqda'),
        ('ACTIVE', 'Faol'),
        ('COMPLETED', 'Tugagan'),
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    subject = models.CharField(max_length=100)
    thumbnail = models.ImageField(upload_to='olympiads/', blank=True, null=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    duration = models.IntegerField(help_text="Duration in minutes")
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    max_participants = models.IntegerField(blank=True, null=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='UPCOMING')
    is_active = models.BooleanField(default=True)
    xp_reward = models.IntegerField(default=50, help_text="XP given for participation")
    show_on_home = models.BooleanField(default=False)
    show_on_home = models.BooleanField(default=False)
    home_order = models.IntegerField(default=0)
    teacher = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, related_name='olympiads', limit_choices_to={'role': 'TEACHER'})
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'olympiads'
        ordering = ['-start_date']
    
    def __str__(self):
        return self.title


class Question(models.Model):
    """Olympiad Question"""
    olympiad = models.ForeignKey(Olympiad, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField()
    options = models.JSONField()  # ["A variant", "B variant", "C variant", "D variant"]
    correct_answer = models.IntegerField()  # 0-based index
    points = models.IntegerField(default=1)
    order = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'questions'
        ordering = ['order']
    
    def __str__(self):
        return f"{self.olympiad.title} - Q{self.order}"


class OlympiadRegistration(models.Model):
    """Olympiad Registration"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='olympiad_registrations')
    olympiad = models.ForeignKey(Olympiad, on_delete=models.CASCADE, related_name='registrations')
    is_paid = models.BooleanField(default=False)
    registered_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'olympiad_registrations'
        unique_together = ['user', 'olympiad']
    
    def __str__(self):
        return f"{self.user.username} - {self.olympiad.title}"


class TestResult(models.Model):
    """Test Result"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='test_results')
    olympiad = models.ForeignKey(Olympiad, on_delete=models.CASCADE, related_name='results')
    answers = models.JSONField()  # [0, 1, 2, 0, ...]
    score = models.IntegerField()
    percentage = models.DecimalField(max_digits=5, decimal_places=2)
    time_taken = models.IntegerField(help_text="Time in seconds")
    submitted_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'test_results'
        unique_together = ['user', 'olympiad']
    
    def __str__(self):
        return f"{self.user.username} - {self.olympiad.title}: {self.score}"


class Certificate(models.Model):
    """Certificate Model"""
    STATUS_CHOICES = [
        ('PENDING', 'Kutilmoqda'),
        ('VERIFIED', 'Tasdiqlangan'),
        ('REJECTED', 'Rad etilgan'),
        ('EXPIRED', 'Muddati o\'tgan'),
    ]
    
    cert_number = models.CharField(max_length=20, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='certificates')
    course = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True, blank=True)
    olympiad = models.ForeignKey(Olympiad, on_delete=models.SET_NULL, null=True, blank=True)
    grade = models.CharField(max_length=10)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='PENDING')
    issued_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(blank=True, null=True)
    verified_by = models.CharField(max_length=100, blank=True, null=True)
    
    class Meta:
        db_table = 'certificates'
    
    def __str__(self):
        return f"{self.cert_number} - {self.user.username}"


class SupportTicket(models.Model):
    """Support Ticket"""
    STATUS_CHOICES = [
        ('OPEN', 'Ochiq'),
        ('IN_PROGRESS', 'Jarayonda'),
        ('PENDING', 'Kutilmoqda'),
        ('RESOLVED', 'Hal qilindi'),
        ('ESCALATED', 'Yuqoriga uzatildi'),
    ]
    PRIORITY_CHOICES = [
        ('LOW', 'Past'),
        ('MEDIUM', 'O\'rta'),
        ('HIGH', 'Yuqori'),
    ]
    
    ticket_number = models.CharField(max_length=20, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tickets')
    subject = models.CharField(max_length=200)
    category = models.CharField(max_length=50)  # Payment, Technical, Course, Olympiad
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='MEDIUM')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='OPEN')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'support_tickets'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.ticket_number} - {self.subject}"


class TicketMessage(models.Model):
    """Ticket Message"""
    ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name='messages')
    sender_id = models.CharField(max_length=50)
    sender_name = models.CharField(max_length=100)
    message = models.TextField()
    is_internal = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'ticket_messages'
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.ticket.ticket_number} - {self.sender_name}"


class Payment(models.Model):
    """Payment Model"""
    STATUS_CHOICES = [
        ('PENDING', 'Kutilmoqda'),
        ('COMPLETED', 'Bajarildi'),
        ('FAILED', 'Muvaffaqiyatsiz'),
        ('REFUNDED', 'Qaytarildi'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    type = models.CharField(max_length=20)  # COURSE, OLYMPIAD
    reference_id = models.CharField(max_length=50)
    method = models.CharField(max_length=20)  # PAYME, CLICK, UZCARD
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='PENDING')
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        db_table = 'payments'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.amount} so'm"


class VerificationCode(models.Model):
    """Phone Verification Code for Registration"""
    phone = models.CharField(max_length=20)
    code = models.CharField(max_length=10)
    email = models.EmailField(blank=True, null=True)
    username = models.CharField(max_length=150, blank=True, null=True)
    password_hash = models.CharField(max_length=255, blank=True, null=True)
    first_name = models.CharField(max_length=150, blank=True, null=True)
    last_name = models.CharField(max_length=150, blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    attempts = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    
    class Meta:
        db_table = 'verification_codes'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.phone} - {self.code}"
    
    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.expires_at
    
    def is_valid(self, code):
        if self.is_expired():
            return False
        if self.attempts >= 5:
            return False
        return self.code == code


class BotConfig(models.Model):
    """Configuration for Telegram Bot"""
    bot_token = models.CharField(max_length=255)
    admin_chat_id = models.CharField(max_length=100, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'bot_configs'
        verbose_name = 'Bot Configuration'
        verbose_name_plural = 'Bot Configurations'

    def __str__(self):
        return f"Bot Config ({'Active' if self.is_active else 'Inactive'})"


class LevelReward(models.Model):
    """Rewards for reaching specific levels"""
    level = models.IntegerField(unique=True)
    xp_threshold = models.IntegerField(help_text="XP required to reach this level")
    reward_description = models.CharField(max_length=255)
    icon = models.CharField(max_length=50, default='Award', help_text="Lucide icon name")
    
    class Meta:
        db_table = 'level_rewards'
        ordering = ['level']
        
    class Meta:
        db_table = 'level_rewards'
        ordering = ['level']
        
    def __str__(self):
        return f"Level {self.level}: {self.reward_description}"


class UserStreak(models.Model):
    """Tracks user's learning streak"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='streak')
    current_streak = models.IntegerField(default=0)
    max_streak = models.IntegerField(default=0)
    last_activity_date = models.DateField(null=True, blank=True)
    freeze_count = models.IntegerField(default=0, help_text="Number of streak freezes available")
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.current_streak} days"

class ActivityLog(models.Model):
    """Log of user activities for streak calculation"""
    ACTIVITY_TYPES = [
        ('LESSON_COMPLETE', 'Lesson Completed'),
        ('TEST_PASS', 'Test Passed'),
        ('OLYMPIAD_PARTICIPATION', 'Olympiad Participation'),
        ('DAILY_LOGIN', 'Daily Login'), # Optional, maybe doesn't count for streak
        ('COURSE_ENROLL', 'Course Enrollment'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities')
    activity_type = models.CharField(max_length=50, choices=ACTIVITY_TYPES)
    description = models.CharField(max_length=255, blank=True)
    points_earned = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.user.username} - {self.activity_type} - {self.created_at.date()}"


class HomePageConfig(models.Model):
    """Homepage Configuration (Singleton)"""
    hero_title = models.CharField(max_length=200, default="Olimpiadalar orqali kelajagingizni quring")
    hero_subtitle = models.TextField(default="O'zbekistonning eng iqtidorli yoshlari safida bo'ling. Bilimingizni sinang va qimmatbaho sovg'alarga ega bo'ling.")
    hero_button_text = models.CharField(max_length=50, default="Boshlash")
    hero_button_link = models.CharField(max_length=200, default="/register")
    hero_image = models.ImageField(upload_to='homepage/', blank=True, null=True)
    
    # CTA Section Configuration
    cta_title = models.CharField(max_length=200, default="Kelajagingizni bugundan boshlang")
    cta_subtitle = models.TextField(default="Minglab o'quvchilar safida bo'ling va o'z bilimingizni sinovdan o'tkazing")
    cta_button_text = models.CharField(max_length=50, default="Ro'yxatdan o'tish")
    cta_button_link = models.CharField(max_length=200, default="/register")
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'homepage_config'
        verbose_name = 'Homepage Configuration'
        verbose_name_plural = 'Homepage Configuration'
        
    def save(self, *args, **kwargs):
        if not self.pk and HomePageConfig.objects.exists():
            return
        return super(HomePageConfig, self).save(*args, **kwargs)
        
    def __str__(self):
        return "Homepage Configuration"


class HomeStat(models.Model):
    """Homepage Statistic Item"""
    label = models.CharField(max_length=100)
    value = models.CharField(max_length=50) # e.g. "10K+"
    icon = models.CharField(max_length=50, help_text="Lucide icon name")
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'home_stats'
        ordering = ['order']

    def __str__(self):
        return self.label


class HomeStep(models.Model):
    """How It Works Step"""
    title = models.CharField(max_length=200)
    description = models.TextField()
    icon = models.CharField(max_length=50)
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'home_steps'
        ordering = ['order']
        
    def __str__(self):
        return self.title


class HomeAdvantage(models.Model):
    """Trust/Advantage Item"""
    title = models.CharField(max_length=200)
    description = models.TextField()
    icon = models.CharField(max_length=50)
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'home_advantages'
        ordering = ['order']
        
    def __str__(self):
        return self.title



class TeacherProfile(models.Model):
    """Teacher Profile extensions"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='teacher_profile')
    bio = models.TextField(blank=True)
    experience_years = models.IntegerField(default=0)
    specialization = models.CharField(max_length=200, blank=True)
    telegram_username = models.CharField(max_length=100, blank=True) # e.g. @username
    instagram_username = models.CharField(max_length=100, blank=True) # e.g. @username_inst
    youtube_channel = models.URLField(blank=True, null=True)
    linkedin_profile = models.URLField(blank=True, null=True)
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'teacher_profiles'
    
    def __str__(self):
        return f"{self.user.username} - Teacher Profile"

class Notification(models.Model):
    """System Notifications for Users"""
    TYPE_CHOICES = [
        ('STREAK', 'Streak Warning'),
        ('LESSON', 'Lesson Reminder'),
        ('OLYMPIAD', 'Olympiad Alert'),
        ('SYSTEM', 'System Message'),
        ('PAYMENT', 'Payment Update'),
        ('ACHIEVEMENT', 'Achievement Unlocked'),
    ]
    
    CHANNEL_CHOICES = [
        ('WEB', 'Web Only'),
        ('TELEGRAM', 'Telegram Only'),
        ('SMS', 'SMS Only'),
        ('ALL', 'All Channels'),
    ]
    
    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='SYSTEM')
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES, default='WEB')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    link = models.CharField(max_length=255, blank=True, null=True, help_text="Link to redirect user")

    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.user.username}"
