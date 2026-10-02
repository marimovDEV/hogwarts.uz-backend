from rest_framework import serializers
from django.db.models import Sum
from django.contrib.auth.hashers import make_password
from .models import (
    OlympiadRegistration, TestResult, Certificate, SupportTicket,
    TicketMessage, Payment, BotConfig, LevelReward, User, Course, Lesson, Enrollment, Olympiad, Question,
    HomePageConfig, HomeStat, HomeStep, HomeAdvantage, FreeCourseSection, FreeCourseLessonCard, Subject, TeacherProfile, Notification,
    Profession, ProfessionSubject, ProfessionRoadmapStep, UserProfessionProgress,
    ProfessionLevel, ProfessionNode, UserProfessionState, UserNodeProgress, # Added new models
    Module, LessonPractice, LessonTest, Lead, LessonProgress,
    Testimonial, Winner, Banner, AIAssistantFAQ,
    NotificationTemplate, NotificationBroadcast,
    AIConversation, AIMessage, AIUnansweredQuestion, OlympiadPrize, WinnerPrize, PrizeAddress,
    TeacherWallet, Transaction, Payout, LessonContent, Homework, HomeworkSubmission
)

# ============= CMS SERIALIZERS =============


class WinnerSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    image = serializers.SerializerMethodField()
    
    class Meta:
        model = Winner
        fields = ['id', 'subject', 'subject_name', 'stage', 'student_name', 'region', 'score', 'position', 'image', 'is_featured']
    
    def get_image(self, obj):
        request = self.context.get('request')
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        return obj.image.url if obj.image else None


class AIAssistantFAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIAssistantFAQ
        fields = '__all__'

# ============= NOTIFICATION SERIALIZERS =============

class NotificationSerializer(serializers.ModelSerializer):
    timestamp = serializers.DateTimeField(source='created_at', format="%d-%m-%Y %H:%M:%S", read_only=True)

    class Meta:
        model = Notification
        fields = ['id', 'title', 'message', 'notification_type', 'is_read', 'timestamp', 'link', 'broadcast']

class NotificationTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationTemplate
        fields = '__all__'

# ============= AI SERIALIZERS =============

class AIConversationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIConversation
        fields = '__all__'

class AIMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIMessage
        fields = '__all__'

class AIUnansweredQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIUnansweredQuestion
        fields = '__all__'

class NotificationBroadcastSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    course_name = serializers.CharField(source='course.title', read_only=True)
    olympiad_name = serializers.CharField(source='olympiad.title', read_only=True)
    audience_type_display = serializers.CharField(source='get_audience_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = NotificationBroadcast
        fields = '__all__'



# ============= USER SERIALIZERS =============

class TeacherProfileSerializer(serializers.ModelSerializer):
    is_vip = serializers.ReadOnlyField()
    is_internal = serializers.ReadOnlyField()
    
    class Meta:
        model = TeacherProfile
        fields = ['bio', 'experience_years', 'specialization', 'telegram_username', 
                  'instagram_username', 'youtube_channel', 'linkedin_profile', 
                  'verification_status', 'rejection_reason', 'approved_at', 'approved_by', 
                  'is_premium', 'teacher_type', 'vip_expire_date', 'is_lifetime_vip',
                  'is_vip', 'is_internal',
                  'is_identity_verified', 'identity_document']


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()
    teacher_profile = serializers.SerializerMethodField()
    subjects = serializers.SerializerMethodField()
    courses_count = serializers.SerializerMethodField()
    students_count = serializers.SerializerMethodField()
    total_revenue = serializers.SerializerMethodField()
    olympiads_count = serializers.SerializerMethodField()
    password = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'full_name',
                  'phone', 'avatar', 'avatar_url', 'role', 'xp', 'level', 'level_progress', 'balance',
                  'ranking', 'certificates_count',
                  'birth_date', 'region', 'school', 'grade', 'language', 'password',
                  'telegram_id', 'telegram_linking_token', 'telegram_connected_at',
                   'is_active', 'is_staff', 'is_superuser', 'last_login', 'date_joined', 'teacher_profile', 'subjects',
                   'courses_count', 'students_count', 'total_revenue', 'olympiads_count']
        read_only_fields = ['id', 'date_joined', 'xp', 'level', 'last_login', 
                            'ranking', 'certificates_count',
                            'telegram_id', 'telegram_linking_token', 'telegram_connected_at',
                            'teacher_profile', 'subjects', 'courses_count', 'students_count', 'total_revenue', 'olympiads_count']
    
    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username
    
    def get_avatar_url(self, obj):
        request = self.context.get('request')
        if obj.avatar and request:
            return request.build_absolute_uri(obj.avatar.url)
        return obj.avatar.url if obj.avatar else None

    def get_teacher_profile(self, obj):
        try:
            profile = obj.teacher_profile
            return TeacherProfileSerializer(profile).data
        except:
            return None

    def get_subjects(self, obj):
        if obj.role == 'TEACHER':
            return [{'id': s.id, 'name': s.name, 'color': s.color} for s in obj.subjects.all()]
        return []

    def get_courses_count(self, obj):
        if obj.role == 'TEACHER':
            return obj.courses.count()
        return 0

    def get_students_count(self, obj):
        if obj.role == 'TEACHER':
            # Sum of students_count from all teacher's courses
            from django.db.models import Sum
            return obj.courses.aggregate(total=Sum('students_count'))['total'] or 0
        return 0

    def get_total_revenue(self, obj):
        if obj.role == 'TEACHER':
            # Check if TeacherWallet exists and return total_earned
            try:
                return float(obj.teacher_wallet.total_earned)
            except:
                return 0.0
        return 0.0

    def get_olympiads_count(self, obj):
        if obj.role == 'TEACHER':
            return obj.olympiads.count()
        return 0

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = super().create(validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        user = super().update(instance, validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user


class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    password_confirm = serializers.CharField(write_only=True, required=False)
    
    email = serializers.EmailField(required=False, allow_blank=True) # Make email optional

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password_confirm', 
                  'first_name', 'last_name', 'phone', 'role']
    
    def validate(self, data):
        if data.get('password') != data.get('password_confirm'):
            raise serializers.ValidationError({"password": "Passwords must match"})
        return data

    def create(self, validated_data):
        validated_data.pop('password_confirm', None)
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


# Wallet Serializers
class TeacherWalletSerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source='teacher.username', read_only=True)
    
    class Meta:
        model = TeacherWallet
        fields = ['id', 'teacher', 'teacher_name', 'balance', 'pending_balance', 
                  'total_earned', 'total_withdrawn', 'created_at', 'updated_at']
        read_only_fields = ['id', 'teacher', 'created_at', 'updated_at']


class TransactionSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    course_title = serializers.CharField(source='course.title', read_only=True)
    transaction_type_display = serializers.CharField(source='get_transaction_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Transaction
        fields = ['id', 'transaction_type', 'transaction_type_display', 'user', 'user_name',
                  'course', 'course_title', 'amount', 'status', 'status_display',
                  'payment_provider', 'payment_id', 'description', 'metadata', 'created_at']
        read_only_fields = ['id', 'created_at']


class PayoutSerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source='teacher.username', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.username', read_only=True, allow_null=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    
    class Meta:
        model = Payout
        fields = ['id', 'teacher', 'teacher_name', 'amount', 'status', 'status_display',
                  'payment_method', 'payment_method_display', 'payment_details',
                  'approved_by', 'approved_by_name', 'approved_at', 'paid_at',
                  'rejection_reason', 'notes', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at', 'approved_by', 'approved_at', 'paid_at']


# Import wallet models at the top of file
from .models import TeacherWallet, Transaction, Payout


class UserRegisterSerializer_OLD(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    password_confirm = serializers.CharField(write_only=True, required=False)
    
    email = serializers.EmailField(required=False, allow_blank=True) # Make email optional

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password_confirm', 
                  'first_name', 'last_name', 'phone', 'role']
    
    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Bu foydalanuvchi nomi band")
        return value
    
    def validate(self, data):
        password = data.get('password')
        password_confirm = data.get('password_confirm')
        if password_confirm and password != password_confirm:
            raise serializers.ValidationError({"password_confirm": "Parollar mos kelmaydi"})
        return data
    
    def create(self, validated_data):
        validated_data.pop('password_confirm', None)
        validated_data['password'] = make_password(validated_data['password'])
        # Allow role setting (e.g. for teachers) if provided
        return super().create(validated_data)


class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=False)
    email = serializers.CharField(required=False)
    password = serializers.CharField()


class UserMiniSerializer(serializers.ModelSerializer):
    """Minimal user info for nested serializers"""
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'full_name', 'phone', 'avatar', 'language']
    
    def get_full_name(self, obj):
        try:
            return obj.get_full_name() or obj.username
        except Exception:
            return getattr(obj, 'username', 'Noma\'lum')


# ============= COURSE SERIALIZERS =============


class HomePageConfigSerializer(serializers.ModelSerializer):
    hero_image = serializers.SerializerMethodField()
    teaser_image = serializers.SerializerMethodField()

    class Meta:
        model = HomePageConfig
        fields = ['id', 'hero_title', 'hero_subtitle', 'hero_button_text', 
                  'hero_button_link', 'hero_image', 'cta_title', 'cta_subtitle', 
                  'cta_button_text', 'cta_button_link', 
                  'teaser_title_uz', 'teaser_title_ru', 'teaser_subtitle_uz', 'teaser_subtitle_ru',
                  'teaser_image', 'teaser_button_text_uz', 'teaser_button_text_ru', 'teaser_button_link',
                  'updated_at',
                  'show_stats', 'show_olympiads', 'show_courses', 'show_professions',
                  'show_testimonials', 'show_mentors', 'show_winners', 'show_steps', 'show_cta', 'show_faq']
        read_only_fields = ['id', 'updated_at']

    def get_hero_image(self, obj):
        request = self.context.get('request')
        if obj.hero_image and request:
            return request.build_absolute_uri(obj.hero_image.url)
        return obj.hero_image.url if obj.hero_image else None

    def get_teaser_image(self, obj):
        request = self.context.get('request')
        if obj.teaser_image and request:
            return request.build_absolute_uri(obj.teaser_image.url)
        return obj.teaser_image.url if obj.teaser_image else None


class HomeStatSerializer(serializers.ModelSerializer):
    class Meta:
        model = HomeStat
        fields = ['id', 'label', 'value', 'icon', 'order', 'is_active']


class HomeStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = HomeStep
        fields = ['id', 'title', 'description', 'icon', 'order', 'is_active']


class HomeAdvantageSerializer(serializers.ModelSerializer):
    class Meta:
        model = HomeAdvantage
        fields = ['id', 'title', 'description', 'icon', 'order', 'is_active']


class FreeCourseSectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = FreeCourseSection
        fields = '__all__'


class FreeCourseLessonCardSerializer(serializers.ModelSerializer):
    class Meta:
        model = FreeCourseLessonCard
        fields = '__all__'


class LessonContentSerializer(serializers.ModelSerializer):
    resources_file = serializers.SerializerMethodField()
    
    class Meta:
        model = LessonContent
        fields = ['id', 'lesson', 'text_content', 'resources_file', 'created_by', 'created_at', 'updated_at']

    def get_resources_file(self, obj):
        request = self.context.get('request')
        if obj.resources_file and request:
            return request.build_absolute_uri(obj.resources_file.url)
        return obj.resources_file.url if obj.resources_file else None


class HomeworkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Homework
        fields = ['id', 'lesson', 'title', 'description', 'deadline', 'created_at']


class HomeworkSubmissionSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = HomeworkSubmission
        fields = ['id', 'student', 'student_name', 'homework', 'file_url', 'grade', 'feedback', 'status', 'submitted_at']

    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.file_url and request:
            return request.build_absolute_uri(obj.file_url.url)
        return obj.file_url.url if obj.file_url else None


# ============= QUESTION SERIALIZERS =============

class QuestionSerializer(serializers.ModelSerializer):
    """Question serializer for students (no correct_answer)"""
    class Meta:
        model = Question
        fields = ['id', 'text', 'type', 'options', 'points', 'order', 'time_limit']

class QuestionAdminSerializer(serializers.ModelSerializer):
    """Question serializer for admins (includes correct_answer)"""
    olympiad = serializers.PrimaryKeyRelatedField(queryset=Olympiad.objects.all())
    correct_answer = serializers.CharField(required=False, allow_blank=True)
    options = serializers.JSONField(required=False, allow_null=True)
    explanation = serializers.CharField(required=False, allow_blank=True)
    
    class Meta:
        model = Question
        fields = ['id', 'olympiad', 'text', 'options', 'correct_answer', 'explanation', 'points', 'order', 'time_limit', 'code_template'] # Full admin fields

