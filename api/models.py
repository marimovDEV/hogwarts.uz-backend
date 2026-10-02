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
    
    # Preferred language
    LANGUAGE_CHOICES = [
        ('uz', "O'zbekcha"),
        ('ru', 'Русский'),
    ]
    language = models.CharField(max_length=2, choices=LANGUAGE_CHOICES, default='uz')
    
    # Notification preferences
    last_active_at = models.DateTimeField(auto_now=True)
    notification_settings = models.JSONField(default=dict, blank=True, help_text="User's notification preferences")
    
    class Meta:
        db_table = 'users'
    
    def __str__(self):
        return self.email or self.username

    def calculate_level(self, xp):
        """Calculate level based on XP: 500 XP per level"""
        return (xp // 500) + 1

    def add_xp(self, amount, activity_type, description=""):
        """
        Add XP to user, update level, and log activity.
        """
        if amount <= 0:
            return
            
        self.xp += amount
        new_level = self.calculate_level(self.xp)
        
        # Check for level up
        leveled_up = new_level > self.level
        self.level = new_level
        self.save(update_fields=['xp', 'level'])
        
        # Log activity
        ActivityLog.objects.create(
            user=self,
            activity_type=activity_type,
            description=description,
            points_earned=amount
        )
        
        # If leveled up, create a notification
        if leveled_up:
            from .services.notification_service import NotificationService
            NotificationService.create_notification(
                user=self,
                title="Yangi daraja! 🚀",
                message=f"Tabriklaymiz! Siz {self.level}-darajaga ko'tarildingiz!",
                notification_type='ACHIEVEMENT',
                link="/dashboard"
            )

    @property
    def level_progress(self):
        """Returns stats about current level progress based on LevelReward model"""
        # Calculate progress relative to current level's threshold and next level's threshold
        current_lvl_reward = LevelReward.objects.filter(level=self.level).first()
        next_lvl_reward = LevelReward.objects.filter(level=self.level + 1).first()
        
        # Determine thresholds
        current_threshold = current_lvl_reward.xp_threshold if current_lvl_reward else (self.level - 1) * 500
        next_threshold = next_lvl_reward.xp_threshold if next_lvl_reward else self.level * 500
        
        xp_in_level = self.xp - current_threshold
        xp_to_next = next_threshold - current_threshold
        
        # Progress Percent
        if xp_to_next > 0:
            progress_percent = int(max(0, min(100, (xp_in_level / xp_to_next) * 100)))
        else:
            progress_percent = 100
            
        xp_left = max(0, next_threshold - self.xp)
        
        # Get Roadmap (all levels)
        all_rewards = LevelReward.objects.all().order_by('level')
        roadmap = []
        for r in all_rewards:
            roadmap.append({
                'level': r.level,
                'name': f"{r.level}-daraja", # Can add a 'name' field to LevelReward if needed
                'reward': r.reward_description,
                'icon': r.icon,
                'reached': self.level >= r.level
            })
            
        # Fallback names
        level_names = {
            1: "Boshlovchi", 2: "Izlanuvchi", 3: "Faol O'quvchi", 
            4: "Bilimdon", 5: "Tajribali", 6: "Professional", 
            7: "Ekspert", 8: "Master", 9: "Grandmaster", 10: "Afsonaviy"
        }
        
        current_name = level_names.get(self.level, f"{self.level}-daraja")
        next_name = level_names.get(self.level + 1, f"{self.level + 1}-daraja")
        
        return {
            'current': self.level,
            'current_name': current_name,
            'next': self.level + 1,
            'next_name': next_name,
            'xp_current': self.xp,
            'xp_max': next_threshold,
            'xp_left': xp_left,
            'progress_percent': progress_percent,
            'reward': next_lvl_reward.reward_description if next_lvl_reward else "Yangi yutuqlar yo'lda!",
            'roadmap': roadmap
        }

    @property
    def ranking(self):
        """Returns the user's rank based on XP among students"""
        if self.role != 'STUDENT' and not self.is_superuser:
            return 0
        
        # Rank is 1 + number of students with more XP than this user
        # In case of equal XP, users are ranked by ID/Date Joined (consistent)
        higher_xp_count = User.objects.filter(
            role='STUDENT',
            xp__gt=self.xp
        ).count()
        
        return higher_xp_count + 1

    @property
    def certificates_count(self):
        """Returns the count of verified certificates for this user"""
        return self.certificates.filter(status='VERIFIED').count()



class CommissionSettings(models.Model):
    """Singleton model for platform commission percentages"""
    default_commission = models.DecimalField(max_digits=5, decimal_places=2, default=30.00, help_text="Normal teachers platform %")
    vip_commission = models.DecimalField(max_digits=5, decimal_places=2, default=20.00, help_text="VIP teachers platform %")
    internal_commission = models.DecimalField(max_digits=5, decimal_places=2, default=10.00, help_text="Internal teachers platform %")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'commission_settings'
        verbose_name_plural = "Commission Settings"

    @classmethod
    def load(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return "Global Commission Settings"



class Subject(models.Model):
    """Subject/Category Model for CMS"""
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True, blank=True, null=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, default="BookOpen", help_text="Lucide icon name")
    color = models.CharField(max_length=50, default="bg-blue-600", help_text="Tailwind class")
    xp_reward = models.IntegerField(default=50)
    is_featured = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True, help_text="Hide from public if False")
    order = models.IntegerField(default=0)
    teachers = models.ManyToManyField('User', related_name='subjects', limit_choices_to={'role': 'TEACHER'})
    
    class Meta:
        db_table = 'subjects'
        ordering = ['order', 'name']
    
    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Subject.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)
        
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
    admin = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, blank=True, related_name='created_courses', limit_choices_to={'role': 'ADMIN'})
    end_time = models.DateTimeField(null=True, blank=True) # Added end_time
    result_time = models.DateTimeField(blank=True, null=True, help_text="Time when results will be published") # Added result_time
    description = models.TextField()
    thumbnail = models.ImageField(upload_to='courses/', blank=True, null=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Revenue Split
    teacher_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=70.00)
    platform_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=30.00)

    level = models.CharField(max_length=15, choices=LEVEL_CHOICES, default='BEGINNER')
    subject = models.ForeignKey('Subject', on_delete=models.SET_NULL, null=True, related_name='courses')
    duration = models.CharField(max_length=50, blank=True, null=True, help_text="Duration in HH:MM:SS or minutes") # Modified duration
    lessons_count = models.IntegerField(default=0)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    students_count = models.IntegerField(default=0)
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    xp_reward = models.IntegerField(default=100, help_text="XP given upon completion")
    show_on_home = models.BooleanField(default=False)
    home_order = models.IntegerField(default=0)
    STATUS_CHOICES = [
        ('DRAFT', 'Qoralama'),
        ('PENDING', 'Kutilmoqda'),
        ('APPROVED', 'Tasdiqlangan'),
        ('REJECTED', 'Rad etilgan'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    LANGUAGE_CHOICES = [
        ('uz', "O'zbek"),
        ('ru', "Rus"),
        ('en', "Ingliz"),
    ]
    LOCK_STRATEGY_CHOICES = [
        ('free', 'Erkin (barcha darslar ochiq)'),
        ('sequential', 'Ketma-ket (oldingi tugaguncha keyingisi yopiq)'),
        ('custom', 'Maxsus (har darsda belgilangan)'),
    ]
    language = models.CharField(max_length=2, choices=LANGUAGE_CHOICES, default='uz')
    lock_strategy = models.CharField(max_length=20, choices=LOCK_STRATEGY_CHOICES, default='free')
    completion_min_progress = models.IntegerField(default=80, help_text="Kurs tugallandi hisoblash uchun minimal foiz")
    teacher = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, related_name='courses', limit_choices_to={'role': 'TEACHER'})
    teachers = models.ManyToManyField('User', related_name='co_teaching_courses', blank=True, limit_choices_to={'role': 'TEACHER'})
    
    # Advanced Settings
    is_certificate_enabled = models.BooleanField(default=False)
    certificate_template = models.CharField(max_length=100, blank=True, null=True, help_text="Template name or path")
    required_final_score = models.IntegerField(default=70, help_text="Sertifikat olish uchun yakuniy imtihondan kutilayotgan minimal ball")
    
    # Payment fields for course creation
    is_paid_creation = models.BooleanField(default=False, help_text="Whether this course requires a creation fee")
    creation_fee_paid = models.BooleanField(default=False, help_text="Whether teacher paid course creation fee")
    creation_fee_transaction = models.ForeignKey('Transaction', on_delete=models.SET_NULL, null=True, blank=True, related_name='course_creation_fees')
    
    is_internal = models.BooleanField(default=False, help_text="Platformaning o'z kursi")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.is_active:
            # Requirements for activating a course:
            # 1. At least 3 published lessons
            # 2. At least 1 demo lesson
            # 3. At least 1 lesson with a test
            if self.pk:
                published_lessons = self.lessons.filter(is_published=True)
                has_demo = published_lessons.filter(is_free=True).exists()
                has_test = published_lessons.filter(test__isnull=False).exists()
                lessons_count = published_lessons.count()

                errors = []
                if not self.teacher:
                    errors.append("Kursni aktivlashtirish uchun o'qituvchi biriktirilgan bo'lishi shart.")
                
                if self.status != 'APPROVED':
                    errors.append("Kursni aktivlashtirish uchun u avval admin tomonidan tasdiqlanishi (APPROVED) kerak.")
                if lessons_count < 3:
                    errors.append("Kursda kamida 3 ta nashr qilingan dars bo'lishi shart.")
                if not has_demo:
                    errors.append("Kursda kamida 1 ta demo (bepul) dars bo'lishi shart.")
                if not has_test:
                    errors.append("Kursda kamida 1 ta testli dars bo'lishi shart.")

                if errors:
                    raise ValidationError(" \n".join(errors))
        super().clean()

    def __str__(self):
        return self.title


class Module(models.Model):
    """Course Module (Section)"""
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='modules')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    order = models.IntegerField(default=0)
    xp_reward = models.IntegerField(default=30, help_text="XP awarded for completing all lessons in this module")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'modules'
        ordering = ['order']

    def __str__(self):
        return f"{self.course.title} - {self.title}"