class LessonTestSerializer(serializers.ModelSerializer):
    questions = QuestionAdminSerializer(many=True, required=False)
    
    class Meta:
        model = LessonTest
        fields = ['id', 'min_pass_score', 'is_final', 'max_attempts', 'questions']

    def update(self, instance, validated_data):
        questions_data = validated_data.pop('questions', None)
        instance.min_pass_score = validated_data.get('min_pass_score', instance.min_pass_score)
        instance.max_attempts = validated_data.get('max_attempts', instance.max_attempts)
        instance.save()
        
        if questions_data is not None:
            # Simple approach: delete old questions and create new ones
            # Or map via IDs. Let's do map via IDs for better persistence.
            existing_question_ids = [q.id for q in instance.questions.all()]
            new_question_ids = []
            
            for q_data in questions_data:
                q_id = q_data.get('id')
                if q_id and q_id in existing_question_ids:
                    # Update existing
                    q_instance = Question.objects.get(id=q_id)
                    for attr, value in q_data.items():
                        setattr(q_instance, attr, value)
                    q_instance.save()
                    new_question_ids.append(q_id)
                else:
                    # Create new
                    # Ensure olympiad is null as it's a LessonTest question
                    q_data.pop('olympiad', None)
                    new_q = Question.objects.create(**q_data)
                    instance.questions.add(new_q)
                    new_question_ids.append(new_q.id)
            
            # Remove questions that are no longer in the list
            for old_id in existing_question_ids:
                if old_id not in new_question_ids:
                    q_to_remove = Question.objects.get(id=old_id)
                    instance.questions.remove(q_to_remove)
                    # Optional: delete the question if it's not used elsewhere
                    if q_to_remove.lesson_tests.count() == 0 and not q_to_remove.olympiad:
                        q_to_remove.delete()
                        
        return instance


class LessonSerializer(serializers.ModelSerializer):
    duration = serializers.SerializerMethodField()
    test = LessonTestSerializer(required=False)
    
    class Meta:
        model = Lesson
        fields = ['id', 'course', 'module', 'title', 'description', 'video_url', 'pdf_url', 
                  'video_duration', 'duration', 'order', 'is_free', 'is_locked', 'min_watch_percent', 
                  'required_lesson', 'test', 'teacher', 'created_at']
        read_only_fields = ['id', 'created_at']

    def update(self, instance, validated_data):
        test_data = validated_data.pop('test', None)
        instance = super().update(instance, validated_data)
        
        if test_data:
            test_instance, _ = LessonTest.objects.get_or_create(lesson=instance)
            test_serializer = LessonTestSerializer(test_instance, data=test_data, partial=True)
            if test_serializer.is_valid():
                test_serializer.save()
            else:
                raise serializers.ValidationError(test_serializer.errors)
        
        return instance

    def get_duration(self, obj):
        if obj.video_duration:
            return obj.video_duration // 60
        return 10 # Default fallback


class LessonCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = ['course', 'module', 'title', 'description', 'video_url', 'pdf_url', 
                  'video_duration', 'order', 'is_free']



class SubjectSerializer(serializers.ModelSerializer):
    courses_count = serializers.SerializerMethodField()
    olympiads_count = serializers.SerializerMethodField()
    professions_count = serializers.SerializerMethodField()
    
    stats = serializers.SerializerMethodField()
    
    class Meta:
        model = Subject
        fields = ['id', 'name', 'slug', 'description', 'icon', 'color', 'xp_reward', 
                  'is_featured', 'is_active', 'order', 'courses_count', 'olympiads_count', 'professions_count', 'stats']
    
    def get_stats(self, obj):
        return {
            'students': obj.courses.filter(is_active=True).aggregate(count=Sum('students_count'))['count'] or 0,
            'olympiads': obj.olympiads_api.count()
        }
    
    def get_courses_count(self, obj):
        return obj.courses.filter(is_active=True).count()
    
    def get_olympiads_count(self, obj):
        return obj.olympiads_api.count()
    
    def get_professions_count(self, obj):
        return obj.profession_links.count()

    def get_teacher_avatar(self, obj):
        if obj.teacher and obj.teacher.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.teacher.avatar.url)
            return obj.teacher.avatar.url
        return None
    
    def get_lessons_count(self, obj):
        return obj.lessons.count()

    def get_is_enrolled(self, obj):
        user = self.context.get('request').user if self.context.get('request') else None
        if user and user.is_authenticated:
            return Enrollment.objects.filter(user=user, course=obj).exists()
        return False

    def validate(self, attrs):
        # We need to call the model's clean() method for business logic validation
        # especially when activating a course.
        instance = self.instance
        if instance:
            # Create a temporary instance to validate without saving
            for key, value in attrs.items():
                setattr(instance, key, value)
            
            try:
                instance.clean()
            except serializers.ValidationError as e:
                raise e
            except Exception as e:
                from django.core.exceptions import ValidationError as DjangoValidationError
                if isinstance(e, DjangoValidationError):
                    raise serializers.ValidationError(e.message_dict if hasattr(e, 'message_dict') else e.messages)
                raise e
                
        return attrs

class UserProfessionProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfessionProgress
        fields = ['id', 'status', 'progress_percent', 'started_at', 'updated_at']


# ============= PROFESSION SERIALIZERS =============

class ProfessionSubjectSerializer(serializers.ModelSerializer):
    subject_id = serializers.IntegerField(source='subject.id')
    name = serializers.CharField(source='subject.name')
    slug = serializers.CharField(source='subject.slug')
    icon = serializers.CharField(source='subject.icon')
    color = serializers.CharField(source='subject.color')
    
    class Meta:
        model = ProfessionSubject
        fields = ['subject_id', 'name', 'slug', 'icon', 'color', 'importance', 'percentage', 'order']


class ProfessionRoadmapStepSerializer(serializers.ModelSerializer):
    step_type_display = serializers.CharField(source='get_step_type_display', read_only=True)
    course_title = serializers.CharField(source='course.title', read_only=True)
    course_id = serializers.IntegerField(source='course.id', read_only=True)
    olympiad_title = serializers.CharField(source='olympiad.title', read_only=True)
    olympiad_id = serializers.IntegerField(source='olympiad.id', read_only=True)
    is_course_completed = serializers.SerializerMethodField()
    
    class Meta:
        model = ProfessionRoadmapStep
        fields = ['id', 'title', 'description', 'step_type', 'step_type_display', 
                  'course_id', 'course_title', 'olympiad_id', 'olympiad_title',
                  'is_mandatory', 'is_course_completed', 'order']

    def get_is_course_completed(self, obj):
        user = self.context.get('request').user if self.context.get('request') and self.context.get('request').user.is_authenticated else None
        if user and obj.course:
            return Enrollment.objects.filter(user=user, course=obj.course, progress__gte=100).exists()
        return False