class LiveLesson(models.Model):
    """Weekly Live Lesson (Google Meet)"""
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='live_lessons')
    title = models.CharField(max_length=200)
    topic = models.TextField(blank=True)
    start_time = models.DateTimeField()
    meet_link = models.URLField(help_text="Google Meet link")
    is_completed = models.BooleanField(default=False)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, limit_choices_to={'role': 'TEACHER'})
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'live_lessons'
        ordering = ['-start_time']

    def __str__(self):
        return f"{self.course.title} - {self.title} ({self.start_time})"


class Lesson(models.Model):
    """Lesson Model (Updated for v2)"""
    COURSE_TYPES = [
        ('VIDEO', 'Video Dars'),
        ('ARTICLE', 'Maqola'),
        ('QUIZ', 'Test'),
    ]
    
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='lessons')
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='lessons', null=True, blank=True)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Video Content
    video_url = models.URLField(blank=True, null=True, help_text="Direct video URL if not YouTube")
    youtube_id = models.CharField(max_length=50, blank=True, null=True, help_text="YouTube Video ID (e.g. _GjgFMGQg40)")
    video_type = models.CharField(max_length=20, default='YOUTUBE') # YOUTUBE, UPLOAD
    video_duration = models.IntegerField(default=0, help_text="Duration in seconds")
    
    # Files
    pdf_url = models.URLField(blank=True, null=True)
    
    # Logic
    order = models.IntegerField(default=0)
    is_free = models.BooleanField(default=False)
    is_published = models.BooleanField(default=True)
    is_locked = models.BooleanField(default=False, help_text="Agar True bo'lsa, oldingi dars tugaguncha yopiq")
    required_lesson = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='unlocks_lessons',
        help_text="Bu dars tugamasdan yuqoridagi dars ochilmaydi"
    )
    xp_amount = models.IntegerField(default=10, help_text="XP awarded for completing this lesson")
    min_watch_percent = models.IntegerField(default=80, help_text="Dars tugallangan hisoblanishi uchun minimal ko'rish foizi")
    
    teacher = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='lessons_assigned', limit_choices_to={'role': 'TEACHER'})
    
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        from .utils import extract_youtube_id
        # Automatically extract youtube_id if not present but video_url is
        if self.video_url and not self.youtube_id:
            y_id = extract_youtube_id(self.video_url)
            if y_id:
                self.youtube_id = y_id
                self.video_type = 'YOUTUBE'
        super().save(*args, **kwargs)

    class Meta:
        db_table = 'lessons'
        ordering = ['module__order', 'order']
    
    def __str__(self):
        return f"{self.course.title} - {self.title}"


class LessonContent(models.Model):
    """Rich content for a lesson added by Teacher"""
    lesson = models.OneToOneField(Lesson, on_delete=models.CASCADE, related_name='content')
    text_content = models.TextField(blank=True)
    resources_file = models.FileField(upload_to='lessons/resources/', blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, limit_choices_to={'role': 'TEACHER'})
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'lesson_contents'

    def __str__(self):
        return f"Content for: {self.lesson.title}"


class Homework(models.Model):
    """Homework assigned to a lesson"""
    lesson = models.OneToOneField(Lesson, on_delete=models.CASCADE, related_name='homework')
    title = models.CharField(max_length=200)
    description = models.TextField()
    deadline = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'homeworks'

    def __str__(self):
        return self.title


class HomeworkSubmission(models.Model):
    """Student submission for homework"""
    STATUS_CHOICES = [
        ('PENDING', 'Kutilmoqda'),
        ('GRADED', 'Baholangan'),
        ('REJECTED', 'Rad etilgan'),
    ]
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='homework_submissions')
    homework = models.ForeignKey(Homework, on_delete=models.CASCADE, related_name='submissions')
    file_url = models.FileField(upload_to='homework/submissions/')
    grade = models.IntegerField(null=True, blank=True)
    feedback = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'homework_submissions'