class ProfessionNodeSerializer(serializers.ModelSerializer):
    user_status = serializers.SerializerMethodField()
    
    class Meta:
        model = ProfessionNode
        fields = ['id', 'title', 'node_type', 'reference_id', 'is_required', 
                  'xp_reward', 'unlock_condition', 'order', 'user_status']

    def get_user_status(self, obj):
        user = self.context.get('request').user if self.context.get('request') else None
        if user and user.is_authenticated:
            prog = UserNodeProgress.objects.filter(user=user, node=obj).first()
            if prog:
                return {
                    'status': prog.status,
                    'score': prog.score,
                    'completed_at': prog.completed_at
                }
        return {'status': 'locked'}

class ProfessionLevelSerializer(serializers.ModelSerializer):
    nodes = ProfessionNodeSerializer(many=True, read_only=True)
    
    class Meta:
        model = ProfessionLevel
        fields = ['id', 'level_number', 'title', 'unlock_xp', 'order', 'is_prestige_only', 'nodes']
        

class UserProfessionStateSerializer(serializers.ModelSerializer):
    current_level_id = serializers.PrimaryKeyRelatedField(source='current_level', read_only=True)
    
    class Meta:
        model = UserProfessionState
        fields = ['id', 'current_level_id', 'total_xp', 'status', 'started_at', 'updated_at']

class ProfessionSerializer(serializers.ModelSerializer):
    required_subjects = ProfessionSubjectSerializer(many=True, read_only=True)
    roadmap_steps = ProfessionRoadmapStepSerializer(many=True, read_only=True)
    user_progress = serializers.SerializerMethodField()
    levels = ProfessionLevelSerializer(many=True, read_only=True)
    user_state = serializers.SerializerMethodField()
    
    class Meta:
        model = Profession
        fields = ['id', 'name', 'slug', 'description', 'icon', 'color', 'is_active', 'order',
                  'suitability', 'requirements', 'salary_range', 'learning_time',
                  'certification_info', 'career_opportunities', 'prestige_only',
                  'primary_subject', 'required_xp', 'total_required_xp',
                  'required_subjects', 'roadmap_steps', 'user_progress', 'levels', 'user_state']

    def get_user_state(self, obj):
        user = self.context.get('request').user if self.context.get('request') else None
        if user and user.is_authenticated:
            state = UserProfessionState.objects.filter(user=user, profession=obj).first()
            if state:
                return UserProfessionStateSerializer(state).data
        return None

    def get_user_progress(self, obj):
        user = self.context.get('request').user if self.context.get('request') else None
        if user and user.is_authenticated:
            progress = UserProfessionProgress.objects.filter(user=user, profession=obj).first()
            if progress:
                return UserProfessionProgressSerializer(progress).data
        return None



class SubjectDetailSerializer(serializers.ModelSerializer):
    """Full detail serializer for subject page with related content"""
    courses_count = serializers.SerializerMethodField()
    olympiads_count = serializers.SerializerMethodField()
    professions_count = serializers.SerializerMethodField()
    courses = serializers.SerializerMethodField()
    olympiads = serializers.SerializerMethodField()
    professions = serializers.SerializerMethodField()
    
    class Meta:
        model = Subject
        fields = ['id', 'name', 'slug', 'description', 'icon', 'color', 'xp_reward', 
                  'is_featured', 'is_active', 'order', 'courses_count', 'olympiads_count', 'professions_count',
                  'total_xp_available', 'courses', 'olympiads', 'professions', 'roadmap_steps']
    
    total_xp_available = serializers.SerializerMethodField()
    roadmap_steps = serializers.SerializerMethodField()

    def get_roadmap_steps(self, obj):
        # We want to show roadmap steps for featured professions of this subject
        featured_profession = obj.professions_featured.filter(is_active=True).first()
        if not featured_profession:
            return []
        
        steps = featured_profession.roadmap_steps.all().order_by('order')
        return ProfessionRoadmapStepSerializer(steps, many=True, context=self.context).data
    
    def get_total_xp_available(self, obj):
        from django.db.models import Sum
        lesson_xp = obj.courses.aggregate(total=Sum('lessons__xp_amount'))['total'] or 0
        course_xp = obj.courses.aggregate(total=Sum('xp_reward'))['total'] or 0
        olympiad_xp = obj.olympiads_api.aggregate(total=Sum('xp_reward'))['total'] or 0
        return lesson_xp + course_xp + olympiad_xp
    
    def get_courses_count(self, obj):
        return obj.courses.filter(is_active=True).count()
    
    def get_olympiads_count(self, obj):
        return obj.olympiads_api.count()
    
    def get_professions_count(self, obj):
        return obj.profession_links.count()
    
    def get_courses(self, obj):
        """Return courses for this subject"""
        from django.db.models import Count
        courses = obj.courses.filter(is_active=True)[:12]
        return [{
            'id': c.id,
            'title': c.title,
            'thumbnail': self.context['request'].build_absolute_uri(c.thumbnail.url) if c.thumbnail and 'request' in self.context else (c.thumbnail.url if c.thumbnail else None),
            'price': c.price,
            'level': c.level,
            'lesson_count': c.modules.aggregate(count=Count('lessons'))['count'] or 0,
        } for c in courses]
    
    def get_olympiads(self, obj):
        """Return upcoming/active olympiads for this subject"""
        from django.utils import timezone
        now = timezone.now()
        # Include UPCOMING and ONGOING olympiads that are active
        olympiads = obj.olympiads_api.filter(
            is_active=True, 
            status__in=['UPCOMING', 'ONGOING']
        ).order_by('status', 'start_date')[:6]
        
        # Refresh status for each to be sure
        for o in olympiads:
            o.refresh_status()
            
        return [{
            'id': o.id,
            'title': o.title,
            'slug': o.slug,
            'start_date': o.start_date,
            'status': o.status,
            'price': o.price,
        } for o in olympiads]
    
    def get_professions(self, obj):
        """Return professions that require this subject"""
        links = obj.profession_links.select_related('profession')[:6]
        return [{
            'id': link.profession.id,
            'name': link.profession.name,
            'icon': link.profession.icon,
            'color': link.profession.color,
            'percentage': link.percentage,
            'required_xp': link.profession.required_xp,
            'roadmap_steps': ProfessionRoadmapStepSerializer(link.profession.roadmap_steps.all(), many=True, context=self.context).data
        } for link in links]

class LessonProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = LessonProgress
        fields = ['id', 'is_video_watched', 'video_last_position', 
                  'practice_score', 'test_score', 'is_completed', 'completed_at']

class LessonPracticeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LessonPractice
        fields = ['id', 'type', 'problem_text', 'points'] # Don't show correct_answer


class LearningLessonSerializer(serializers.ModelSerializer):
    """Specialized serializer for the learning interface"""
    duration = serializers.SerializerMethodField()
    progress = serializers.SerializerMethodField()
    is_locked = serializers.SerializerMethodField()
    practice = LessonPracticeSerializer(read_only=True)
    test = LessonTestSerializer(read_only=True)
    content = LessonContentSerializer(read_only=True)
    homework = HomeworkSerializer(read_only=True)
    
    class Meta:
        model = Lesson
        fields = ['id', 'title', 'description', 'video_url', 'youtube_id', 'video_type', 
                  'video_duration', 'duration', 'pdf_url', 'order', 'is_free', 
                  'progress', 'is_locked', 'required_lesson', 'practice', 'test', 'content', 'homework', 'teacher']

    def get_duration(self, obj):
        if obj.video_duration:
            return obj.video_duration // 60
        return 10

    def get_progress(self, obj):
        # Data passed from service to_attr='my_progress'
        progress = getattr(obj, 'my_progress', [])
        if progress:
            return {
                "is_video_watched": progress[0].is_video_watched,
                "practice_score": progress[0].practice_score,
                "test_score": progress[0].test_score,
                "is_completed": progress[0].is_completed
            }
        return None

    def get_is_locked(self, obj):
        return getattr(obj, 'is_locked', False)


class ModuleSerializer(serializers.ModelSerializer):
    lessons = LearningLessonSerializer(many=True, read_only=True)
    
    class Meta:
        model = Module
        fields = ['id', 'course', 'title', 'description', 'order', 'lessons']


class CourseSerializer(serializers.ModelSerializer):
    subject_name = serializers.SerializerMethodField()
    teacher_name = serializers.SerializerMethodField()
    teacher_avatar = serializers.SerializerMethodField()
    is_enrolled = serializers.SerializerMethodField()
    total_duration = serializers.SerializerMethodField()
    
    class Meta:
        model = Course
        fields = [
            'id', 'title', 'admin', 'description', 'thumbnail', 'subject', 'subject_name',
            'level', 'price', 'teacher_percentage', 'platform_percentage',
            'is_active', 'status', 'lessons_count', 'students_count',
            'rating', 'teacher_name', 'teacher_avatar', 'is_enrolled', 'created_at',
            'lock_strategy', 'completion_min_progress', 'required_final_score', 'total_duration',
            'is_internal', 'is_paid_creation', 'creation_fee_paid', 'teachers'
        ]

    def get_total_duration(self, obj):
        from django.db.models import Sum
        total_seconds = obj.modules.aggregate(total=Sum('lessons__video_duration'))['total'] or 0
        total_minutes = total_seconds // 60
        hours = total_minutes // 60
        minutes = total_minutes % 60
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"

    def get_subject_name(self, obj):
        if obj.subject:
            return obj.subject.name
        return None

    def get_teacher_name(self, obj):
        if obj.teacher:
            return obj.teacher.full_name or obj.teacher.get_full_name() or obj.teacher.username
        return None

    def get_teacher_avatar(self, obj):
        request = self.context.get('request')
        if obj.teacher and obj.teacher.avatar and request:
            return request.build_absolute_uri(obj.teacher.avatar.url)
        return obj.teacher.avatar.url if obj.teacher and obj.teacher.avatar else None

    def get_is_enrolled(self, obj):
        user = self.context.get('request').user if self.context.get('request') else None
        if user and user.is_authenticated:
            return Enrollment.objects.filter(user=user, course=obj).exists()
        return False