class LessonPractice(models.Model):
    """Practice Section for a Lesson"""
    TYPE_CHOICES = [
        ('CODE', 'Coding Challenge'),
        ('MATH', 'Math Problem'),
        ('TEXT', 'Text Answer'),
        ('UPLOAD', 'File Upload'),
    ]
    
    lesson = models.OneToOneField(Lesson, on_delete=models.CASCADE, related_name='practice')
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='TEXT')
    problem_text = models.TextField()
    correct_answer = models.TextField(blank=True, null=True, help_text="For auto-checking text/math")
    test_cases = models.JSONField(blank=True, null=True, help_text="For code runner")
    points = models.IntegerField(default=10)
    
    class Meta:
        db_table = 'lesson_practices'


class LessonTest(models.Model):
    """Mini-test for a Lesson"""
    lesson = models.OneToOneField(Lesson, on_delete=models.CASCADE, related_name='test')
    questions = models.ManyToManyField('Question', related_name='lesson_tests')
    min_pass_score = models.IntegerField(default=70, help_text="Percentage 0-100")
    is_final = models.BooleanField(default=False, help_text="Agar True bo'lsa, bu kursning yakuniy imtihoni hisoblanadi")
    max_attempts = models.IntegerField(default=3)
    
    class Meta:
        db_table = 'lesson_tests'


class LessonProgress(models.Model):
    """Granular Progress Tracking"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='lesson_progress')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='user_progress')
    
    is_video_watched = models.BooleanField(default=False)
    video_last_position = models.IntegerField(default=0, help_text="Seconds watched")
    
    practice_score = models.IntegerField(null=True, blank=True)
    practice_submission = models.TextField(blank=True, null=True)
    
    test_score = models.IntegerField(null=True, blank=True)
    test_attempts = models.IntegerField(default=0)
    
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        db_table = 'lesson_progress'
        unique_together = ['user', 'lesson']


class Enrollment(models.Model):
    """Course Enrollment"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='enrollments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    progress = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    completed_at = models.DateTimeField(blank=True, null=True)
    current_lesson = models.ForeignKey(Lesson, on_delete=models.SET_NULL, null=True, blank=True, related_name='current_learners')
    last_accessed_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'enrollments'
        unique_together = ['user', 'course']
    
    def __str__(self):
        return f"{self.user.username} - {self.course.title}"



class Olympiad(models.Model):
    STATUS_CHOICES = [
        ('DRAFT', 'Qoralama'),
        ('PENDING', 'Kutilmoqda'),
        ('APPROVED', 'Tasdiqlangan'),
        ('REGISTRATION_OPEN', 'Ro\'yxatga olish boshlandi'),
        ('REGISTRATION_CLOSED', 'Ro\'yxatdan o\'tish tugadi'),
        ('ONGOING', 'Olimpiada boshladi'),
        ('CHECKING', 'Tekshirilmoqda'),
        ('PUBLISHED', 'Natijalar e\'lon qilindi'),
    ]

    LEVEL_CHOICES = [
        ('BEGINNER', 'Boshlang\'ich'),
        ('INTERMEDIATE', 'O\'rta'),
        ('ADVANCED', 'Murakkab'),
    ]
    
    DIFFICULTY_CHOICES = [
        ('EASY', 'Oson'),
        ('MEDIUM', 'O\'rta'),
        ('HARD', 'Qiyin'),
    ]

    FORMAT_CHOICES = [
        ('ONLINE', 'Online'),
        ('LIVE', 'Live'),
        ('HYBRID', 'Hybrid'),
    ]
    
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=255, unique=True, blank=True, null=True) # Allow blank for auto-gen
    description = models.TextField(blank=True, null=True)
    subject = models.CharField(max_length=100, blank=True, null=True) # Optional now
    subject_id = models.ForeignKey('Subject', on_delete=models.SET_NULL, null=True, blank=True, related_name='olympiads_api')
    profession = models.ForeignKey('Profession', on_delete=models.SET_NULL, null=True, blank=True, related_name='olympiads')
    course = models.ForeignKey('Course', on_delete=models.SET_NULL, null=True, blank=True, related_name='olympiads')
    thumbnail = models.ImageField(upload_to='olympiads/', blank=True, null=True)
    
    # Content
    rules = models.TextField(blank=True, help_text="HTML/Markdown content")
    evaluation_criteria = models.TextField(blank=True, help_text="HTML/Markdown content")

    # Schedule
    registration_start = models.DateTimeField(null=True, blank=True)
    registration_end = models.DateTimeField(null=True, blank=True)
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    result_time = models.DateTimeField(blank=True, null=True, help_text="Time when results will be published")
    duration = models.IntegerField(default=60, help_text="Duration in minutes")
    
    # Participants config
    max_participants = models.IntegerField(blank=True, null=True)
    grade_range = models.CharField(max_length=50, blank=True, help_text="e.g. 5-6, 7-9, 10-11")
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default='BEGINNER') # Keep for legacy/grouping
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, default='MEDIUM')
    
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='DRAFT')
    
    format = models.CharField(max_length=20, choices=FORMAT_CHOICES, default='ONLINE')
    
    # Payment
    is_paid = models.BooleanField(default=False)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default='UZS')
    discount_percent = models.IntegerField(default=0)

    # Limits & Security
    max_attempts = models.IntegerField(default=1)
    tab_switch_limit = models.IntegerField(default=3, help_text="Max allowed tab switches before auto-submit")
    time_limit_per_question = models.IntegerField(default=0, help_text="Seconds per question (0 = no limit)")
    is_random = models.BooleanField(default=False, help_text="Randomize question order")
    cannot_go_back = models.BooleanField(default=False, help_text="Prevent going back to previous questions")
    required_camera = models.BooleanField(default=False, help_text="Require camera access")
    required_full_screen = models.BooleanField(default=False, help_text="Force full screen mode")
    disable_copy_paste = models.BooleanField(default=False, help_text="Disable copy/paste functionality")
    allowed_ip_range = models.CharField(max_length=200, blank=True, null=True, help_text="Comma separated IPs or CIDR")

    is_active = models.BooleanField(default=True)
    xp_reward = models.IntegerField(default=150, help_text="XP given for participation (finishing test)")
    winner_xp = models.IntegerField(default=400, help_text="Extra XP for 1st place/Winners")
    show_on_home = models.BooleanField(default=False)
    home_order = models.IntegerField(default=0)
    teacher = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, related_name='olympiads', limit_choices_to={'role': 'TEACHER'})
    checker = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, blank=True, related_name='checking_olympiads', limit_choices_to={'role': 'TEACHER'})
    moderator = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, blank=True, related_name='moderated_olympiads', limit_choices_to={'role': 'TEACHER'})
    
    # Rewards Config
    REWARD_STRATEGY_CHOICES = [
        ('TOP_N', 'Top g\'oliblar bo\'yicha'),
        ('THRESHOLD', 'Ball foizi bo\'yicha'),
        ('MANUAL', 'Qo\'lda'),
    ]
    reward_strategy = models.CharField(max_length=20, choices=REWARD_STRATEGY_CHOICES, default='MANUAL')
    auto_reward = models.BooleanField(default=False, help_text="Olimpiada tugagach sovrinlarni avto yuborish")
    
    DISTRIBUTION_STATUS_CHOICES = [
        ('PENDING', 'Kutilmoqda'),
        ('IN_PROGRESS', 'Jarayonda'),
        ('COMPLETED', 'Yakunlandi'),
        ('FAILED', 'Xatolik'),
    ]
    reward_distribution_status = models.CharField(max_length=20, choices=DISTRIBUTION_STATUS_CHOICES, default='PENDING')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def refresh_status(self):
        """Automatically refresh status based on dates"""
        from django.utils import timezone
        now = timezone.now()
        
        # Only auto-refresh if status is in a "trackable" state
        if self.status in ['PAUSED', 'CANCELED', 'PUBLISHED', 'COMPLETED', 'DRAFT']:
            return self.status

        # If dates are missing, we cannot auto-refresh accurately
        if not self.start_date or not self.end_date:
            return self.status

        # Sequence of time-based status transitions
        if self.registration_start and now < self.registration_start:
            new_status = 'UPCOMING'
        elif self.registration_start and self.registration_end and self.registration_start <= now <= self.registration_end:
            new_status = 'REGISTRATION_OPEN'
        elif now < self.start_date:
            new_status = 'UPCOMING' # Or REGISTRATION_CLOSED if after reg_end
        elif self.start_date <= now <= self.end_date:
            new_status = 'ONGOING'
        else:
            # After end_date, if not already PUBLISHED or COMPLETED, it's CHECKING
            new_status = 'CHECKING'

        if self.status != new_status:
            self.status = new_status
            self.save(update_fields=['status'])
        
        return self.status

    def clean(self):
        from django.core.exceptions import ValidationError
        activation_statuses = ['PUBLISHED', 'UPCOMING', 'ONGOING']
        if self.status in activation_statuses and self.pk:
            if not self.questions.exists():
                raise ValidationError("Savollar qo'shilmagan olimpiadani aktivlashtirib bo'lmaydi.")
        super().clean()

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while Olympiad.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)
    
    class Meta:
        db_table = 'olympiads'
        ordering = ['-start_date']
    
    # Extended Settings
    is_paid_creation = models.BooleanField(default=False, help_text="Whether this olympiad requires a creation fee")
    creation_fee_paid = models.BooleanField(default=False, help_text="Whether teacher paid olympiad creation fee")
    creation_fee_transaction = models.ForeignKey('Transaction', on_delete=models.SET_NULL, null=True, blank=True, related_name='olympiad_creation_fees')
    eligibility_grades = models.JSONField(blank=True, null=True, help_text="List of eligible grades, e.g. [7, 8, 9]")
    eligibility_regions = models.JSONField(blank=True, null=True, help_text="List of eligible regions")
    technical_config = models.JSONField(blank=True, null=True, help_text="Technical constraints like tab_limit")
    certificate_config = models.JSONField(blank=True, null=True, help_text="Certificate generation settings")

    def __str__(self):
        return self.title


class OlympiadPrize(models.Model):
    """Prizes for Olympiad Winners"""
    PRIZE_TYPES = [
        ('PHYSICAL', 'Fizik sovrin (Medal, Kitob...)'),
        ('COIN', 'Hogwords Coin'),
        ('XP', 'Tajriba balli (XP)'),
    ]
    
    olympiad = models.ForeignKey(Olympiad, on_delete=models.CASCADE, related_name='prizes')
    name = models.CharField(max_length=255)
    prize_type = models.CharField(max_length=20, choices=PRIZE_TYPES, default='PHYSICAL')
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Coin yoki XP miqdori")
    target_value = models.IntegerField(default=1, help_text="1-o'rin uchun 1, yoki Threshold uchun ball foizi (80, 90...)")
    image = models.ImageField(upload_to='olympiad_prizes/', blank=True, null=True)
    description = models.TextField(blank=True)
    
    class Meta:
        db_table = 'olympiad_prizes'
        ordering = ['id']
    
    def __str__(self):
        return f"{self.olympiad.title} - {self.name}"


class Question(models.Model):
    """Olympiad Question"""
    TYPE_CHOICES = [
        ('MCQ', 'Multiple Choice'),
        ('NUMERIC', 'Numeric Answer'),
        ('TEXT', 'Text Answer'),
        ('CODE', 'Code Submission'),
    ]

    olympiad = models.ForeignKey(Olympiad, on_delete=models.CASCADE, related_name='questions', null=True, blank=True)
    text = models.TextField()
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='MCQ')
    options = models.JSONField(blank=True, null=True)  # ["A variant", ...] for MCQ
    correct_answer = models.TextField(help_text="Index for MCQ, number/text for others") 
    explanation = models.TextField(blank=True, help_text="Explanation shown after test")
    points = models.IntegerField(default=1)
    time_limit = models.IntegerField(default=0, help_text="Seconds for this specific question (0=none)")
    code_template = models.TextField(blank=True, null=True, help_text="Starter code for CODE questions")
    order = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'questions'
        ordering = ['order']
    
    def __str__(self):
        return f"{self.olympiad.title} - Q{self.order}"


class WinnerPrize(models.Model):
    """Specific prize awarded to a student after an olympiad"""
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('CONTACTED', 'Contacted'),
        ('ADDRESS_RECEIVED', 'Address received'),
        ('SHIPPED', 'Shipped'),
        ('COMPLETED', 'Completed'),
    ]

    olympiad = models.ForeignKey(Olympiad, on_delete=models.CASCADE, related_name='winners_prizes')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='won_prizes')
    position = models.IntegerField(help_text="1, 2 or 3")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    prize_item = models.ForeignKey(OlympiadPrize, on_delete=models.SET_NULL, null=True, blank=True)
    awarded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'winner_prizes'
        ordering = ['position']
        unique_together = ['olympiad', 'student']

    def __str__(self):
        return f"{self.student.username} - {self.olympiad.title} ({self.position}-o'rin)"