class CourseDetailSerializer(serializers.ModelSerializer):
    lessons = LessonSerializer(many=True, read_only=True)
    level_display = serializers.CharField(source='get_level_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    subject_details = SubjectSerializer(source='subject', read_only=True)
    is_enrolled = serializers.SerializerMethodField()
    enrollment = serializers.SerializerMethodField()
    
    modules = ModuleSerializer(many=True, read_only=True)
    
    class Meta:
        model = Course
        fields = ['id', 'title', 'admin', 'description', 'thumbnail', 'price', 'level',
                  'level_display', 'status', 'status_display', 'subject', 'subject_name', 'subject_details', 'language', 'duration', 'lessons_count', 
                  'teacher_percentage', 'platform_percentage',
                  'rating', 'students_count', 'is_featured', 'is_active', 'xp_reward',
                  'lock_strategy', 'completion_min_progress', 'required_final_score',
                  'is_enrolled', 'enrollment', 'created_at', 'updated_at', 'lessons', 'modules']

    def get_subject_name(self, obj):
        if obj.subject:
            return obj.subject.name
        return None

    def get_is_enrolled(self, obj):
        user = self.context.get('request').user if self.context.get('request') else None
        if user and user.is_authenticated:
            return Enrollment.objects.filter(user=user, course=obj).exists()
        return False

    def get_enrollment(self, obj):
        user = self.context.get('request').user if self.context.get('request') else None
        if user and user.is_authenticated:
            enrollment = Enrollment.objects.filter(user=user, course=obj).first()
            if enrollment:
                return {
                    'id': enrollment.id,
                    'progress': float(enrollment.progress),
                    'current_lesson': enrollment.current_lesson.id if enrollment.current_lesson else None,
                    'updated_at': enrollment.updated_at
                }
        return None


class CourseCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ['title', 'description', 'thumbnail', 'price', 'level',
                  'subject', 'language', 'duration', 'is_featured', 'is_active', 'status', 'xp_reward',
                  'lock_strategy', 'completion_min_progress', 'required_final_score']





class EnrollmentSerializer(serializers.ModelSerializer):
    course = CourseSerializer(read_only=True)
    progress_percent = serializers.SerializerMethodField()
    
    class Meta:
        model = Enrollment
        fields = ['id', 'course', 'progress', 'progress_percent', 
                  'current_lesson', 'completed_at', 'created_at', 'updated_at']
    
    def get_progress_percent(self, obj):
        return f"{float(obj.progress):.0f}%"




# --- Teacher Serializers (with internal data) ---

class TeacherLessonPracticeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LessonPractice
        fields = ['id', 'lesson', 'type', 'problem_text', 'correct_answer', 'points']

class TeacherLessonTestSerializer(serializers.ModelSerializer):
    class Meta:
        model = LessonTest
        fields = ['id', 'lesson', 'min_pass_score', 'max_attempts', 'questions']


class TeacherLessonSerializer(serializers.ModelSerializer):
    practice = TeacherLessonPracticeSerializer(read_only=True)
    test = TeacherLessonTestSerializer(read_only=True)
    content = LessonContentSerializer(read_only=True)
    homework = HomeworkSerializer(read_only=True)
    
    class Meta:
        model = Lesson
        fields = '__all__'

class TeacherModuleSerializer(serializers.ModelSerializer):
    lessons = TeacherLessonSerializer(many=True, read_only=True)
    
    class Meta:
        model = Module
        fields = ['id', 'course', 'title', 'description', 'order', 'lessons']

class TeacherCourseDetailSerializer(serializers.ModelSerializer):
    modules = TeacherModuleSerializer(many=True, read_only=True)
    
    class Meta:
        model = Course
        fields = ['id', 'title', 'description', 'thumbnail', 'price', 'level',
                  'subject', 'duration', 'is_featured', 'is_active', 'xp_reward',
                  'created_at', 'updated_at', 'modules']




# ============= OLYMPIAD SERIALIZERS =============



class OlympiadPrizeSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    
    class Meta:
        model = OlympiadPrize
        fields = ['id', 'olympiad', 'name', 'image', 'description', 'prize_type', 'amount', 'target_value']

    def get_image(self, obj):
        request = self.context.get('request')
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        return obj.image.url if obj.image else None


class PrizeAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrizeAddress
        fields = '__all__'


class WinnerPrizeSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    olympiad_title = serializers.CharField(source='olympiad.title', read_only=True)
    address = serializers.SerializerMethodField()
    prize_item_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = WinnerPrize
        fields = ['id', 'olympiad', 'olympiad_title', 'student', 'student_name', 
                  'position', 'status', 'status_display', 'prize_item', 'prize_item_name', 
                  'address', 'awarded_at', 'updated_at']

    def get_address(self, obj):
        try:
            addr = obj.address
            return PrizeAddressSerializer(addr).data
        except:
            return None

    def get_prize_item_name(self, obj):
        if obj.prize_item:
            return obj.prize_item.name
        return None


class OlympiadSerializer(serializers.ModelSerializer):
    questions_count = serializers.SerializerMethodField()
    participants_count = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    time_remaining = serializers.SerializerMethodField()
    is_registered = serializers.SerializerMethodField()
    is_completed = serializers.SerializerMethodField()
    prizes = OlympiadPrizeSerializer(many=True, read_only=True)
    start_time = serializers.SerializerMethodField()
    revenue = serializers.SerializerMethodField()
    
    thumbnail = serializers.SerializerMethodField()
    
    class Meta:
        model = Olympiad
        fields = ['id', 'title', 'slug', 'description', 'thumbnail', 'subject', 'subject_id', 'profession', 'course',
                  'rules', 'prizes', 'evaluation_criteria',
                  'registration_start', 'registration_end', 'start_date', 'end_date', 'duration', 
                  'price', 'is_paid', 'currency', 'discount_percent',
                  'max_participants', 'status', 'status_display', 'is_active', 
                  'grade_range', 'level', 'difficulty', 'format',
                  'max_attempts', 'tab_switch_limit', 'is_random', 'cannot_go_back', 'required_camera', 'required_full_screen', 'disable_copy_paste',
                  'questions_count', 'xp_reward', 'participants_count', 'time_remaining', 'is_registered', 'is_completed', 'created_at',
                  'eligibility_grades', 'eligibility_regions', 'technical_config', 'certificate_config', 'start_time', 'revenue',
                  'is_paid_creation', 'creation_fee_paid', 'checker', 'moderator',
                  'reward_strategy', 'auto_reward', 'reward_distribution_status']
    
    def get_thumbnail(self, obj):
        request = self.context.get('request')
        if obj.thumbnail and request:
            return request.build_absolute_uri(obj.thumbnail.url)
        return obj.thumbnail.url if obj.thumbnail else None
    
    def get_start_time(self, obj):
        return obj.start_date

    def get_revenue(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated and request.user.role in ['ADMIN', 'TEACHER']:
            from .models import Payment
            return float(Payment.objects.filter(type='OLYMPIAD', reference_id=str(obj.id), status='COMPLETED').aggregate(total=Sum('amount'))['total'] or 0)
        return 0
    
    def validate(self, data):
        """
        Custom validation for Olympiad.
        Ensure it has questions before activating (PUBLISHED, UPCOMING, ONGOING).
        Allow DRAFT, CANCELED, PAUSED, COMPLETED, CHECKING without question check.
        """
        status = data.get('status')
        # Only block activation-type statuses if no questions
        activation_statuses = ['PUBLISHED', 'UPCOMING', 'ONGOING']
        if status and status in activation_statuses:
            if self.instance:
                q_count = self.instance.questions.count()
                if q_count == 0:
                    raise serializers.ValidationError({
                        "status": f"Savollar qo'shilmagan olimpiadani aktivlashtirib bo'lmaydi. Avval savollarni qo'shing. (Hozirda: {q_count} ta savol)"
                    })
        return data

    def get_questions_count(self, obj):
        return obj.questions.count()
    
    def get_participants_count(self, obj):
        return obj.registrations.count()
    
    def get_time_remaining(self, obj):
        from django.utils import timezone
        
        if not obj.start_date or not obj.end_date:
             return None

        now = timezone.now()
        if now < obj.start_date:
            delta = obj.start_date - now
            days = delta.days
            hours = delta.seconds // 3600
            minutes = (delta.seconds % 3600) // 60
            if days > 0:
                return f"{days}d {hours}h {minutes}m"
            return f"{hours}h {minutes}m"
        elif now < obj.end_date:
            delta = obj.end_date - now
            hours = delta.seconds // 3600
            minutes = (delta.seconds % 3600) // 60
            return f"{hours}h {minutes}m"
        return None

    def get_is_registered(self, obj):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if user and user.is_authenticated:
            return OlympiadRegistration.objects.filter(user=user, olympiad=obj).exists()
        return False

    def get_is_completed(self, obj):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if user and user.is_authenticated:
            return TestResult.objects.filter(user=user, olympiad=obj, status='COMPLETED').exists()
        return False


class OlympiadDetailSerializer(serializers.ModelSerializer):
    questions = serializers.SerializerMethodField()
    is_registered = serializers.SerializerMethodField()
    is_completed = serializers.SerializerMethodField()
    total_score = serializers.SerializerMethodField()
    start_time = serializers.SerializerMethodField()
    revenue = serializers.SerializerMethodField()
    
    class Meta:
        model = Olympiad
        fields = ['id', 'title', 'slug', 'description', 'subject', 'subject_id', 'thumbnail',
                  'registration_start', 'registration_end', 'start_date', 'end_date', 'duration', 'price', 'status', 'questions',
                  'rules', 'prizes', 'evaluation_criteria', 'max_attempts', 'tab_switch_limit', 'disable_copy_paste',
                  'is_registered', 'is_completed', 'total_score', 'start_time', 'revenue']

    def get_start_time(self, obj):
        return obj.start_date

    def get_questions(self, obj):
        request = self.context.get('request')
        user = request.user if request else None
        
        # Order questions
        questions = obj.questions.all().order_by('order')
        
        # For teachers and admins, show correct answers and explanations
        if user and user.is_authenticated and user.role in ['ADMIN', 'TEACHER']:
            return QuestionAdminSerializer(questions, many=True).data
        return QuestionSerializer(questions, many=True).data

    def get_revenue(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated and request.user.role in ['ADMIN', 'TEACHER']:
            from .models import Payment
            from django.db.models import Sum
            return float(Payment.objects.filter(type='OLYMPIAD', reference_id=str(obj.id), status='COMPLETED').aggregate(total=Sum('amount'))['total'] or 0)
        return 0

    def get_is_registered(self, obj):
        user = self.context.get('request').user if self.context.get('request') else None
        if user and user.is_authenticated:
            return OlympiadRegistration.objects.filter(user=user, olympiad=obj).exists()
        return False

    def get_is_completed(self, obj):
        user = self.context.get('request').user if self.context.get('request') else None
        if user and user.is_authenticated:
            return TestResult.objects.filter(user=user, olympiad=obj, status='COMPLETED').exists()
        return False

    def get_total_score(self, obj):
        return sum(q.points for q in obj.questions.all())


class OlympiadCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Olympiad
        fields = ['title', 'slug', 'description', 'subject', 'subject_id', 'thumbnail',
                  'registration_start', 'registration_end', 'start_date', 'end_date', 'duration', 'price', 
                  'max_participants', 'status', 'is_active', 'xp_reward',
                  'rules', 'prizes', 'evaluation_criteria',
                  'grade_range', 'level', 'difficulty', 'format',
                  'is_paid', 'max_attempts', 'tab_switch_limit', 
                  'time_limit_per_question', 'is_random', 'cannot_go_back',
                  'required_camera', 'required_full_screen', 'disable_copy_paste', 'allowed_ip_range']


class OlympiadRegistrationSerializer(serializers.ModelSerializer):
    olympiad = OlympiadSerializer(read_only=True)
    user = UserMiniSerializer(read_only=True)
    
    class Meta:
        model = OlympiadRegistration
        fields = ['id', 'user', 'olympiad', 'is_paid', 'registered_at']


class TestResultSerializer(serializers.ModelSerializer):
    user = UserMiniSerializer(read_only=True)
    olympiad = OlympiadSerializer(read_only=True)
    correct_answers = serializers.SerializerMethodField()
    total_questions = serializers.SerializerMethodField()
    
    class Meta:
        model = TestResult
        fields = ['id', 'user', 'olympiad', 'answers', 'score', 
                  'percentage', 'time_taken', 'submitted_at', 'status', 'disqualified_reason', 'feedback', 'correct_answers', 'total_questions']

    def get_correct_answers(self, obj):
        # For now return score as proxy for correct count
        # (Assuming 1 point per question, or just showing points)
        return int(obj.score)

    def get_total_questions(self, obj):
        return obj.olympiad.questions.count()

class TestSubmitSerializer(serializers.Serializer):
    answers = serializers.DictField(
        child=serializers.CharField(),
        allow_empty=True
    )
    time_taken = serializers.IntegerField(min_value=0)
    tab_switches = serializers.IntegerField(min_value=0, default=0, required=False)


# ============= CERTIFICATE SERIALIZERS =============

class CertificateSerializer(serializers.ModelSerializer):
    user = UserMiniSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='user', write_only=True, required=True
    )
    course_id = serializers.PrimaryKeyRelatedField(
        queryset=Course.objects.all(), source='course', write_only=True, required=False, allow_null=True
    )
    olympiad_id = serializers.PrimaryKeyRelatedField(
        queryset=Olympiad.objects.all(), source='olympiad', write_only=True, required=False, allow_null=True
    )
    course_title = serializers.CharField(source='course.title', read_only=True, default=None)
    olympiad_title = serializers.CharField(source='olympiad.title', read_only=True, default=None)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    type_display = serializers.CharField(source='get_cert_type_display', read_only=True)
    verified_by_name = serializers.SerializerMethodField()
    source = serializers.SerializerMethodField()
    title = serializers.SerializerMethodField()
    verify_url = serializers.SerializerMethodField()
    
    qr_code = serializers.SerializerMethodField()
    pdf_file = serializers.SerializerMethodField()
    
    class Meta:
        model = Certificate
        fields = ['id', 'cert_number', 'cert_type', 'type_display', 'user', 'user_id',
                  'course_id', 'course_title', 'olympiad_id', 'olympiad_title', 
                  'title', 'source', 'grade', 'score', 'status', 'status_display', 
                  'issued_at', 'verified_at', 'verified_by', 'verified_by_name',
                  'rejection_reason', 'verify_url', 'qr_code', 'pdf_file']

    def get_qr_code(self, obj):
        request = self.context.get('request')
        if obj.qr_code:
            try:
                url = obj.qr_code.url
                if request:
                    return request.build_absolute_uri(url)
                return url
            except Exception:
                return None
        return None

    def get_pdf_file(self, obj):
        request = self.context.get('request')
        if obj.pdf_file:
            try:
                url = obj.pdf_file.url
                if request:
                    return request.build_absolute_uri(url)
                return url
            except Exception:
                return None
        return None
    
    def get_source(self, obj):
        try:
            if obj.course:
                return {'type': 'course', 'title': getattr(obj.course, 'title', 'Noma\'lum'), 'id': obj.course.id}
            elif obj.olympiad:
                return {'type': 'olympiad', 'title': getattr(obj.olympiad, 'title', 'Noma\'lum'), 'id': obj.olympiad.id}
        except Exception:
            pass
        return None
    
    def get_title(self, obj):
        try:
            return obj.title
        except Exception:
            return "Sertifikat"
            
    def get_verify_url(self, obj):
        try:
            return obj.verify_url
        except Exception:
            return ""

    def get_verified_by_name(self, obj):
        try:
            if obj.verified_by:
                return obj.verified_by.get_full_name() or obj.verified_by.username
        except Exception:
            pass
        return None


class CertificateVerifySerializer(serializers.ModelSerializer):
    """Public verification serializer - limited info"""
    user_name = serializers.SerializerMethodField()
    source = serializers.SerializerMethodField()
    type_display = serializers.CharField(source='get_cert_type_display', read_only=True)
    
    class Meta:
        model = Certificate
        fields = ['cert_number', 'cert_type', 'type_display', 'user_name', 
                  'source', 'grade', 'score', 'status', 'issued_at', 'verified_at']
    
    def get_user_name(self, obj):
        return obj.user.get_full_name() or obj.user.username
    
    def get_source(self, obj):
        if obj.course:
            return obj.course.title
        elif obj.olympiad:
            return obj.olympiad.title
        return None


class CertificateRejectSerializer(serializers.Serializer):
    """Serializer for rejecting a certificate"""
    reason = serializers.CharField(required=True, min_length=10, 
                                   help_text="Rad etish sababi (kamida 10 belgi)")


# ============= SUPPORT SERIALIZERS =============

class TicketMessageSerializer(serializers.ModelSerializer):
    is_admin = serializers.SerializerMethodField()
    
    class Meta:
        model = TicketMessage
        fields = ['id', 'sender_id', 'sender_name', 'message', 
                  'is_internal', 'is_admin', 'created_at']

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        request = self.context.get('request')
        if request and request.user.role != 'ADMIN' and instance.is_internal:
            return None
        return ret
    
    def get_is_admin(self, obj):
        try:
            user = User.objects.get(id=obj.sender_id)
            return user.role == 'ADMIN'
        except (User.DoesNotExist, ValueError):
            return False


class SupportTicketSerializer(serializers.ModelSerializer):
    user = UserMiniSerializer(read_only=True)
    messages = TicketMessageSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    messages_count = serializers.SerializerMethodField()
    
    class Meta:
        model = SupportTicket
        fields = ['id', 'ticket_number', 'user', 'subject', 'category', 
                  'priority', 'priority_display', 'status', 'status_display',
                  'messages_count', 'created_at', 'updated_at', 'messages']
    
    def get_messages_count(self, obj):
        return obj.messages.count()


class SupportTicketListSerializer(serializers.ModelSerializer):
    """Lighter serializer for list view"""
    user = UserMiniSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    messages_count = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    
    class Meta:
        model = SupportTicket
        fields = ['id', 'ticket_number', 'user', 'subject', 'category', 
                  'priority', 'priority_display', 'status', 'status_display',
                  'messages_count', 'last_message', 'created_at', 'updated_at']
    
    def get_messages_count(self, obj):
        return obj.messages.count()
    
    def get_last_message(self, obj):
        last = obj.messages.last()
        if last:
            return {
                'sender': last.sender_name,
                'message': last.message[:100],
                'created_at': last.created_at
            }
        return None


class CreateTicketSerializer(serializers.Serializer):
    subject = serializers.CharField(max_length=200)
    category = serializers.ChoiceField(choices=[
        ('Payment', 'To\'lov'),
        ('Technical', 'Texnik'),
        ('Course', 'Kurs'),
        ('Olympiad', 'Olimpiada'),
        ('Certificate', 'Sertifikat'),
        ('Other', 'Boshqa'),
    ])
    priority = serializers.ChoiceField(
        choices=['LOW', 'MEDIUM', 'HIGH'], 
        default='MEDIUM'
    )
    message = serializers.CharField(min_length=10)


# ============= PAYMENT SERIALIZERS =============

class PaymentSerializer(serializers.ModelSerializer):
    user = UserMiniSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    reference_title = serializers.SerializerMethodField()
    receipt_image = serializers.SerializerMethodField()
    
    class Meta:
        model = Payment
        fields = ['id', 'user', 'amount', 'type', 'reference_id', 
                  'reference_title', 'method', 'status', 'status_display',
                  'transaction_id', 'receipt_image', 'created_at', 'completed_at']

    def get_receipt_image(self, obj):
        request = self.context.get('request')
        if obj.receipt_image and request:
            return request.build_absolute_uri(obj.receipt_image.url)
        return obj.receipt_image.url if obj.receipt_image else None
    
    def get_reference_title(self, obj):
        if obj.type == 'COURSE':
            try:
                course = Course.objects.get(id=obj.reference_id)
                return course.title
            except Course.DoesNotExist:
                return None
        elif obj.type == 'OLYMPIAD':
            try:
                olympiad = Olympiad.objects.get(id=obj.reference_id)
                return olympiad.title
            except Olympiad.DoesNotExist:
                return None
        return None


class PaymentCreateSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=['COURSE', 'OLYMPIAD'])
    reference_id = serializers.CharField()
    method = serializers.ChoiceField(
        choices=['PAYME', 'CLICK', 'UZCARD'],
        default='PAYME'
    )


# ============= BOT SERIALIZERS =============

class BotConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = BotConfig
        fields = ['id', 'bot_token', 'admin_chat_id', 'humo_bot_url', 'click_merchant_id', 'is_active', 'updated_at']
        read_only_fields = ['id', 'updated_at']


class PublicBotConfigSerializer(serializers.ModelSerializer):
    """Safe serializer for public/student use"""
    class Meta:
        model = BotConfig
        fields = ['humo_bot_url', 'is_active']


class LevelRewardSerializer(serializers.ModelSerializer):
    class Meta:
        model = LevelReward
        fields = ['id', 'level', 'xp_threshold', 'reward_description', 'icon']







class LeadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lead
        fields = ['id', 'name', 'phone', 'telegram_username', 'status', 'created_at']
        read_only_fields = ['id', 'status', 'created_at']

# ============= CMS SERIALIZERS =============

class TestimonialSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    
    class Meta:
        model = Testimonial
        fields = ['id', 'name', 'profession', 'text_uz', 'text_ru', 'image', 'instagram_url', 'rating', 'is_active', 'is_highlighted', 'created_at']

    def get_image(self, obj):
        request = self.context.get('request')
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        return obj.image.url if obj.image else None
        extra_kwargs = {
            'rating': {'required': False},
            'is_active': {'required': False},
            'is_highlighted': {'required': False},
            'text_ru': {'required': False},
            'instagram_url': {'required': False},
        }

class BannerSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    mobile_image = serializers.SerializerMethodField()
    
    class Meta:
        model = Banner
        fields = ['id', 'title', 'subtitle', 'image', 'mobile_image', 'button_text', 'button_link', 'order', 'is_active', 'created_at']

    def get_image(self, obj):
        request = self.context.get('request')
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        return obj.image.url if obj.image else None

    def get_mobile_image(self, obj):
        request = self.context.get('request')
        if obj.mobile_image and request:
            return request.build_absolute_uri(obj.mobile_image.url)
        return obj.mobile_image.url if obj.mobile_image else None


# Import Settings Serializers
from .serializers_settings import (
    PlatformSettingsSerializer,
    SecuritySettingsSerializer,
    NotificationSettingsSerializer,
    PaymentProviderConfigSerializer,
    PermissionSerializer,
    RolePermissionSerializer,
    AuditLogSerializer
)