class PrizeAddress(models.Model):
    """Shipping information collected via Telegram"""
    prize = models.OneToOneField(WinnerPrize, on_delete=models.CASCADE, related_name='address')
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    address_text = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'prize_addresses'

    def __str__(self):
        return f"Address for {self.prize.student.username}"


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
    answers = models.JSONField(default=dict)  # {question_id: answer_value}
    score = models.IntegerField(default=0)
    percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    time_taken = models.IntegerField(default=0, help_text="Time in seconds")
    
    # Anti-cheat stats
    tab_switches_count = models.IntegerField(default=0)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    device_info = models.TextField(blank=True, null=True)
    
    status = models.CharField(max_length=20, default='COMPLETED') # IN_PROGRESS, COMPLETED, DISQUALIFIED, CHECKING
    disqualified_reason = models.TextField(blank=True, null=True)
    feedback = models.TextField(blank=True, null=True, help_text="Teacher's feedback for the student")
    submitted_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'test_results'
        unique_together = ['user', 'olympiad']
    
    def __str__(self):
        return f"{self.user.username} - {self.olympiad.title}: {self.score}"


class Certificate(models.Model):
    """Certificate Model - Enhanced with types, verification, and PDF support"""
    TYPE_CHOICES = [
        ('COURSE', 'Kurs sertifikati'),
        ('OLYMPIAD', 'Olimpiada sertifikati'),
        ('DIPLOMA', 'Diplom / Faxriy yorliq'),
    ]
    STATUS_CHOICES = [
        ('PENDING', 'Kutilmoqda'),
        ('VERIFIED', 'Tasdiqlangan'),
        ('REJECTED', 'Rad etilgan'),
    ]
    
    # Core fields
    cert_number = models.CharField(max_length=20, unique=True, blank=True)
    cert_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='COURSE')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='certificates')
    course = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True, blank=True)
    olympiad = models.ForeignKey(Olympiad, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Results
    grade = models.CharField(max_length=50, help_text="98% yoki 1-o'rin")
    score = models.IntegerField(default=0, help_text="Umumiy ball")
    
    # Dates
    issued_at = models.DateTimeField(auto_now_add=True)
    
    # Verification
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='PENDING')
    verified_at = models.DateTimeField(blank=True, null=True)
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_certificates')
    rejection_reason = models.TextField(blank=True, help_text="Rad etish sababi")
    
    # Files
    qr_code = models.ImageField(upload_to='certificates/qr/', blank=True, null=True)
    pdf_file = models.FileField(upload_to='certificates/pdf/', blank=True, null=True)
    
    class Meta:
        db_table = 'certificates'
        ordering = ['-issued_at']
    
    def save(self, *args, **kwargs):
        if not self.cert_number:
            # Generate unique cert number: CRT-XXXX
            import random
            while True:
                num = f"CRT-{random.randint(1000, 9999)}"
                if not Certificate.objects.filter(cert_number=num).exists():
                    self.cert_number = num
                    break
        
        # Check if status is becoming VERIFIED
        was_verified = False
        if self.pk:
            old_self = Certificate.objects.get(pk=self.pk)
            was_verified = old_self.status == 'VERIFIED'
        
        super().save(*args, **kwargs)

        if self.status == 'VERIFIED' and not was_verified:
            from .services.notification_service import NotificationService
            NotificationService.create_notification(
                user=self.user,
                title="Sertifikat tayyor!",
                message=f"Tabriklaymiz! Sizning '{self.title}' bo'yicha sertifikatingiz tasdiqlandi.",
                notification_type='ACHIEVEMENT',
                link=f"/profile"
            )
    
    def __str__(self):
        return f"{self.cert_number} - {self.user.username}"
    
    @property
    def title(self):
        """Return course or olympiad title"""
        if self.course:
            return self.course.title
        elif self.olympiad:
            return self.olympiad.title
        return "Sertifikat"
    
    @property
    def verify_url(self):
        """Public verification URL"""
        return f"/certificate/verify/{self.cert_number}"


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
    amount = models.DecimalField(max_digits=12, decimal_places=2)  # This will be FINAL Amount
    original_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    unique_add = models.IntegerField(default=0)
    final_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    expires_at = models.DateTimeField(blank=True, null=True)
    type = models.CharField(max_length=50)  # COURSE, OLYMPIAD, COURSE_CREATION_FEE, TOPUP
    reference_id = models.CharField(max_length=50, blank=True, null=True)
    method = models.CharField(max_length=20)  # PAYME, CLICK, UZCARD
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='PENDING')
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    receipt_image = models.ImageField(upload_to='payment_receipts/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    admin_message_ids = models.JSONField(default=list, blank=True)
    
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
    admin_chat_id = models.CharField(max_length=500, default="0", help_text="Comma separated admin chat IDs")
    humo_bot_url = models.CharField(max_length=255, default="https://t.me/ardentsoft_olimpiada_bot", blank=True, null=True)
    click_merchant_id = models.CharField(max_length=50, blank=True, null=True)
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
    
    @property
    def is_active_today(self):
        """Returns True if user has already recorded activity today"""
        if not self.last_activity_date:
            return False
        from django.utils import timezone
        return self.last_activity_date == timezone.localdate()

    @property
    def seconds_until_reset(self):
        """Returns seconds until midnight when streak will reset"""
        from django.utils import timezone
        from datetime import datetime, time, timedelta
        
        # If user is active today, we show time until NEXT midnight
        # If user NOT active today, we show time until THIS midnight
        
        now = timezone.now()
        local_now = timezone.localtime(now)
        
        # Calculate next midnight
        next_midnight = datetime.combine(local_now.date() + timedelta(days=1), time.min)
        next_midnight = timezone.make_aware(next_midnight, timezone.get_current_timezone())
        
        diff = next_midnight - local_now
        return int(diff.total_seconds())

    @property
    def time_since_last(self):
        """Returns hours since last recorded activity (or since updated_at)"""
        if not self.last_activity_date:
            return 24
            
        from django.utils import timezone
        today = timezone.localdate()
        if self.last_activity_date == today:
            # Already active today, not in danger
            return 0
            
        now = timezone.now()
        diff = now - self.updated_at
        return int(diff.total_seconds() // 3600)

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



class Banner(models.Model):
    """Homepage Hero Banner Slider"""
    title = models.CharField(max_length=200)
    subtitle = models.TextField(blank=True)
    image = models.ImageField(upload_to='banners/')
    mobile_image = models.ImageField(upload_to='banners/', blank=True, null=True)
    button_text = models.CharField(max_length=50, blank=True)
    button_link = models.CharField(max_length=200, blank=True)
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'banners'
        ordering = ['order', '-created_at']

    def __str__(self):
        return self.title


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

    # Teaser Section Configuration
    teaser_title_uz = models.CharField(max_length=200, default="Sun'iy Intellekt va Data Science")
    teaser_title_ru = models.CharField(max_length=200, default="Искусственный Интеллект и Data Science")
    teaser_subtitle_uz = models.TextField(default="Zamonaviy kasblarni o'rganing. Yangi kurslarimiz ustida qizg'in ish olib boryapmiz.")
    teaser_subtitle_ru = models.TextField(default="Изучайте современные профессии. Мы активно работаем над нашими новыми курсами.")
    teaser_image = models.ImageField(upload_to='homepage/teaser/', blank=True, null=True, help_text="Tavsiya etilgan o'lcham: 1200x400px. Format: JPG, PNG.")
    teaser_button_text_uz = models.CharField(max_length=50, default="Xabardor bo'lish")
    teaser_button_text_ru = models.CharField(max_length=50, default="Узнать больше")
    teaser_button_link = models.CharField(max_length=200, default="/auth/register")
    
    # Section Toggles
    show_stats = models.BooleanField(default=True)
    show_olympiads = models.BooleanField(default=True)
    show_courses = models.BooleanField(default=True)
    show_professions = models.BooleanField(default=True)
    show_testimonials = models.BooleanField(default=True)
    show_mentors = models.BooleanField(default=True)
    show_winners = models.BooleanField(default=True)
    show_steps = models.BooleanField(default=True)
    show_cta = models.BooleanField(default=True)
    show_faq = models.BooleanField(default=True)
    
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


class FreeCourseSection(models.Model):
    """Free Courses Section CMS"""
    title_uz = models.CharField(max_length=200, default="MUTLAQO BEPUL")
    title_ru = models.CharField(max_length=200, default="АБСОЛЮТНО БЕСПЛАТНО")
    subtitle_uz = models.CharField(max_length=300, default="O'rganishni hoziroq boshlang")
    subtitle_ru = models.CharField(max_length=300, default="Начните учиться прямо сейчас")
    description_uz = models.TextField(default="Hech qanday to'lovsiz, ro'yxatdan o'tmasdan ham ko'rishingiz mumkin bo'lgan darslar.")
    description_ru = models.TextField(default="Уроки, которые вы можете посмотреть без какой-либо оплаты, даже без регистрации.")
    button_text_uz = models.CharField(max_length=100, default="Barcha bepul darslar")
    button_text_ru = models.CharField(max_length=100, default="Все бесплатные уроки")
    button_link = models.CharField(max_length=255, default="/courses?filter=free")
    is_active = models.BooleanField(default=True)
    show_on_homepage = models.BooleanField(default=True)
    order = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'free_course_section'
        verbose_name = 'Free Course Section'
        verbose_name_plural = 'Free Course Sections'
        ordering = ['order']
        
    def __str__(self):
        return f"Free Course Section - {self.title_uz}"


class FreeCourseLessonCard(models.Model):
    """Free Course Lesson Cards for Homepage"""
    title_uz = models.CharField(max_length=200)
    title_ru = models.CharField(max_length=200)
    category_uz = models.CharField(max_length=100, default="Boshlang'ich")
    category_ru = models.CharField(max_length=100, default="Начальный")
    image = models.URLField(max_length=500, help_text="Image URL for the course card")
    duration_minutes = models.IntegerField(default=30, help_text="Duration in minutes")
    link = models.CharField(max_length=255, default="/auth/register", help_text="Link when card is clicked")
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'free_course_lesson_cards'
        verbose_name = 'Free Course Lesson Card'
        verbose_name_plural = 'Free Course Lesson Cards'
        ordering = ['order', '-created_at']
        
    def __str__(self):
        return f"{self.title_uz} - {self.category_uz}"



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
    
    # Identity Verification
    is_identity_verified = models.BooleanField(default=False)
    identity_document = models.ImageField(upload_to='teacher_docs/', blank=True, null=True)
    
    # Verification
    VERIFICATION_STATUS = [
        ('PENDING', 'Pending Verification'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('BLOCKED', 'Blocked')
    ]
    verification_status = models.CharField(max_length=20, choices=VERIFICATION_STATUS, default='PENDING')
    rejection_reason = models.TextField(blank=True, null=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_teachers')
    
    # Tiered Teacher System
    TEACHER_TYPES = [
        ('NORMAL', 'Oddiy'),
        ('VIP', 'VIP'),
        ('INTERNAL', 'Internal (Platforma)'),
    ]
    teacher_type = models.CharField(max_length=20, choices=TEACHER_TYPES, default='NORMAL')
    vip_expire_date = models.DateTimeField(null=True, blank=True)
    is_lifetime_vip = models.BooleanField(default=False)
    
    # Premium subscription (Legacy, can be mapped to VIP)
    is_premium = models.BooleanField(default=False, help_text="Premium teachers can create unlimited courses")
    
    updated_at = models.DateTimeField(auto_now=True)
    
    @property
    def is_vip(self):
        if self.teacher_type == 'VIP':
            if self.is_lifetime_vip:
                return True
            from django.utils import timezone
            if self.vip_expire_date and self.vip_expire_date > timezone.now():
                return True
            return False
        return False

    @property
    def is_internal(self):
        return self.teacher_type == 'INTERNAL'
    
    class Meta:
        db_table = 'teacher_profiles'
    
    def __str__(self):
        return f"{self.user.username} - Teacher Profile"

class TeacherWallet(models.Model):
    """Teacher Wallet for managing earnings and payouts"""
    teacher = models.OneToOneField(User, on_delete=models.CASCADE, related_name='teacher_wallet', limit_choices_to={'role': 'TEACHER'})
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Available for withdrawal")
    pending_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Locked for 7 days after sale")
    total_earned = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Lifetime earnings")
    total_withdrawn = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Total payouts received")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'teacher_wallets'
    
    def __str__(self):
        return f"{self.teacher.username} - Wallet"


class VIPLog(models.Model):
    """Logs for VIP status changes"""
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name='vip_logs')
    given_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='given_vips')
    prev_type = models.CharField(max_length=20)
    new_type = models.CharField(max_length=20)
    duration_days = models.IntegerField(null=True, blank=True)
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'vip_logs'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.teacher.username}: {self.prev_type} -> {self.new_type}"

class Transaction(models.Model):
    """Transaction history for all wallet operations"""
    TRANSACTION_TYPES = [
        ('COURSE_CREATION_FEE', 'Course Creation Fee'),
        ('COURSE_SALE', 'Course Sale'),
        ('COMMISSION', 'Platform Commission'),
        ('PAYOUT', 'Payout to Teacher'),
        ('REFUND', 'Refund'),
        ('OLYMPIAD_REWARD', 'Olympiad Reward'),
        ('STREAK_REWARD', 'Streak Reward'),
    ]
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
        ('REFUNDED', 'Refunded'),
    ]
    
    transaction_type = models.CharField(max_length=30, choices=TRANSACTION_TYPES)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    course = models.ForeignKey('Course', on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    platform_commission = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    teacher_earnings = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    payment_provider = models.CharField(max_length=50, null=True, blank=True, help_text="click, payme, etc")
    payment_id = models.CharField(max_length=255, null=True, blank=True, help_text="External payment ID")
    description = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True, help_text="Additional transaction data")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'transactions'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.amount} - {self.user.username}"

class Payout(models.Model):
    """Payout requests from teachers"""
    STATUS_CHOICES = [
        ('REQUESTED', 'Requested'),
        ('APPROVED', 'Approved'),
        ('PAID', 'Paid'),
        ('REJECTED', 'Rejected'),
    ]
    
    PAYMENT_METHODS = [
        ('CARD', 'Bank Card'),
        ('CLICK', 'Click'),
        ('PAYME', 'Payme'),
    ]
    
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payouts', limit_choices_to={'role': 'TEACHER'})
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='REQUESTED')
    payment_method = models.CharField(max_length=50, choices=PAYMENT_METHODS)
    payment_details = models.JSONField(help_text="Card number, phone, account details")
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_payouts')
    approved_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    notes = models.TextField(blank=True, help_text="Admin notes")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'payouts'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Payout {self.id} - {self.teacher.username} - {self.amount} - {self.status}"

class NotificationTemplate(models.Model):
    """Reusable message templates for common notifications"""
    name = models.CharField(max_length=100)
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, default='SYSTEM')
    channel = models.CharField(max_length=20, default='WEB')
    link = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'notification_templates'

    def __str__(self):
        return self.name

class NotificationBroadcast(models.Model):
    """Mass notification broadcast history"""
    AUDIENCE_CHOICES = [
        ('ALL', 'Barcha foydalanuvchilar'),
        ('STUDENTS', 'Talabalar'),
        ('TEACHERS', 'Oʻqituvchilar'),
        ('COURSE_STUDENTS', 'Kurs oʻquvchilari'),
        ('OLYMPIAD_PARTICIPANTS', 'Olimpiada qatnashchilari'),
        ('INACTIVE', 'Faol boʻlmaganlar (7+ kun)'),
        ('NEW', 'Yangi foydalanuvchilar (24+ soat)'),
    ]
    STATUS_CHOICES = [
        ('PENDING', 'Kutilmoqda'),
        ('IN_PROGRESS', 'Jarayonda'),
        ('SENT', 'Yuborildi'),
        ('FAILED', 'Xatolik'),
    ]

    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, default='SYSTEM')
    channel = models.CharField(max_length=20, default='WEB')
    link = models.CharField(max_length=255, blank=True, null=True)
    
    audience_type = models.CharField(max_length=30, choices=AUDIENCE_CHOICES, default='ALL')
    course = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True, blank=True)
    olympiad = models.ForeignKey(Olympiad, on_delete=models.SET_NULL, null=True, blank=True)
    
    scheduled_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    total_recipients = models.IntegerField(default=0)
    read_count = models.IntegerField(default=0)
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'notification_broadcasts'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.audience_type})"

class Notification(models.Model):
    """System Notifications for Users"""
    TYPE_CHOICES = [
        ('SYSTEM', 'System Message'),
        ('PAYMENT', 'Payment Update'),
        ('ACHIEVEMENT', 'Achievement Unlocked'),
        ('COURSE', 'Course Status Update'),
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
    broadcast = models.ForeignKey(NotificationBroadcast, on_delete=models.SET_NULL, null=True, blank=True, related_name='delivered_notifications')
    link = models.CharField(max_length=255, blank=True, null=True, help_text="Link to redirect user")

    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.user.username}"

class Profession(models.Model):
    """Career/Profession Model (e.g. Developer, Engineer)"""
    name = models.CharField(max_length=100)
    description = models.TextField()
    icon = models.CharField(max_length=50, default="Briefcase", help_text="Lucide icon name")
    color = models.CharField(max_length=50, default="bg-indigo-600", help_text="Tailwind class")
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)
    
    # Career Engine enhancements
    slug = models.SlugField(max_length=100, blank=True, null=True, unique=True)
    prestige_only = models.BooleanField(default=False)
    primary_subject = models.ForeignKey('Subject', on_delete=models.SET_NULL, null=True, blank=True, related_name='professions_featured')
    required_xp = models.IntegerField(default=0, help_text="Kasbni ochish uchun kerakli XP")
    total_required_xp = models.IntegerField(default=0, help_text="Kasb uchun umumiy talab qilingan XP")
    
    # Roadmap / Career Info
    suitability = models.TextField(blank=True, help_text="Kimlar uchun mos")
    requirements = models.TextField(blank=True, help_text="Boshlash uchun talablar")
    salary_range = models.CharField(max_length=100, blank=True, help_text="Taxminiy daromad")
    learning_time = models.CharField(max_length=100, blank=True, help_text="O'rganish vaqti")
    certification_info = models.TextField(blank=True, help_text="Sertifikat haqida")
    career_opportunities = models.TextField(blank=True, help_text="Qaysi ishlarda ishlash mumkin")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'professions'
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

class ProfessionSubject(models.Model):
    """Linking Subjects to Professions with importance level"""
    profession = models.ForeignKey(Profession, on_delete=models.CASCADE, related_name='required_subjects')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='profession_links')
    importance = models.IntegerField(default=3, help_text="1-5 stars")
    percentage = models.IntegerField(default=50, help_text="How much this subject is needed (0-100)")
    order = models.IntegerField(default=0)

    class Meta:
        db_table = 'profession_subjects'
        ordering = ['order']
        unique_together = ['profession', 'subject']

    def __str__(self):
        return f"{self.profession.name} - {self.subject.name}"


class ProfessionRoadmapStep(models.Model):
    """Career Roadmap Steps"""
    STEP_TYPES = [
        ('LEARN', 'O\'rganish'),
        ('PRACTICE', 'Amaliyot'),
        ('COMPETE', 'Olimpiada'),
        ('PROJECT', 'Loyiha'),
        ('CERTIFY', 'Sertifikat'),
    ]

    profession = models.ForeignKey(Profession, on_delete=models.CASCADE, related_name='roadmap_steps')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    step_type = models.CharField(max_length=20, choices=STEP_TYPES, default='LEARN')
    course = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True, blank=True, related_name='roadmap_steps')
    olympiad = models.ForeignKey('Olympiad', on_delete=models.SET_NULL, null=True, blank=True, related_name='roadmap_steps')
    required_xp = models.IntegerField(default=0, help_text="Ushbu qadam uchun kerakli XP")
    is_mandatory = models.BooleanField(default=True)
    order = models.IntegerField(default=0)

    class Meta:
        db_table = 'profession_roadmap_steps'
        ordering = ['order']

    def __str__(self):
        return f"{self.profession.name} Step {self.order}: {self.title}"

class UserProfessionProgress(models.Model):
    """Tracking user progress in a profession roadmap"""
    STATUS_CHOICES = [
        ('FOLLOWING', 'Kuzatmoqda'),
        ('COMPLETED', 'Tugatgan'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='profession_progress')
    profession = models.ForeignKey(Profession, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='FOLLOWING')
    progress_percent = models.IntegerField(default=0)
    started_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_profession_progress'
        unique_together = ['user', 'profession']

    def __str__(self):
        return f"{self.user.username} - {self.profession.name} ({self.progress_percent}%)"


class ProfessionLevel(models.Model):
    """Career Level within a Profession (e.g. Apprentice, Adept, Master)"""
    profession = models.ForeignKey(Profession, on_delete=models.CASCADE, related_name='levels')
    level_number = models.IntegerField()
    title = models.CharField(max_length=100)
    unlock_xp = models.IntegerField(default=0, help_text="Ushbu levelni ochish uchun talab etiladigan XP")
    order = models.IntegerField(default=0)
    is_prestige_only = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'profession_levels'
        ordering = ['profession', 'order', 'level_number']
        
    def __str__(self):
        return f"{self.profession.name} - Level {self.level_number}: {self.title}"


class ProfessionNode(models.Model):
    """Specific nodes/steps within a Profession Level"""
    NODE_TYPES = [
        ('course', 'Course'),
        ('olympiad', 'Olympiad'),
        ('project', 'Project'),
        ('exam', 'Exam'),
        ('certificate', 'Certificate'),
        ('custom', 'Custom Task'),
    ]
    level = models.ForeignKey(ProfessionLevel, on_delete=models.CASCADE, related_name='nodes')
    title = models.CharField(max_length=200)
    node_type = models.CharField(max_length=20, choices=NODE_TYPES, default='course')
    reference_id = models.IntegerField(blank=True, null=True, help_text="Course/Olympiad/etc ID")
    is_required = models.BooleanField(default=True, help_text="Ushbu bosqich majburiymi?")
    xp_reward = models.IntegerField(default=0, help_text="Ushbu qadamni yakunlash uchun beriladigan XP")
    unlock_condition = models.JSONField(blank=True, null=True, help_text="Shartlar (min_score, required_nodes, etc.)")
    order = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'profession_nodes'
        ordering = ['level', 'order']
        
    def __str__(self):
        return f"{self.level.profession.name} - {self.level.title} - Node: {self.title}"


class UserProfessionState(models.Model):
    """Tracks a user's overall progress in a specific profession"""
    STATUS_CHOICES = [
        ('locked', 'Locked'),
        ('active', 'Active'),
        ('completed', 'Completed'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='profession_states')
    profession = models.ForeignKey(Profession, on_delete=models.CASCADE, related_name='user_states')
    current_level = models.ForeignKey(ProfessionLevel, on_delete=models.SET_NULL, null=True, blank=True)
    total_xp = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='locked')
    started_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_profession_states'
        unique_together = ['user', 'profession']
        
    def __str__(self):
        return f"{self.user.username} -> {self.profession.name} ({self.status})"


class UserNodeProgress(models.Model):
    """Tracks a user's completion of individual profession nodes"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='node_progress')
    node = models.ForeignKey(ProfessionNode, on_delete=models.CASCADE, related_name='user_progress')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    score = models.IntegerField(default=0, blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        db_table = 'user_node_progress'
        unique_together = ['user', 'node']
        
    def __str__(self):
        return f"{self.user.username} -> {self.node.title} ({self.status})"


class Lead(models.Model):
    """Lead from Landing Page"""
    STATUS_CHOICES = [
        ('NEW', 'Yangi'),
        ('CONTACTED', 'Bog\'lanilgan'),
        ('CONVERTED', 'Mijoz bo\'ldi'),
        ('ARCHIVED', 'Arxiv'),
    ]

    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    telegram_username = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='NEW')
    created_at = models.DateTimeField(auto_now_add=True)
    note = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'leads'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.phone}"


class Testimonial(models.Model):
    """User testimonials for landing page"""
    name = models.CharField(max_length=100)
    profession = models.CharField(max_length=100)
    text_uz = models.TextField()
    text_ru = models.TextField()
    image = models.ImageField(upload_to='testimonials/', blank=True, null=True)
    instagram_url = models.URLField(blank=True, null=True, help_text='Instagram video/reel URL')
    rating = models.IntegerField(default=5)
    is_active = models.BooleanField(default=True)
    is_highlighted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'testimonials'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.profession}"


class Winner(models.Model):
    """Winners of Olympiads for 'Pride Carousel'"""
    STAGE_CHOICES = [
        ('REPUBLIC', 'Respublika'),
        ('REGION', 'Viloyat'),
        ('SCHOOL', 'Maktab'),
    ]
    POSITION_CHOICES = [
        (1, '1-o\'rin'),
        (2, '2-o\'rin'),
        (3, '3-o\'rin'),
    ]

    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='winners')
    stage = models.CharField(max_length=20, choices=STAGE_CHOICES, default='REPUBLIC')
    student_name = models.CharField(max_length=150)
    region = models.CharField(max_length=100)
    score = models.IntegerField()
    position = models.IntegerField(choices=POSITION_CHOICES, default=1)
    image = models.ImageField(upload_to='winners/', blank=True, null=True)
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'winners'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.student_name} - {self.subject.name} ({self.position}-o'rin)"


class AIAssistantFAQ(models.Model):
    CATEGORY_CHOICES = [
        ('GENERAL', 'Umumiy'),
        ('COURSES', 'Kurslar'),
        ('OLYMPIADS', 'Olimpiadalar'),
        ('PAYMENTS', 'To\'lovlar'),
    ]
    
    question_uz = models.CharField(max_length=255)
    question_ru = models.CharField(max_length=255)
    answer_uz = models.TextField()
    answer_ru = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='GENERAL')
    
    action_label_uz = models.CharField(max_length=50, blank=True, null=True)
    action_label_ru = models.CharField(max_length=50, blank=True, null=True)
    action_link = models.CharField(max_length=255, blank=True, null=True)
    
    order = models.IntegerField(default=0)
    priority = models.IntegerField(default=0, help_text="Yechimning ustuvorligi")
    search_tags = models.TextField(blank=True, help_text="Qidiruv teglari (vergul bilan)")
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ai_assistant_faqs'
        ordering = ['-priority', 'order', '-created_at']

    def __str__(self):
        return self.question_uz

class AIConversation(models.Model):
    """Tracks a user's session with the AI Assistant"""
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    session_id = models.CharField(max_length=100, unique=True, blank=True)
    context_url = models.CharField(max_length=255, blank=True, null=True)
    last_active = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ai_conversations'
        ordering = ['-last_active']

class AIMessage(models.Model):
    """Individual messages within an AI conversation"""
    ROLE_CHOICES = [('user', 'User'), ('assistant', 'Assistant')]
    SOURCE_CHOICES = [('FAQ', 'FAQ Match'), ('LLM', 'AI Generated'), ('SYSTEM', 'System')]

    conversation = models.ForeignKey(AIConversation, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default='FAQ')
    faq = models.ForeignKey(AIAssistantFAQ, on_delete=models.SET_NULL, null=True, blank=True)
    
    rating = models.IntegerField(null=True, blank=True, help_text="1 for Up, -1 for Down")
    feedback = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ai_messages'
        ordering = ['created_at']

class AIUnansweredQuestion(models.Model):
    """Captures questions where AI failed or was rated poorly"""
    question = models.TextField()
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    context_url = models.CharField(max_length=255, blank=True, null=True)
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ai_unanswered_questions'
        ordering = ['-created_at']


# Import Settings Models
from .models_settings import (
    PlatformSettings,
    SecuritySettings,
    NotificationSettings,
    PaymentProviderConfig,
    Permission,
    RolePermission,
    AuditLog
)
