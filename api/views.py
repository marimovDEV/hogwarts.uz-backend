from rest_framework import viewsets, status, generics
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser
import pandas as pd
import json
import os
from rest_framework.exceptions import ValidationError
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from django.db.models import Count, Sum, Avg, Max, Q, Min, F
from django.db import models
from django.shortcuts import get_object_or_404
from django.core.files.storage import default_storage
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
import random
import string
from datetime import timedelta
from decimal import Decimal

from .models import (
    User, Course, Lesson, Enrollment, Olympiad, Question,
    OlympiadRegistration, TestResult, Certificate, SupportTicket,
    TicketMessage, Payment, VerificationCode, BotConfig, LevelReward, UserStreak, ActivityLog,
    HomePageConfig, HomeStat, HomeStep, HomeAdvantage, FreeCourseSection, FreeCourseLessonCard, Subject, TeacherProfile, Notification, Profession,
    ProfessionRoadmapStep, UserProfessionProgress, PaymentProviderConfig,
    Module, LessonPractice, LessonTest, Lead, LessonProgress,
    Testimonial, Winner, Banner, AIAssistantFAQ,
    NotificationBroadcast, NotificationTemplate,
    AIConversation, AIMessage, AIUnansweredQuestion, OlympiadPrize, WinnerPrize, PrizeAddress,
    TeacherWallet, Transaction, Payout, LessonContent, Homework, HomeworkSubmission
)
from .serializers import (
    UserSerializer, UserRegisterSerializer, UserLoginSerializer,
    CourseSerializer, CourseDetailSerializer, LessonSerializer, EnrollmentSerializer,
    OlympiadSerializer, OlympiadDetailSerializer, QuestionSerializer, QuestionAdminSerializer,
    OlympiadPrizeSerializer,
    OlympiadRegistrationSerializer, TestResultSerializer, TestSubmitSerializer,
    CertificateSerializer, CertificateVerifySerializer,
    SupportTicketSerializer, CreateTicketSerializer, TicketMessageSerializer,
    PaymentSerializer, BotConfigSerializer, PublicBotConfigSerializer, LevelRewardSerializer,
    HomePageConfigSerializer, HomeStatSerializer, HomeStepSerializer, HomeAdvantageSerializer, FreeCourseSectionSerializer, FreeCourseLessonCardSerializer,
    SubjectSerializer, SubjectDetailSerializer, CourseCreateSerializer, LessonCreateSerializer, OlympiadCreateSerializer,
    NotificationSerializer, ProfessionSerializer, UserProfessionProgressSerializer,
    ModuleSerializer, LessonProgressSerializer, LearningLessonSerializer,
    TeacherLessonPracticeSerializer, TeacherLessonTestSerializer, 
    TeacherModuleSerializer, TeacherLessonSerializer, TeacherCourseDetailSerializer, LeadSerializer,
    TestimonialSerializer, WinnerSerializer, BannerSerializer, AIAssistantFAQSerializer,
    NotificationBroadcastSerializer, NotificationTemplateSerializer,
    AIConversationSerializer, AIMessageSerializer, AIUnansweredQuestionSerializer,
    WinnerPrizeSerializer, PrizeAddressSerializer,
    TeacherWalletSerializer, TransactionSerializer, PayoutSerializer,
    LessonContentSerializer, HomeworkSerializer, HomeworkSubmissionSerializer
)
from .streak_service import StreakService
from .services.learning_service import LearningService
from .authentication import generate_token
from .permissions import IsAdmin, IsOwnerOrAdmin, IsTeacher, IsTeacherOrAdmin, HasCourseAccess
from .pagination import StandardPagination, SmallPagination
from .telegram_service import TelegramService, generate_verification_code, format_phone_number
from .utils import generate_unique_id


from .services.notification_service import NotificationService
from .services.olympiad_service import OlympiadService
from .services.email_service import EmailService
from .bot_service import BotService
from .services.certificate_service import CertificateService
from .services.reward_service import RewardService
from .services.sms_service import EskizSMSService


# ============= TELEGRAM AUTH VIEWS =============

@api_view(['POST'])
@permission_classes([AllowAny])
def send_verification_code(request):
    """
    Send verification code via Telegram - only phone required
    
    POST /api/auth/send-code/
    Body: { phone }
    """
    request_type = request.data.get('type', 'register') # 'register' or 'recover'
    phone = request.data.get('phone')
    
    if not phone:
        return Response({
            'success': False,
            'error': 'Telefon raqami talab qilinadi'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if phone already registered
    user_exists = User.objects.filter(phone=phone).exists()

    if request_type == 'register' and user_exists:
        return Response({
            'success': False,
            'error': 'Bu telefon raqami allaqachon ro\'yxatdan o\'tgan'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if request_type == 'recover' and not user_exists:
        return Response({
            'success': False,
            'error': 'Bu raqam bilan foydalanuvchi topilmadi'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Generate verification code
    code = generate_verification_code(6)
    
    # Delete old verification codes for this phone
    VerificationCode.objects.filter(phone=phone).delete()
    
    # Create new verification code (expires in 10 minutes)
    verification = VerificationCode.objects.create(
        phone=phone,
        code=code,
        expires_at=timezone.now() + timedelta(minutes=10)
    )
    
    # Format message for SMS
    formatted_phone = format_phone_number(phone)
    if request_type == 'recover':
        title = "HOGWARTS: Parolni tiklash."
    else:
        title = "HOGWARTS: Yangi ro'yxatdan o'tish."

    message = f"{title}\nSizning tasdiqlash kodingiz: {code}\nKod 10 daqiqa davomida amal qiladi."
    
    # Send via Eskiz SMS
    sms_sent = EskizSMSService.send_sms(phone, message)
    
    if not sms_sent:
        # Fallback to Telegram Admin in case SMS fails
        TelegramService.send_to_admin(f"SMS yuborishda xatolik ({phone}):\n{message}")
    
    return Response({
        'success': True,
        'message': 'Tasdiqlash kodi yuborildi'
    })

@api_view(['POST'])
@permission_classes([AllowAny])
def forgot_password(request):
    """
    Initiate password recovery
    POST /api/auth/forgot-password/
    Body: { phone }
    """
    phone = request.data.get('phone')
    if not phone:
        return Response({'success': False, 'error': 'Telefon raqam kiritilishi shart'}, status=400)
    
    user = User.objects.filter(phone=phone).first()
    if not user:
        return Response({'success': False, 'error': 'Bunday foydalanuvchi topilmadi'}, status=404)
    
    # Generate and send code
    code = generate_verification_code(6)
    VerificationCode.objects.filter(phone=phone).delete()
    VerificationCode.objects.create(
        phone=phone,
        code=code,
        expires_at=timezone.now() + timedelta(minutes=10)
    )
    
    sms_message = f"HOGWARTS: Parolni tiklash.\nSizning tasdiqlash kodingiz: {code}\nKod 10 daqiqa davomida amal qiladi."
    sms_sent = EskizSMSService.send_sms(phone, sms_message)
    
    if not sms_sent:
        # Fallback to Telegram if SMS service fails
        tg_message = f"""
🔐 <b>Parolni tiklash</b>

👤 <b>User:</b> {user.first_name} {user.last_name}
📱 <b>Telefon:</b> {phone}
🔢 <b>Tasdiqlash kodi:</b> <code>{code}</code>

Kod 10 daqiqa davomida amal qiladi.
"""
        if user.telegram_id:
            TelegramService.send_message(user.telegram_id, tg_message)
        else:
            TelegramService.send_to_admin(tg_message + "\n\n⚠️ SMS yuborishda xatolik bo'lganligi sababli adminga yuborildi.")
    
    return Response({'success': True, 'message': 'Tasdiqlash kodi yuborildi'})

@api_view(['POST'])
@permission_classes([AllowAny])
def verify_reset_code(request):
    """
    Verify recovery code
    POST /api/auth/verify-reset-code/
    Body: { phone, code }
    """
    phone = request.data.get('phone')
    code = request.data.get('code')
    
    if not phone or not code:
        return Response({'success': False, 'error': 'Ma\'lumotlar yetarli emas'}, status=400)
        
    verification = VerificationCode.objects.filter(
        phone=phone,
        expires_at__gt=timezone.now()
    ).first()
    
    if not verification:
        return Response({'success': False, 'error': 'Kod muddati tugagan yoki xato'}, status=400)
        
    # Check attempts
    if verification.attempts >= 3:
        return Response({'success': False, 'error': 'Urinishlar soni tugadi. Qaytadan kod so\'rang.'}, status=403)
        
    if verification.code != code:
        verification.attempts += 1
        verification.save()
        remaining = 3 - verification.attempts
        return Response({'success': False, 'error': f'Kod noto\'g\'ri. {remaining} ta urinish qoldi.'}, status=400)
        
    # Correct code
    verification.is_verified = True
    verification.save()
    
    return Response({'success': True, 'message': 'Kod tasdiqlandi'})

@api_view(['POST'])
@permission_classes([AllowAny])
def reset_password(request):
    """
    Set new password
    POST /api/auth/reset-password/
    Body: { phone, code, new_password }
    """
    phone = request.data.get('phone')
    code = request.data.get('code') # We re-verify code or use token. Re-verifying logic here.
    new_password = request.data.get('new_password')

    if not all([phone, code, new_password]):
        return Response({'success': False, 'error': 'Barcha maydonlar to\'ldirilishi shart'}, status=400)

    # Verify again (Double check is_verified is True from previous step)
    verification = VerificationCode.objects.filter(
        phone=phone,
        code=code,
        is_verified=True, 
        expires_at__gt=timezone.now()
    ).first()

    if not verification:
         return Response({'success': False, 'error': 'Kod tasdiqlanmagan yoki muddati tugagan'}, status=400)

    try:
        user = User.objects.get(phone=phone)
        if len(new_password) < 8:
             return Response({'success': False, 'error': 'Parol kamida 8 ta belgidan iborat bo\'lishi kerak'}, status=400)
        
        user.password = make_password(new_password)
        user.save()
        
        verification.delete()
        
        return Response({'success': True, 'message': 'Parol muvaffaqiyatli o\'zgartirildi'})
    except User.DoesNotExist:
        return Response({'success': False, 'error': 'Foydalanuvchi topilmadi'}, status=404)




@api_view(['POST'])
@permission_classes([AllowAny])
def verify_code(request):
    """
    Verify code only - does NOT create user
    
    POST /api/auth/verify-code/
    Body: { phone, code }
    """
    phone = request.data.get('phone')
    code = request.data.get('code')
    
    if not phone or not code:
        return Response({
            'success': False,
            'error': 'Telefon raqami va kod talab qilinadi'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        verification = VerificationCode.objects.get(phone=phone, is_verified=False)
    except VerificationCode.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Tasdiqlash kodi topilmadi. Qayta urinib ko\'ring.'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Check attempts
    verification.attempts += 1
    verification.save(update_fields=['attempts'])
    
    if verification.attempts > 5:
        return Response({
            'success': False,
            'error': 'Juda ko\'p urinish. Yangi kod oling.'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Check expiration
    if verification.is_expired():
        return Response({
            'success': False,
            'error': 'Tasdiqlash kodi muddati tugagan. Yangi kod oling.'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Verify code
    if verification.code != code:
        return Response({
            'success': False,
            'error': f'Kod noto\'g\'ri. Qolgan urinishlar: {5 - verification.attempts}'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Mark as verified but DON'T create user yet
    verification.is_verified = True
    verification.save(update_fields=['is_verified'])
    
    return Response({
        'success': True,
        'message': 'Kod tasdiqlandi',
        'phone': phone,
        'verified': True
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def complete_registration(request):
    """
    Complete registration with all student info
    
    POST /api/auth/complete-registration/
    Body: { phone, first_name, last_name, birth_date, region, school, grade, password }
    """
    phone = request.data.get('phone')
    first_name = request.data.get('first_name')
    last_name = request.data.get('last_name')
    birth_date = request.data.get('birth_date')
    region = request.data.get('region')
    school = request.data.get('school')
    grade = request.data.get('grade')
    password = request.data.get('password')
    
    if not phone:
        return Response({
            'success': False,
            'error': 'Telefon raqami talab qilinadi'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if not first_name or not last_name:
        return Response({
            'success': False,
            'error': 'Ism va familiya talab qilinadi'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if not password or len(password) < 6:
        return Response({
            'success': False,
            'error': 'Parol kamida 6 ta belgidan iborat bo\'lishi kerak'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if phone was verified
    try:
        verification = VerificationCode.objects.get(phone=phone, is_verified=True)
    except VerificationCode.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Telefon raqami tasdiqlanmagan. Avval kodni tasdiqlang.'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if user already exists
    if User.objects.filter(phone=phone).exists():
        return Response({
            'success': False,
            'error': 'Bu telefon raqami allaqachon ro\'yxatdan o\'tgan'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Create username from phone
    username = phone.replace('+', '').replace(' ', '')
    
    # Create user with all info
    from django.contrib.auth.hashers import make_password
    user = User.objects.create(
        username=username,
        email=f"{username}@olimpiada.uz",  # Auto-generate email
        password=make_password(password),
        first_name=first_name,
        last_name=last_name,
        phone=phone,
        birth_date=birth_date if birth_date else None,
        region=region or '',
        school=school or '',
        grade=grade or '',
        role='STUDENT'
    )
    
    # Delete verification code
    verification.delete()
    
    # Generate token
    token = generate_token(user)
    
    # Send success notification to Telegram (Admin)
    formatted_phone = format_phone_number(phone)
    success_message = f"""
✅ <b>Yangi foydalanuvchi ro'yxatdan o'tdi!</b>

👤 <b>Ism:</b> {first_name} {last_name}
📱 <b>Telefon:</b> {formatted_phone}
📍 <b>Viloyat:</b> {region or '-'}
🏫 <b>Maktab:</b> {school or '-'}
📚 <b>Sinf:</b> {grade or '-'}

🎉 Muvaffaqiyatli!
"""
    TelegramService.send_to_admin(success_message)

    # Email Welcome
    EmailService.send_welcome_email(user)
    
    return Response({
        'success': True,
        'message': 'Ro\'yxatdan muvaffaqiyatli o\'tdingiz!',
        'user': UserSerializer(user).data,
        'token': token
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([AllowAny])
def resend_code(request):
    """
    Resend verification code
    
    POST /api/auth/resend-code/
    Body: { phone }
    """
    phone = request.data.get('phone')
    
    if not phone:
        return Response({
            'success': False,
            'error': 'Telefon raqami talab qilinadi'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        verification = VerificationCode.objects.get(phone=phone, is_verified=False)
    except VerificationCode.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Avval ro\'yxatdan o\'ting'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Generate new code
    new_code = generate_verification_code(6)
    verification.code = new_code
    verification.attempts = 0
    verification.expires_at = timezone.now() + timedelta(minutes=10)
    verification.save()
    
    # Send to Telegram
    formatted_phone = format_phone_number(phone)
    message = f"""
🔄 <b>Qayta yuborilgan kod</b>

📱 <b>Telefon:</b> {formatted_phone}
👤 <b>Username:</b> {verification.username}

🔢 <b>Yangi tasdiqlash kodi:</b> <code>{new_code}</code>

⏰ Kod 10 daqiqa ichida yaroqli.
"""
    
    TelegramService.send_to_admin(message)
    
    return Response({
        'success': True,
        'message': 'Yangi kod yuborildi'
    })


# ============= AUTH VIEWS =============

@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """
    Register a new user (Direct registration without verification)
    
    POST /api/auth/register/
    Body: { username, email, password, first_name, last_name, phone }
    """
    serializer = UserRegisterSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        token = generate_token(user)
        return Response({
            'success': True,
            'message': 'Foydalanuvchi muvaffaqiyatli ro\'yxatdan o\'tdi',
            'user': UserSerializer(user).data,
            'token': token
        }, status=status.HTTP_201_CREATED)
    return Response({
        'success': False,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """
    Login user and return token
    
    POST /api/auth/login/
    Body: { email, password }
    """
    serializer = UserLoginSerializer(data=request.data)
    if serializer.is_valid():
        email = serializer.validated_data.get('email')
        username = serializer.validated_data.get('username')
        password = serializer.validated_data['password']
        
        user = None
        
        if not email and username:
            email = username

        # Try fetch by email or username
        # Try fetch by email, username OR phone
        if email:
            # Check if input is email-like
            if '@' in email:
                user = User.objects.filter(email=email).first()
            else:
                # Try as phone number (remove + and spaces)
                clean_input = email.replace('+', '').replace(' ', '')
                if clean_input.isdigit():
                    # Try exact match (with or without 998? storage is +998...)
                    # Let's try flexible:
                    # 1. Exact match with +
                    user = User.objects.filter(phone=f"+{clean_input}").first()
                    # 2. Exact match without +
                    if not user:
                         user = User.objects.filter(phone=clean_input).first()
                    # 3. Match suffix (last 9 digits) if length is 9
                    if not user and len(clean_input) >= 9:
                         user = User.objects.filter(phone__endswith=clean_input[-9:]).first()
                
                # If still not found, try as username
                if not user:
                    user = User.objects.filter(username=email).first()

        if not user:
             return Response({
                'success': False,
                'error': 'Login yoki parol noto\'g\'ri'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        if not user.check_password(password):
            return Response({
                'success': False,
                'error': 'Login yoki parol noto\'g\'ri'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        if not user.is_active:
            return Response({
                'success': False,
                'error': 'Hisobingiz faol emas'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Update last login
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])
        
        token = generate_token(user)
        return Response({
            'success': True,
            'message': 'Tizimga muvaffaqiyatli kirdingiz',
            'user': UserSerializer(user).data,
            'token': token
        })
    return Response({
        'success': False,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([AllowAny])
def check_username(request):
    """
    Check if username is available
    
    GET /api/auth/check-username/?username=xxx
    """
    username = request.GET.get('username', '').strip().lower()
    
    if not username:
        return Response({
            'available': False,
            'error': 'Username talab qilinadi'
        })
    
    if len(username) < 3:
        return Response({
            'available': False,
            'error': 'Username kamida 3 ta belgidan iborat bo\'lishi kerak'
        })
    
    # Check if username exists
    exists = User.objects.filter(username__iexact=username).exists()
    
    return Response({
        'available': not exists,
        'username': username
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    """Get current user profile"""
    return Response({
        'success': True,
        'user': UserSerializer(request.user).data
    })


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_profile(request):
    """
    Update user profile with all fields including username
    
    PUT/PATCH /api/auth/profile/
    Body: { username, first_name, last_name, phone, birth_date, region, school, grade }
    """
    user = request.user
    data = request.data
    
    # Handle username change with uniqueness check
    new_username = data.get('username')
    if new_username and new_username != user.username:
        # Validate username format
        new_username = new_username.strip().lower()
        if len(new_username) < 3:
            return Response({
                'success': False,
                'error': 'Username kamida 3 ta belgidan iborat bo\'lishi kerak'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check uniqueness
        if User.objects.filter(username__iexact=new_username).exclude(id=user.id).exists():
            return Response({
                'success': False,
                'error': 'Bu username band'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        user.username = new_username
    
    # Update other fields
    if 'first_name' in data:
        user.first_name = data['first_name']
    
    if 'last_name' in data:
        user.last_name = data['last_name']
    
    if 'phone' in data:
        user.phone = data['phone']
    
    if 'birth_date' in data:
        birth_date = data['birth_date']
        if birth_date:
            user.birth_date = birth_date
        else:
            user.birth_date = None
    
    if 'region' in data:
        user.region = data['region'] or ''
    
    if 'school' in data:
        user.school = data['school'] or ''
    
    if 'grade' in data:
        user.grade = data['grade'] or ''
    
    if 'language' in data:
        user.language = data['language']
    
    user.save()
    
    # Handle Teacher Profile if user is teacher
    if user.role == 'TEACHER':
        teacher_profile, created = TeacherProfile.objects.get_or_create(user=user)
        
        tp_fields = ['bio', 'experience_years', 'specialization', 'telegram_username', 
                     'instagram_username', 'youtube_channel', 'linkedin_profile']
        
        updated_tp = False
        for field in tp_fields:
            if field in data:
                val = data[field]
                # Convert empty strings to default values if needed
                if field == 'experience_years':
                    try:
                        val = int(val) if val else 0
                    except:
                        val = 0
                setattr(teacher_profile, field, val)
                updated_tp = True
        
        if updated_tp:
            teacher_profile.save()

    
    return Response({
        'success': True,
        'message': 'Profil muvaffaqiyatli yangilandi',
        'user': UserSerializer(user).data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    """Change user password"""
    old_password = request.data.get('old_password')
    new_password = request.data.get('new_password')
    
    if not old_password or not new_password:
        return Response({
            'success': False,
            'error': 'Eski va yangi parol talab qilinadi'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if not request.user.check_password(old_password):
        return Response({
            'success': False,
            'error': 'Eski parol noto\'g\'ri'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if len(new_password) < 6:
        return Response({
            'success': False,
            'error': 'Yangi parol kamida 6 ta belgidan iborat bo\'lishi kerak'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    request.user.set_password(new_password)
    request.user.save()
    
    return Response({
        'success': True,
        'message': 'Parol muvaffaqiyatli o\'zgartirildi'
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_avatar(request):
    """Upload user avatar"""
    if 'avatar' not in request.FILES:
        return Response({
            'success': False,
            'error': 'Avatar fayli talab qilinadi'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    request.user.avatar = request.FILES['avatar']
    request.user.save()
    
    return Response({
        'success': True,
        'message': 'Avatar yuklandi',
        'avatar_url': request.user.avatar.url if request.user.avatar else None
    })


# ============= COURSE VIEWS =============

class CourseViewSet(viewsets.ModelViewSet):
    """
    Course API endpoints
    
    GET /api/courses/ - List all courses (with filters)
    GET /api/courses/{id}/ - Get course details
    POST /api/courses/ - Create course (Admin)
    PUT /api/courses/{id}/ - Update course (Admin)
    DELETE /api/courses/{id}/ - Delete course (Admin)
    POST /api/courses/{id}/enroll/ - Enroll in course
    GET /api/courses/my_courses/ - Get enrolled courses
    """
    queryset = Course.objects.filter(is_active=True)
    serializer_class = CourseSerializer
    permission_classes = [AllowAny]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['title', 'description', 'subject__name']
    ordering_fields = ['created_at', 'price', 'rating', 'students_count']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return CourseDetailSerializer
        if self.action == 'learning_state':
            return ModuleSerializer
        return CourseSerializer

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated, IsTeacherOrAdmin])
    def analytics(self, request, pk=None):
        course = self.get_object()
        enrollments = Enrollment.objects.filter(course=course)
        total_students = enrollments.count()
        
        if total_students == 0:
            return Response({
                'total_students': 0,
                'completion_rate': 0,
                'lessons': []
            })
            
        completed_students = enrollments.filter(completed_at__isnull=False).count()
        completion_rate = (completed_students / total_students * 100) if total_students > 0 else 0
        
        # Get all lessons for this course
        lessons = Lesson.objects.filter(course=course).order_by('order')
        lesson_stats = []
        
        for lesson in lessons:
            # Count how many students have progress for this lesson
            reached = LessonProgress.objects.filter(lesson=lesson).count()
            completed = LessonProgress.objects.filter(lesson=lesson, is_completed=True).count()
            
            lesson_stats.append({
                'id': lesson.id,
                'title': lesson.title,
                'reached_count': reached,
                'completed_count': completed,
                'dropoff_rate': ((reached - completed) / reached * 100) if reached > 0 else 0
            })
            
        return Response({
            'total_students': total_students,
            'completed_students': completed_students,
            'completion_rate': completion_rate,
            'lessons': lesson_stats
        })

    def perform_create(self, serializer):
        user = self.request.user
        # Check teacher status
        if user.role == 'TEACHER':
            teacher_profile = getattr(user, 'teacher_profile', None)
            teacher_type = getattr(teacher_profile, 'teacher_type', 'NORMAL')
            
            # Normal teachers have limits unless they pay (creation_fee_paid)
            is_privileged = teacher_type in ['VIP', 'INTERNAL'] or getattr(teacher_profile, 'is_premium', False)
            
            if not is_privileged:
                # Check if they have already created a course and haven't paid for the new one
                # Note: creation_fee_paid should be handled by a separate payment webhook
                existing_courses = Course.objects.filter(teacher=user).count()
                if existing_courses >= 1:
                    # We can allow creation if they have a 'creation_fee_paid' flag (which we added to Course model)
                    # But serializer.validated_data might not have it yet.
                    pass 

            # Auto-assign teacher and set status to DRAFT
            course = serializer.save(teacher=user, status='DRAFT')
            
            # Set is_internal if teacher is INTERNAL
            if teacher_type == 'INTERNAL':
                course.is_internal = True
                course.save(update_fields=['is_internal'])
        else:
            course = serializer.save()

        # Trigger notification for new course if active
        if course.is_active:
            from .services.notification_service import NotificationService
            from .models import NotificationBroadcast
            
            # Create a broadcast record for history
            broadcast = NotificationBroadcast.objects.create(
                title="Yangi kurs e'lon qilindi!",
                message=f"{course.title} kursi endi platformamizda muvjud. Hoziroq o'rganishni boshlang!",
                audience_type='ALL',
                notification_type='COURSE',
                channel='ALL',
                link=f"/courses/{course.id}",
                status='SENT',
                sent_at=timezone.now(),
                created_by=user if user.is_authenticated else None
            )
            NotificationService.broadcast_notification(broadcast.id)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsTeacherOrAdmin])
    def reorder_lessons(self, request, pk=None):
        """Reorder lessons within a course"""
        items = request.data.get('items', [])
        if not items:
            return Response({'error': 'items is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        course = self.get_object()
        for item in items:
            Lesson.objects.filter(id=item['id'], course=course).update(order=item['order'])
            
        return Response({'success': True})

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsTeacherOrAdmin])
    def reorder_modules(self, request, pk=None):
        """Reorder modules within a course"""
        items = request.data.get('items', [])
        if not items:
            return Response({'error': 'items is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        course = self.get_object()
        for item in items:
            Module.objects.filter(id=item['id'], course=course).update(order=item['order'])
            
        return Response({'success': True})
    
    @action(detail=True, methods=['get'])
    def modules(self, request, pk=None):
        """Get modules for a specific course"""
        course = self.get_object()
        modules = course.modules.all()
        serializer = ModuleSerializer(modules, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def set_current_lesson(self, request, pk=None):
        """Update the user's current lesson for this course"""
        lesson_id = request.data.get('lesson_id')
        if not lesson_id:
            return Response({'error': 'lesson_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        result = LearningService.set_current_lesson(request.user, pk, lesson_id)
        if result:
            return Response({'success': True})
        return Response({'error': 'Failed to update current lesson'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def learning_state(self, request, pk=None):
        """Get the detailed learning state for the course"""
        user = request.user
        state = LearningService.get_course_learning_state(user, pk)
        
        # Serialize modules (which include lessons with progress)
        serializer = ModuleSerializer(state['modules'], many=True)
        
        return Response({
            "enrollment": EnrollmentSerializer(state['enrollment']).data,
            "modules": serializer.data
        })
    
    
    def get_queryset(self):
        queryset = Course.objects.filter(is_active=True)
        user = self.request.user

        # Admin sees all
        if user.is_authenticated and user.role == 'ADMIN':
            queryset = Course.objects.all()
        # Teacher sees own courses and co-taught courses
        elif user.is_authenticated and user.role == 'TEACHER':
            queryset = Course.objects.filter(Q(teacher=user) | Q(teachers=user)).distinct()
        else:
            # Public
            queryset = Course.objects.filter(is_active=True)
        
        # Manual filters (keep existing logic)
        subject = self.request.query_params.get('subject')
        level = self.request.query_params.get('level')
        teacher_id = self.request.query_params.get('teacher')
        featured = self.request.query_params.get('featured')
        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')
        
        if teacher_id:
            queryset = queryset.filter(teacher_id=teacher_id)
        if subject:
            queryset = queryset.filter(subject__iexact=subject)
        if level:
            queryset = queryset.filter(level=level.upper())
        if featured == 'true':
            queryset = queryset.filter(is_featured=True)
        if min_price:
            queryset = queryset.filter(price__gte=float(min_price))
        if max_price:
            queryset = queryset.filter(price__lte=float(max_price))
        
        return queryset
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'add_lesson', 'update_lesson', 'delete_lesson']:
            return [IsAuthenticated(), IsTeacherOrAdmin()]
        return [AllowAny()]


    def perform_update(self, serializer):
        # Prevent teachers from activating unapproved courses
        if self.request.user.role == 'TEACHER':
            # If teacher is trying to activate, ensure it's approved
            is_active = self.request.data.get('is_active')
            if is_active is True and serializer.instance.status != 'APPROVED':
                from rest_framework.exceptions import ValidationError
                raise ValidationError("Kursni aktivlashtirish uchun u avval tasdiqlanishi kerak.")
            
            # Teachers can only set status to DRAFT or PENDING
            new_status = self.request.data.get('status')
            if new_status and new_status not in ['DRAFT', 'PENDING']:
                from rest_framework.exceptions import ValidationError
                raise ValidationError("Siz faqat 'DRAFT' yoki 'PENDING' statusini o'rnata olasiz.")
                
            # Prevent updating sensitive fields
            for field in ['teacher_percentage', 'platform_percentage', 'admin', 'price']:
                 if field in serializer.validated_data:
                      serializer.validated_data.pop(field)

        serializer.save()

    @action(detail=True, methods=['post'], permission_classes=[IsAdmin])
    def approve(self, request, pk=None):
        course = self.get_object()
        course.status = 'APPROVED'
        course.save()
        
        # Send notification to teacher
        if course.teacher:
            Notification.objects.create(
                user=course.teacher,
                title="Kurs tasdiqlandi! 🎉",
                message=f"Tabriklaymiz! '{course.title}' kursi adminlar tomonidan tasdiqlandi va nashr qilindi.",
                notification_type='COURSE',
                channel='ALL',
                link=f"/teacher/courses"
            )
            
        return Response({'success': True, 'message': 'Kurs tasdiqlandi'})

    @action(detail=True, methods=['post'], permission_classes=[IsAdmin])
    def reject(self, request, pk=None):
        reason = request.data.get('reason', '')
        course = self.get_object()
        course.status = 'REJECTED'
        course.is_active = False # Ensure it's not active if rejected
        course.save()
        
        # Send notification to teacher
        if course.teacher:
            msg = f"'{course.title}' kursi rad etildi."
            if reason:
                msg += f" Sabab: {reason}"
            
            Notification.objects.create(
                user=course.teacher,
                title="Kurs rad etildi",
                message=msg,
                notification_type='COURSE',
                channel='ALL',
                link=f"/teacher/courses"
            )
            
        return Response({'success': True, 'message': 'Kurs rad etildi'})
    
    def create(self, request, *args, **kwargs):
        """Create a new course"""
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            is_internal = False
            creation_fee_paid = False
            
            if user.role == 'TEACHER':
                profile = getattr(user, 'teacher_profile', None)
                if profile:
                    if getattr(profile, 'teacher_type', None) == 'INTERNAL':
                        is_internal = True
                        creation_fee_paid = True
                    elif getattr(profile, 'is_vip', False):
                        creation_fee_paid = True
            else:
                creation_fee_paid = True # Admin creates for free
                
            # If admin provided a teacher in data, keep it. Otherwise default to user if teacher.
            assigned_teacher = serializer.validated_data.get('teacher', user if user.role == 'TEACHER' else None)

            # Teachers must be moderated
            status_val = 'APPROVED' if user.role == 'ADMIN' else 'PENDING'

            course = serializer.save(
                teacher=assigned_teacher,
                is_internal=is_internal,
                creation_fee_paid=creation_fee_paid,
                status=status_val
            )

            # Notify Admins if teacher created
            if user.role == 'TEACHER':
                admins = User.objects.filter(role='ADMIN', is_active=True)
                title = "Yangi kurs (Moderatsiya)"
                message = f"O'qituvchi {user.username} yangi kurs yaratdi: {course.title}. Iltimos, ko'rib chiqing va tasdiqlang."
                
                for admin in admins:
                    NotificationService.create_notification(
                        user=admin,
                        title=title,
                        message=message,
                        notification_type='COURSE',
                        channel='ALL' # Web + Telegram if linked
                    )
                
                # Direct Telegram to system admin channel/group if configured
                config = BotConfig.objects.filter(is_active=True).first()
                if config and config.admin_chat_id:
                    tg_msg = f"🆕 <b>Yangi kurs (Moderatsiya)</b>\n\n👤 O'qituvchi: {user.username}\n📚 Kurs: {course.title}\n\nTasdiqlash kutilmoqda."
                    BotService.send_to_admin(tg_msg)
            return Response({
                'success': True,
                'message': 'Kurs yaratildi',
                'course': CourseSerializer(course).data
            }, status=status.HTTP_201_CREATED)
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def enroll(self, request, pk=None):
        """Enroll in a course"""
        course = self.get_object()
        user = request.user
        
        # Check if already enrolled
        if Enrollment.objects.filter(user=user, course=course).exists():
            return Response({
                'success': False,
                'error': 'Siz allaqachon ushbu kursga yozilgansiz'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if course is paid and user has paid
        if course.price > 0:
            # Check for completed payment
            payment_exists = Payment.objects.filter(
                user=user,
                type='COURSE',
                reference_id=str(course.id),
                status='COMPLETED'
            ).exists()
            
            if not payment_exists:
                return Response({
                    'success': False,
                    'error': 'Kurs uchun to\'lov amalga oshirilmagan',
                    'requires_payment': True,
                    'price': float(course.price)
                }, status=status.HTTP_402_PAYMENT_REQUIRED)
        
        first_lesson = course.lessons.all().order_by('module__order', 'order').first()
        enrollment = Enrollment.objects.create(
            user=user, 
            course=course,
            current_lesson=first_lesson
        )
        
        # Add XP
        user.add_xp(50, 'COURSE_ENROLL', f"Kursga yozildi: {course.title}")
        
        return Response({
            'success': True,
            'message': 'Kursga muvaffaqiyatli yozildingiz',
            'enrollment': EnrollmentSerializer(enrollment).data
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def buy(self, request, pk=None):
        """Purchase a course using AC balance"""
        course = self.get_object()
        user = request.user
        
        # 1. Check if already enrolled
        if Enrollment.objects.filter(user=user, course=course).exists():
            return Response({'error': 'Siz allaqachon ushbu kursga yozilgansiz'}, status=status.HTTP_400_BAD_REQUEST)
            
        # 2. Check balance
        if user.balance < course.price:
            return Response({'error': 'Mablag\' yetarli emas', 'requires_balance': float(course.price - user.balance)}, status=status.HTTP_402_PAYMENT_REQUIRED)
            
        # 3. Deduct balance & Create Payment record
        user.balance -= course.price
        user.save(update_fields=['balance'])
        
        payment = Payment.objects.create(
            user=user,
            type='COURSE',
            reference_id=str(course.id),
            amount=course.price,
            status='COMPLETED',
            payment_method='BALANCE'
        )

        # 4. Revenue Split Logic
        if course.teacher and course.price > 0:
            from .models import CommissionSettings, TeacherWallet, Transaction
            
            # Dynamic commission based on teacher type
            settings = CommissionSettings.load()
            teacher_type = 'NORMAL'
            if hasattr(course.teacher, 'teacher_profile'):
                teacher_type = course.teacher.teacher_profile.teacher_type
                
            platform_percent = settings.default_commission
            if teacher_type == 'VIP':
                platform_percent = settings.vip_commission
            elif teacher_type == 'INTERNAL':
                platform_percent = settings.internal_commission
                
            platform_share = (course.price * platform_percent) / 100
            teacher_share = course.price - platform_share
            
            # Update Teacher Wallet
            wallet, created = TeacherWallet.objects.get_or_create(teacher=course.teacher)
            wallet.pending_balance += teacher_share
            wallet.total_earned += teacher_share
            wallet.save()
            
            # Create Transaction for Teacher (Income)
            Transaction.objects.create(
                transaction_type='COURSE_SALE',
                user=course.teacher,
                course=course,
                amount=course.price,
                teacher_earnings=teacher_share,
                platform_commission=platform_share,
                status='SUCCESS',
                description=f"Kurs sotuvi: {course.title} ({100-platform_percent}% ulush)",
                metadata={'purchase_id': payment.id, 'student_id': user.id}
            )
            
            # Create Transaction for Platform (optional, for tracking)
            admin_user = User.objects.filter(role='ADMIN').first()
            if admin_user:
                Transaction.objects.create(
                    transaction_type='COMMISSION',
                    user=admin_user,
                    course=course,
                    amount=course.price,
                    teacher_earnings=0,
                    platform_commission=platform_share,
                    status='SUCCESS',
                    description=f"Platforma komissiyasi: {course.title} ({platform_percent}%)",
                    metadata={'purchase_id': payment.id}
                )
        
        # 5. Enroll
        first_lesson = course.lessons.all().order_by('module__order', 'order').first()
        enrollment = Enrollment.objects.create(
            user=user, 
            course=course,
            current_lesson=first_lesson
        )
        
        course.students_count += 1
        course.save(update_fields=['students_count'])
        
        # Initial XP for buying
        user.add_xp(50, 'COURSE_ENROLL', f"Kurs sotib olindi: {course.title}")
        
        return Response({
            'success': True,
            'message': 'Kurs muvaffaqiyatli sotib olindi',
            'enrollment': EnrollmentSerializer(enrollment).data
        })

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_courses(self, request):
        """Get user's enrolled courses"""
        enrollments = Enrollment.objects.filter(user=request.user).select_related('course')
        serializer = EnrollmentSerializer(enrollments, many=True)
        return Response({
            'success': True,
            'enrollments': serializer.data
        })
    
    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def lessons(self, request, pk=None):
        """Get all lessons for a course (if enrolled or admin)"""
        course = self.get_object()
        user = request.user
        
        # Check access
        if user.role != 'ADMIN':
            if not Enrollment.objects.filter(user=user, course=course).exists():
                # Return only free lessons
                lessons = course.lessons.filter(is_free=True)
                return Response({
                    'success': True,
                    'enrolled': False,
                    'lessons': LessonSerializer(lessons, many=True).data
                })
        
        lessons = course.lessons.all()
        return Response({
            'success': True,
            'enrolled': True,
            'lessons': LessonSerializer(lessons, many=True).data
        })
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def add_lesson(self, request, pk=None):
        """Add lesson to course (Admin only)"""
        if request.user.role != 'ADMIN':
            return Response({'error': 'Admin huquqi talab qilinadi'}, status=status.HTTP_403_FORBIDDEN)
        
        course = self.get_object()
        serializer = LessonSerializer(data=request.data)
        if serializer.is_valid():
            lesson = serializer.save(course=course)
            course.lessons_count = course.lessons.count()
            course.save(update_fields=['lessons_count'])
            return Response({
                'success': True,
                'message': 'Dars qo\'shildi',
                'lesson': LessonSerializer(lesson).data
            }, status=status.HTTP_201_CREATED)
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['put'], url_path='lessons/(?P<lesson_id>[^/.]+)', permission_classes=[IsAuthenticated])
    def update_lesson(self, request, pk=None, lesson_id=None):
        """Update a lesson (Admin only)"""
        if request.user.role != 'ADMIN':
            return Response({'error': 'Admin huquqi talab qilinadi'}, status=status.HTTP_403_FORBIDDEN)
        
        lesson = get_object_or_404(Lesson, id=lesson_id, course_id=pk)
        serializer = LessonSerializer(lesson, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Dars yangilandi',
                'lesson': serializer.data
            })
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['delete'], url_path='lessons/(?P<lesson_id>[^/.]+)', permission_classes=[IsAuthenticated])
    def delete_lesson(self, request, pk=None, lesson_id=None):
        """Delete a lesson (Admin only)"""
        if request.user.role != 'ADMIN':
            return Response({'error': 'Admin huquqi talab qilinadi'}, status=status.HTTP_403_FORBIDDEN)
        
        lesson = get_object_or_404(Lesson, id=lesson_id, course_id=pk)
        lesson.delete()
        
        course = self.get_object()
        course.lessons_count = course.lessons.count()
        course.save(update_fields=['lessons_count'])
        
        return Response({
            'success': True,
            'message': 'Dars o\'chirildi'
        })
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def update_progress(self, request, pk=None):
        """Update lesson progress for user"""
        course = self.get_object()
        user = request.user
        lesson_id = request.data.get('lesson_id')
        completed = request.data.get('completed', False)
        
        try:
            enrollment = Enrollment.objects.get(user=user, course=course)
        except Enrollment.DoesNotExist:
            return Response({'error': 'Kursga yozilmagansiz'}, status=status.HTTP_400_BAD_REQUEST)
        
        if completed:
            # Use LearningService to ensure consistent logic (XP, Certificate, etc.)
            LearningService.update_lesson_progress(user, lesson_id, 'VIDEO_COMPLETE')
            enrollment.refresh_from_db()
        
        return Response({
            'success': True,
            'progress': float(enrollment.progress),
            'completed': enrollment.completed_at is not None
        })



class LessonViewSet(viewsets.ModelViewSet):
    """
    Direct access to lessons (mostly for Admin)
    """
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ['retrieve', 'complete_video', 'submit_practice', 'submit_test']:
            return [IsAuthenticated(), HasCourseAccess()]
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsTeacherOrAdmin()]
        return [IsAuthenticated()]

    def get_queryset(self):
        # Admins see all, others see none unless through filtered access 
        # (Though LearningService handles the heavy lifting)
        if self.request.user.role == 'ADMIN':
            return Lesson.objects.all()
        return Lesson.objects.none()

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        user = request.user
        
        # Admin and Teacher (of this course) bypass lock
        if user.role == 'ADMIN' or (user.role == 'TEACHER' and instance.course.teacher == user):
             return super().retrieve(request, *args, **kwargs)
             
        # Guest/Student check
        state = LearningService.get_course_learning_state(user, instance.course_id)
        # Find this lesson in the flat list
        lesson_data = next((l for l in state['flat_lessons'] if l.id == instance.id), None)
        
        if lesson_data and getattr(lesson_data, 'is_locked', False):
            return Response({
                'error': 'Lesson is locked. Complete previous requirements first.',
                'required_lesson_id': lesson_data.required_lesson_id
            }, status=status.HTTP_403_FORBIDDEN)
            
        return super().retrieve(request, *args, **kwargs)

    def perform_create(self, serializer):
        lesson = serializer.save()
        # Trigger notification for enrolled students
        course = lesson.course
        from .services.notification_service import NotificationService
        from .models import Enrollment
        
        students = Enrollment.objects.filter(course=course).values_list('user', flat=True)
        for student_id in students:
            from .models import User
            user = User.objects.get(id=student_id)
            NotificationService.create_notification(
                user=user,
                title=f"Yangi dars: {lesson.title}",
                message=f"{course.title} kursiga yangi dars qo'shildi. Davom etishingiz mumkin!",
                notification_type='COURSE',
                link=f"/learning/{course.id}"
            )

    def perform_update(self, serializer):
        if self.request.user.role == 'TEACHER':
            # Teachers cannot change video source/admin fields
            for field in ['video_url', 'youtube_id', 'video_type', 'video_duration']:
                 if field in serializer.validated_data:
                     serializer.validated_data.pop(field)
        serializer.save()

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def complete_video(self, request, pk=None):
        position = request.data.get('position', 0)
        progress = LearningService.update_lesson_progress(
            request.user, pk, 'VIDEO_COMPLETE', {'position': position}
        )
        return Response(LessonProgressSerializer(progress).data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def submit_practice(self, request, pk=None):
        answer = request.data.get('answer', '')
        progress = LearningService.update_lesson_progress(
            request.user, pk, 'SUBMIT_PRACTICE', {'answer': answer}
        )
        return Response(LessonProgressSerializer(progress).data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def submit_test(self, request, pk=None):
        answers = request.data.get('answers', {})
        progress = LearningService.update_lesson_progress(
            request.user, pk, 'SUBMIT_TEST', {'answers': answers}
        )
        return Response(LessonProgressSerializer(progress).data)


class ModuleViewSet(viewsets.ModelViewSet):
    queryset = Module.objects.all()
    serializer_class = TeacherModuleSerializer
    permission_classes = [IsAuthenticated, IsTeacherOrAdmin]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'ADMIN':
            return Module.objects.all()
        return Module.objects.filter(course__teacher=user)

class LessonPracticeViewSet(viewsets.ModelViewSet):
    queryset = LessonPractice.objects.all()
    serializer_class = TeacherLessonPracticeSerializer
    permission_classes = [IsAuthenticated, HasCourseAccess]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'ADMIN':
            return LessonPractice.objects.all()
        return LessonPractice.objects.filter(lesson__course__teacher=user)

class LessonTestViewSet(viewsets.ModelViewSet):
    queryset = LessonTest.objects.all()
    serializer_class = TeacherLessonTestSerializer
    permission_classes = [IsAuthenticated, HasCourseAccess]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'ADMIN':
            return LessonTest.objects.all()
        return LessonTest.objects.filter(lesson__course__teacher=user)


# ============= OLYMPIAD VIEWS =============

class OlympiadPrizeViewSet(viewsets.ModelViewSet):
    queryset = OlympiadPrize.objects.all()
    serializer_class = OlympiadPrizeSerializer
    permission_classes = [IsAuthenticated, IsTeacherOrAdmin] 
    
    def get_queryset(self):
        user = self.request.user
        olympiad_id = self.request.query_params.get('olympiad_id')
        
        if user.role == 'ADMIN':
            qs = self.queryset
        else:
            # Teachers can only see prizes for their own olympiads
            qs = self.queryset.filter(olympiad__teacher=user)

        if olympiad_id:
            qs = qs.filter(olympiad_id=olympiad_id)
        return qs

    def perform_create(self, serializer):
        # Additional check to ensure teacher is creating prize for their own olympiad
        user = self.request.user
        if user.role != 'ADMIN':
            olympiad = serializer.validated_data.get('olympiad')
            if olympiad.teacher != user:
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied("You can only add prizes to your own olympiads.")
        serializer.save()

class WinnerPrizeViewSet(viewsets.ModelViewSet):
    """ViewSet for managing Olympiad winners and their prizes"""
    queryset = WinnerPrize.objects.all()
    serializer_class = WinnerPrizeSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['olympiad', 'student', 'status']
    ordering = ['position']

    def get_queryset(self):
        user = self.request.user
        if user.role == 'ADMIN':
            return WinnerPrize.objects.all()
        elif user.role == 'TEACHER':
            return WinnerPrize.objects.filter(olympiad__teacher=user)
        return WinnerPrize.objects.filter(student=user)

    def list(self, request, *args, **kwargs):
        """Override list to support ?limit=N parameter"""
        try:
            queryset = self.filter_queryset(self.get_queryset())
            limit = request.query_params.get('limit')
            if limit and limit.isdigit():
                queryset = queryset[:int(limit)]
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['POST'])
    def update_status(self, request, pk=None):
        """Admin/Teacher can update delivery status"""
        if request.user.role not in ['ADMIN', 'TEACHER']:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
            
        try:
            prize = self.get_object()
            new_status = request.data.get('status')
            if new_status in dict(WinnerPrize.STATUS_CHOICES):
                prize.status = new_status
                prize.save()
                
                # Notify user about status change if needed
                if prize.student.telegram_id:
                    status_texts = {
                        'SHIPPED': "🚚 Sizning sovriningiz yo'lga chiqdi!",
                        'COMPLETED': "✅ Sovrin yetkazib berildi. Tabriklaymiz!",
                        'CONTACTED': "📞 Admin sovrin bo'yicha siz bilan bog'lanadi."
                    }
                    if new_status in status_texts:
                        BotService.send_message(prize.student.telegram_id, status_texts[new_status])

                return Response({'success': True, 'status': prize.status})
            return Response({'success': False, 'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        


class OlympiadViewSet(viewsets.ModelViewSet):
    """
    Olympiad API endpoints
    """
    queryset = Olympiad.objects.filter(is_active=True)
    serializer_class = OlympiadSerializer
    permission_classes = [AllowAny]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['title', 'description', 'subject', 'subject_id__name']
    ordering_fields = ['start_date', 'created_at']
    ordering = ['-start_date']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return OlympiadDetailSerializer
        return OlympiadSerializer
    
    
    @action(detail=False, methods=['GET'], permission_classes=[IsAuthenticated, IsAdmin])
    def admin_stats(self, request):
        """Dashboard stats for Olympiad section"""
        from datetime import datetime
        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # 1. Status Stats
        status_counts = Olympiad.objects.values('status').annotate(count=Count('id'))
        stats_dict = {
            'ACTIVE': Olympiad.objects.filter(status='ONGOING').count(),
            'UPCOMING': Olympiad.objects.filter(status='UPCOMING').count(),
            'COMPLETED': Olympiad.objects.filter(status='COMPLETED').count(),
            'REGISTRATION_OPEN': Olympiad.objects.filter(status='REGISTRATION_OPEN').count(),
        }
        
        # 2. Revenue Stats
        total_revenue = Payment.objects.filter(
            type='OLYMPIAD', 
            status='COMPLETED'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        monthly_revenue = Payment.objects.filter(
            type='OLYMPIAD', 
            status='COMPLETED',
            created_at__gte=month_start
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # 3. Participation Stats
        total_participants = OlympiadRegistration.objects.count()
        avg_participants = Olympiad.objects.annotate(
            p_count=Count('registrations')
        ).aggregate(avg=Avg('p_count'))['avg'] or 0
        
        return Response({
            'success': True,
            'status_counts': stats_dict,
            'total_revenue': float(total_revenue),
            'monthly_revenue': float(monthly_revenue),
            'total_participants': total_participants,
            'avg_participants': round(float(avg_participants), 1)
        })

    @action(detail=True, methods=['GET'], permission_classes=[IsAuthenticated, IsTeacherOrAdmin])
    def stats(self, request, pk=None):
        """Detailed stats for an olympiad results page"""
        olympiad = self.get_object()
        
        total_registrations = olympiad.registrations.count()
        results = TestResult.objects.filter(olympiad=olympiad)
        total_submissions = results.count()
        total_paid = olympiad.registrations.filter(is_paid=True).count()
        total_disqualified = results.filter(status='DISQUALIFIED').count()
        
        avg_score = results.aggregate(Avg('score'))['score__avg'] or 0
        max_score = results.aggregate(Max('score'))['score__max'] or 0
        
        # Region breakdown
        from django.db.models import Count
        region_breakdown = olympiad.registrations.values('user__region').annotate(count=Count('id')).order_by('-count')
        
        return Response({
            'success': True,
            'stats': {
                'total_registrations': total_registrations,
                'total_submissions': total_submissions,
                'total_paid': total_paid,
                'total_disqualified': total_disqualified,
                'avg_score': round(float(avg_score), 1),
                'max_score': max_score,
                'region_breakdown': [{'region': item['user__region'], 'count': item['count']} for item in region_breakdown]
            }
        })

    @action(detail=True, methods=['GET'], permission_classes=[IsAuthenticated, IsTeacherOrAdmin])
    def live_stats(self, request, pk=None):
        """Live stats for an ongoing olympiad"""
        olympiad = self.get_object()
        now = timezone.now()
        
        # Online users = users who updated their result in the last 5 minutes
        online_count = TestResult.objects.filter(
            olympiad=olympiad,
            # We assume updating results frequently or check updated_at
            # Since TestResult doesn't have updated_at in snippet, checking submitted_at might be wrong
            # Let's check for 'COMPLETED' or if there's an ongoing signal
        ).count() # Placeholder count
        
        # Score distribution
        distribution = {
            '0-20%': TestResult.objects.filter(olympiad=olympiad, percentage__lt=20).count(),
            '20-50%': TestResult.objects.filter(olympiad=olympiad, percentage__gte=20, percentage__lt=50).count(),
            '50-80%': TestResult.objects.filter(olympiad=olympiad, percentage__gte=50, percentage__lt=80).count(),
            '80-100%': TestResult.objects.filter(olympiad=olympiad, percentage__gte=80).count(),
        }
        
        return Response({
            'success': True,
            'online_participants': online_count, # Mock for now
            'submissions': distribution,
            'revenue': float(Payment.objects.filter(type='OLYMPIAD', reference_id=str(olympiad.id), status='COMPLETED').aggregate(Sum('amount'))['amount__sum'] or 0)
        })

    @action(detail=True, methods=['POST'], permission_classes=[IsAuthenticated, IsAdmin])
    def distribute_rewards(self, request, pk=None):
        """Trigger automated reward distribution for this olympiad"""
        olympiad = self.get_object()
        
        # Check if olympiad is published or completed
        if olympiad.status not in ['PUBLISHED', 'CHECKING', 'COMPLETED']:
             return Response({
                'success': False,
                'error': 'Sovrinlarni tarqatish uchun olimpiada natijalari tekshirilgan yoki e\'lon qilingan bo\'lishi kerak'
            }, status=status.HTTP_400_BAD_REQUEST)

        success = RewardService.distribute_rewards(olympiad.id)
        if success:
            return Response({'success': True, 'message': 'Sovrinlar muvaffaqiyatli tarqatildi!'})
        else:
            return Response({'success': False, 'error': 'Sovrinlarni tarqatishda xatolik yuz berdi'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['GET'])
    def winners(self, request, pk=None):
        """Get list of winners and their prizes for this olympiad"""
        olympiad = self.get_object()
        winners = WinnerPrize.objects.filter(olympiad=olympiad).select_related('student', 'prize_item')
        serializer = WinnerPrizeSerializer(winners, many=True)
        return Response({
            'success': True,
            'winners': serializer.data
        })
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'add_question', 'import_questions', 'submissions', 'grade_result']:
            return [IsAuthenticated(), IsTeacherOrAdmin()]
        return [AllowAny()]

    def perform_create(self, serializer):
        user = self.request.user
        creation_fee_paid = False
        
        if user.role == 'TEACHER':
            profile = getattr(user, 'teacher_profile', None)
            if profile:
                if getattr(profile, 'teacher_type', None) == 'INTERNAL' or getattr(profile, 'is_vip', False):
                    creation_fee_paid = True
            
            # If admin assigned a teacher, keep it. Otherwise default to current user.
            assigned_teacher = serializer.validated_data.get('teacher', user)
            
            # Teachers must be moderated
            olympiad = serializer.save(
                teacher=assigned_teacher, 
                creation_fee_paid=creation_fee_paid,
                status='PENDING'
            )

            # Notify Admins
            admins = User.objects.filter(role='ADMIN', is_active=True)
            admin_title = "Yangi olimpiada (Moderatsiya)"
            admin_msg = f"O'qituvchi {user.username} yangi olimpiada yaratdi: {olympiad.title}. Iltimos, ko'rib chiqing va tasdiqlang."
            
            for admin in admins:
                NotificationService.create_notification(
                    user=admin,
                    title=admin_title,
                    message=admin_msg,
                    notification_type='OLYMPIAD',
                    channel='ALL'
                )
            
            # Direct Telegram to system admin channel/group if configured
            config = BotConfig.objects.filter(is_active=True).first()
            if config and config.admin_chat_id:
                tg_msg = f"🆕 <b>Yangi olimpiada (Moderatsiya)</b>\n\n👤 O'qituvchi: {user.username}\n🏆 Olimpiada: {olympiad.title}\n\nTasdiqlash kutilmoqda."
                BotService.send_to_admin(tg_msg)
        else:
            # For Admins, if teacher is in data, use it.
            assigned_teacher = serializer.validated_data.get('teacher', None)
            serializer.save(teacher=assigned_teacher, creation_fee_paid=True, status='APPROVED')
    
    @action(detail=True, methods=['POST'], permission_classes=[IsAuthenticated, IsAdmin])
    def force_start(self, request, pk=None):
        """
        Admin action to immediately start the olympiad.
        Updates start_date to now and status to ONGOING.
        """
        try:
            olympiad = self.get_object()
            olympiad.status = 'ONGOING'
            olympiad.start_date = timezone.now()
            olympiad.is_active = True
            olympiad.save()
            
            # Notify participants
            from api.services.olympiad_service import OlympiadService
            notify_count = OlympiadService.notify_participants_olympiad_start(olympiad)
            
            return Response({
                'success': True, 
                'message': f'Olimpiada boshlandi! {notify_count} ta foydalanuvchiga xabar yuborildi.'
            })
        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def register(self, request, pk=None):
        """Register for an olympiad"""
        olympiad = self.get_object()
        user = request.user
        
        # Check status
        if olympiad.status == 'COMPLETED':
            return Response({
                'success': False,
                'error': 'Olimpiada tugagan'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if already registered
        if OlympiadRegistration.objects.filter(user=user, olympiad=olympiad).exists():
            return Response({
                'success': False,
                'error': 'Siz allaqachon ro\'yxatdan o\'tgansiz'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check max participants
        if olympiad.max_participants:
            current_count = olympiad.registrations.count()
            if current_count >= olympiad.max_participants:
                return Response({
                    'success': False,
                    'error': 'Ishtirokchilar soni chegaraga yetdi'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check payment
        is_paid = True
        if olympiad.price > 0:
            payment_exists = Payment.objects.filter(
                user=user,
                type='OLYMPIAD',
                reference_id=str(olympiad.id),
                status='COMPLETED'
            ).exists()
            
            if not payment_exists:
                return Response({
                    'success': False,
                    'error': 'To\'lov amalga oshirilmagan',
                    'requires_payment': True,
                    'price': float(olympiad.price)
                }, status=status.HTTP_402_PAYMENT_REQUIRED)
        
        registration = OlympiadRegistration.objects.create(
            user=user,
            olympiad=olympiad,
            is_paid=is_paid
        )
        
        return Response({
            'success': True,
            'message': 'Ro\'yxatdan muvaffaqiyatli o\'tdingiz',
            'registration': OlympiadRegistrationSerializer(registration).data
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def questions(self, request, pk=None):
        """Get olympiad questions for test"""
        olympiad = self.get_object()
        user = request.user
        
        # Check registration
        if not OlympiadRegistration.objects.filter(user=user, olympiad=olympiad).exists():
            return Response({
                'success': False,
                'error': 'error.not_registered'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Check if already submitted
        attempt = TestResult.objects.filter(user=user, olympiad=olympiad).first()
        if attempt and attempt.status == 'COMPLETED' and olympiad.max_attempts <= 1:
            return Response({
                'success': False,
                'error': 'error.already_submitted'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check olympiad timing (skip if status is ONGOING - admin started manually)
        now = timezone.now()
        if olympiad.status != 'ONGOING':
            if now < olympiad.start_date:
                return Response({
                    'success': False,
                    'error': 'error.not_started',
                    'starts_at': olympiad.start_date
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if olympiad.end_date and now > olympiad.end_date:
                return Response({
                    'success': False,
                    'error': 'error.finished'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        questions = olympiad.questions.all()
        if olympiad.is_random:
            questions = questions.order_by('?')
        else:
            questions = questions.order_by('order')

        return Response({
            'success': True,
            'questions': QuestionSerializer(questions, many=True).data,
            'duration': olympiad.duration,
            'olympiad': {
                'id': olympiad.id,
                'title': olympiad.title,
                'duration': olympiad.duration,
                'start_date': olympiad.start_date,
                'end_date': olympiad.end_date,
                'status': olympiad.status,
                'tab_switch_limit': olympiad.tab_switch_limit,
                'required_full_screen': olympiad.required_full_screen,
                'disable_copy_paste': olympiad.disable_copy_paste,
                'cannot_go_back': olympiad.cannot_go_back,
                'max_attempts': olympiad.max_attempts,
            }
        })

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_registrations(self, request):
        """List olympiads the user has registered for"""
        registrations = OlympiadRegistration.objects.filter(user=self.request.user).select_related('olympiad')
        
        data = []
        for reg in registrations:
            # Manually construct response to match frontend expectation
            data.append({
                'id': reg.id,
                'olympiad': OlympiadSerializer(reg.olympiad, context={'request': request}).data,
                'registered_at': reg.registered_at,
                'status': reg.olympiad.status
            })
            
        return Response({'success': True, 'registrations': data})


    
    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated, IsTeacherOrAdmin])
    def get_questions(self, request, pk=None):
        """Get all questions for admin/teacher management"""
        olympiad = self.get_object()
        questions = olympiad.questions.all().order_by('order')
        return Response(QuestionAdminSerializer(questions, many=True).data)

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated, IsTeacherOrAdmin])
    def ranking(self, request, pk=None):
        """Get the leaderboard for an olympiad"""
        olympiad = self.get_object()
        
        # Ranking logic: score DESC, then time_taken ASC
        results = TestResult.objects.filter(olympiad=olympiad, status='COMPLETED')\
            .order_by('-score', 'time_taken', 'submitted_at')
        
        data = []
        for i, res in enumerate(results):
            data.append({
                'rank': i + 1,
                'user_id': res.user.id,
                'full_name': res.user.get_full_name() or res.user.username,
                'phone': res.user.phone,
                'score': res.score,
                'percentage': res.percentage,
                'time_taken': res.time_taken,
                'submitted_at': res.submitted_at
            })
            
        return Response({'success': True, 'ranking': data})

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsTeacherOrAdmin])
    def confirm_winners(self, request, pk=None):
        """Confirm winners and notify via Telegram"""
        olympiad = self.get_object()
        winners_data = request.data.get('winners', []) # List of {user_id, position, prize_id}
        
        if not winners_data:
            return Response({'success': False, 'error': 'G\'oliblar ro\'yxati bo\'sh'}, status=status.HTTP_400_BAD_REQUEST)
            
        notifications_sent = 0
        for win in winners_data:
            user_id = win.get('user_id')
            position = win.get('position')
            prize_id = win.get('prize_id')
            
            user = get_object_or_404(User, id=user_id)
            prize_item = None
            if prize_id:
                prize_item = get_object_or_404(OlympiadPrize, id=prize_id)
                
            winner_prize, created = WinnerPrize.objects.update_or_create(
                olympiad=olympiad,
                student=user,
                defaults={
                    'position': position,
                    'prize_item': prize_item,
                    'status': 'PENDING'
                }
            )
            
            # Send notification
            if BotService.notify_winner(winner_prize):
                winner_prize.status = 'CONTACTED'
                winner_prize.save()
                notifications_sent += 1
            
        return Response({
            'success': True, 
            'message': f'{len(winners_data)} ta g\'olib tasdiqlandi. {notifications_sent} tasiga Telegram orqali xabar yuborildi.'
        })

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def submit(self, request, pk=None):
        """Submit test answers with anti-cheat validation"""
        olympiad = self.get_object()
        user = request.user
        
        serializer = TestSubmitSerializer(data=request.data)
        if not serializer.is_valid():
            print(f"DEBUG: Submit Serializer Errors: {serializer.errors}")
            print(f"DEBUG: Request Data: {request.data}")
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        answers = serializer.validated_data['answers']
        time_taken = serializer.validated_data['time_taken']
        tab_switches = serializer.validated_data.get('tab_switches', 0)
        
        # Check existing result
        result = TestResult.objects.filter(user=user, olympiad=olympiad).first()
        
        if result and result.status == 'COMPLETED' and olympiad.max_attempts <= 1:
            return Response({
                'success': False,
                'error': 'error.already_submitted'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Anti-Cheat Validation
        status_result = 'COMPLETED'
        if olympiad.tab_switch_limit > 0 and tab_switches > olympiad.tab_switch_limit:
            status_result = 'DISQUALIFIED'
        
        # Calculate score
        all_questions = {q.id: q for q in olympiad.questions.all()}
        score = 0
        
        for q_id_str, user_ans in answers.items():
            try:
                q_id = int(q_id_str)
                if q_id in all_questions:
                    q = all_questions[q_id]
                    # Comparison logic
                    if str(user_ans).strip() == str(q.correct_answer).strip():
                        score += q.points
            except (ValueError, TypeError):
                continue
                
        # Calculate percentage
        total_points = sum(q.points for q in all_questions.values())
        percentage = round((score / total_points * 100), 2) if total_points > 0 else 0
        
        # Update or Save result
        if result:
            result.answers = answers
            result.score = score
            result.percentage = percentage
            result.time_taken = time_taken
            result.tab_switches_count = tab_switches
            result.status = status_result
            result.save()
        else:
            result = TestResult.objects.create(
                user=user,
                olympiad=olympiad,
                answers=answers,
                score=score,
                percentage=percentage,
                time_taken=time_taken,
                tab_switches_count=tab_switches,
                status=status_result
            )
        
        # Award XP (only if not disqualified and logic permits)
        if status_result == 'COMPLETED':
            xp_gained = int(score * 2) # Base XP for questions
            if percentage >= 70: # Bonus for good result
                xp_gained += 20
            
            user.add_xp(xp_gained, 'TEST_COMPLETE', f"Test yakunlandi")
            
        # Notify via Bot
        try:
            BotService.notify_result(user, result)
        except Exception as e:
            print(f"Result notification error: {e}")
        
        return Response({
            'success': True,
            'message': 'success.submitted' if status_result == 'COMPLETED' else 'error.disqualified',
            'result': TestResultSerializer(result).data
        }, status=status.HTTP_200_OK if result.pk else status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def result(self, request, pk=None):
        """Get user's result for this olympiad including global leaderboard"""
        olympiad = self.get_object()
        user = request.user
        
        # 1. Base Stats (Global)
        completed_results = TestResult.objects.filter(
            olympiad=olympiad,
            status='COMPLETED'
        ).select_related('user')
        
        avg_score = completed_results.aggregate(models.Avg('score'))['score__avg'] or 0
        participants_count = TestResult.objects.filter(olympiad=olympiad).count()
        
        # 2. Personal Result
        my_result_full = None
        try:
            my_res = TestResult.objects.get(user=user, olympiad=olympiad)
            my_result_full = TestResultSerializer(my_res).data
            # Calculate Rank
            my_result_full['rank'] = completed_results.filter(
                models.Q(score__gt=my_res.score) | 
                models.Q(score=my_res.score, time_taken__lt=my_res.time_taken)
            ).count() + 1
        except TestResult.DoesNotExist:
            pass

        # 3. Result Time Logic
        now = timezone.now()
        is_results_open = True
        if olympiad.result_time and now < olympiad.result_time:
            is_results_open = False
        
        if not is_results_open:
            return Response({
                'success': True,
                'status': 'WAITING_RESULTS',
                'result_time': olympiad.result_time,
                'message': 'Natijalar tez orada e\'lon qilinadi',
                'my_result': my_result_full,
                'avg_score': round(float(avg_score), 1),
                'participants_count': participants_count
            })
            
        # 4. Leaderboard Data (Top 5 for preview)
        leaderboard_data = []
        if is_results_open:
            total_points = sum(q.points for q in olympiad.questions.all())
            qs = completed_results.order_by('-score', 'time_taken')[:5]
            for idx, res in enumerate(qs):
                name = res.user.get_full_name().strip() or res.user.username
                leaderboard_data.append({
                    'rank': idx + 1,
                    'student': name,
                    'score': res.score,
                    'max_score': total_points,
                    'time_taken': res.time_taken,
                    'region': res.user.region or "",
                    'avatar': res.user.avatar.url if res.user.avatar else None
                })

        return Response({
            'success': True,
            'status': 'RESULTS_OPEN',
            'my_result': my_result_full,
            'leaderboard': leaderboard_data,
            'avg_score': round(float(avg_score), 1),
            'participants_count': participants_count
        })

    @action(detail=True, methods=['get'], permission_classes=[AllowAny])
    def leaderboard(self, request, pk=None):
        """Get leaderboard for olympiad"""
        olympiad = self.get_object()
        
        is_staff = request.user.is_authenticated and (request.user.role in ['ADMIN', 'TEACHER'])
        is_published = olympiad.status == 'PUBLISHED'
        
        completed_results = TestResult.objects.filter(
            olympiad=olympiad,
            status='COMPLETED'
        ).select_related('user')
        
        # Calculate some stats
        avg_score = completed_results.aggregate(models.Avg('score'))['score__avg'] or 0
        participants_count = TestResult.objects.filter(olympiad=olympiad).count()
        best_time = completed_results.aggregate(models.Min('time_taken'))['time_taken__min'] or 0
        regions_count = completed_results.values('user__region').distinct().count()

        # Get current user's rank and result
        my_result_data = None
        if request.user.is_authenticated:
            my_res = completed_results.filter(user=request.user).first()
            if my_res:
                # Rank logic (Score DESC, Time ASC)
                my_rank = completed_results.filter(
                    models.Q(score__gt=my_res.score) | 
                    models.Q(score=my_res.score, time_taken__lt=my_res.time_taken)
                ).count() + 1
                my_result_data = {
                    'rank': my_rank,
                    'score': my_res.score,
                    'time_taken': my_res.time_taken,
                    'percentage': float(my_res.percentage or 0)
                }

        # Check result time for leaderboard visibility
        now = timezone.now()
        is_results_open = is_published
        if olympiad.result_time and now < olympiad.result_time:
            is_results_open = False
            
        # Calculate Max Score
        total_points = sum(q.points for q in olympiad.questions.all())

        leaderboard_data = []
        # Queryset Logic
        if is_staff:
            qs = TestResult.objects.filter(olympiad=olympiad).select_related('user').order_by('-score', 'time_taken')
        else:
            if is_results_open:
                qs = completed_results.order_by('-score', 'time_taken')[:100]
            else:
                qs = []

        if qs:
            for idx, res in enumerate(qs):
                # Name Logic
                name = res.user.get_full_name().strip()
                if not name:
                    name = res.user.username
                
                # Format Time
                mins, secs = divmod(res.time_taken, 60)
                time_str = f"{mins:02}:{secs:02}"
                    
                # Winner Prize Info
                prize_info = WinnerPrize.objects.filter(olympiad=olympiad, student=res.user).first()
                prize_status = prize_info.status if prize_info else None
                prize_item = prize_info.prize_item.name if prize_info and prize_info.prize_item else None
                    
                leaderboard_data.append({
                    'id': res.user.id,
                    'rank': idx + 1,
                    'student': name, # For Public Leaderboard compat
                    'name': name,    # For Admin Participants Page
                    'score': res.score,
                    'max_score': total_points,
                    'time_taken': res.time_taken,
                    'time': time_str,
                    'region': res.user.region or "",
                    'status': res.status,
                    'avatar': res.user.avatar.url if res.user.avatar else None,
                    'prize_status': prize_status,
                    'prize_item': prize_item
                })

        return Response({
            'success': True,
            'status': 'WAITING_RESULTS' if is_published and not is_results_open else olympiad.status,
            'title': olympiad.title,
            'subject': olympiad.subject,
            'date': olympiad.start_date,
            'avg_score': round(float(avg_score or 0), 1),
            'participants_count': participants_count,
            'best_time': best_time,
            'regions_count': regions_count,
            'my_result': my_result_data,
            'leaderboard': leaderboard_data,
            'participant_count': participants_count, # Alias
            'participants': leaderboard_data,
            'result_time': olympiad.result_time 
        })

    @action(detail=True, methods=['get'], url_path=r'result_detail/(?P<user_id>\d+)', permission_classes=[IsAuthenticated, IsTeacherOrAdmin])
    def result_detail(self, request, pk=None, user_id=None):
        """Get detailed result analysis for a specific user"""
        olympiad = self.get_object()
        try:
            result = TestResult.objects.get(olympiad=olympiad, user_id=user_id)
        except TestResult.DoesNotExist:
            return Response({'error': 'Result not found'}, status=404)
        
        questions = olympiad.questions.all()
        q_data = []
        
        for q in questions:
            user_ans = result.answers.get(str(q.id))
            is_correct = False
            status = 'SKIPPED'
            
            if user_ans is not None:
                # Basic correctness check (should match grading logic)
                status = 'INCORRECT'
                if q.type == 'MCQ':
                    if str(user_ans) == str(q.correct_answer):
                        is_correct = True
                        status = 'CORRECT'
                elif q.type == 'NUMERIC':
                    if str(user_ans).strip() == str(q.correct_answer).strip():
                        is_correct = True
                        status = 'CORRECT'
                elif q.type == 'TEXT':
                    # Manual grading usually needed, but for now exact match or INCORRECT
                    if str(user_ans).strip().lower() == str(q.correct_answer).strip().lower():
                        is_correct = True
                        status = 'CORRECT'
            
            q_data.append({
                'id': q.id,
                'text': q.text,
                'type': q.type,
                # 'options': q.options, # Maybe too heavy? Frontend should render. But useful for context.
                'points': q.points,
                'user_answer': user_ans,
                'correct_answer': q.correct_answer,
                'status': status,
                'is_correct': is_correct,
                'explanation': q.explanation
            })
            
        return Response({
            'success': True,
            'user': {
                'id': result.user.id,
                'name': result.user.get_full_name() or result.user.username,
                'avatar': result.user.avatar.url if result.user.avatar else None
            },
            'stats': {
                'score': result.score,
                'max_score': sum(q.points for q in questions),
                'participants_avg': 0, # Placeholder
                'time_taken': result.time_taken,
                'tab_switches': result.tab_switches_count,
                'ip': result.ip_address,
                'device': result.device_info,
                'submitted_at': result.submitted_at
            },
            'questions': q_data
        })

    @action(detail=True, methods=['get'])
    def submissions(self, request, pk=None):
        """List all submissions for teacher/admin"""
        olympiad = self.get_object()
        results = TestResult.objects.filter(olympiad=olympiad).select_related('user').order_by('-submitted_at')
        
        data = []
        for res in results:
            name = res.user.get_full_name().strip() or res.user.username
            data.append({
                'id': res.id,
                'user_id': res.user.id,
                'student': name,
                'score': res.score,
                'percentage': float(res.percentage),
                'time_taken': res.time_taken,
                'status': res.status,
                'submitted_at': res.submitted_at,
                'region': res.user.region,
                'answers': res.answers,
                'feedback': res.feedback
            })
        
        return Response({
            'success': True,
            'results': data
        })

    @action(detail=True, methods=['post'])
    def grade_result(self, request, pk=None):
        """Override student grade (Teacher/Admin only)"""
        olympiad = self.get_object()
        user_id = request.data.get('user_id')
        new_score = request.data.get('score')
        comment = request.data.get('comment', '')
        
        try:
            result = TestResult.objects.get(olympiad=olympiad, user_id=user_id)
            if new_score is not None:
                result.score = int(new_score)
                # Recalculate percentage based on total points
                total_points = sum(q.points for q in olympiad.questions.all())
                if total_points > 0:
                    result.percentage = round((result.score / total_points) * 100, 2)
                
            if comment:
                result.feedback = comment
                
            result.save()
            return Response({'success': True, 'message': 'Natija yangilandi'})
        except TestResult.DoesNotExist:
            return Response({'success': False, 'error': 'Natija topilmadi'}, status=404)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsTeacherOrAdmin])
    def publish_results(self, request, pk=None):
        """Finalize results and publish leaderboard"""
        olympiad = self.get_object()
        olympiad.status = 'PUBLISHED'
        olympiad.save()
        
        # Issue certificates for qualified students (>70%)
        certs_count = CertificateService.issue_olympiad_certificates(olympiad.id)
        
        return Response({
            'success': True, 
            'message': f'Natijalar e\'lon qilindi va {certs_count} ta sertifikat yaratildi'
        })

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsTeacherOrAdmin])
    def disqualify(self, request, pk=None):
        """Disqualify a student"""
        olympiad = self.get_object()
        user_id = request.data.get('user_id')
        reason = request.data.get('reason', 'Qoidabuzarlik aniqlandi')
        
        try:
            result = TestResult.objects.get(olympiad=olympiad, user_id=user_id)
            result.status = 'DISQUALIFIED'
            result.disqualified_reason = reason
            result.save()
            return Response({'success': True, 'message': 'Talaba diskvalifikatsiya qilindi'})
        except TestResult.DoesNotExist:
            return Response({'success': False, 'error': 'Natija topilmadi'}, status=404)

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated, IsTeacherOrAdmin])
    def stats(self, request, pk=None):
        """Get detailed KPIs for admin"""
        olympiad = self.get_object()
        registrations = olympiad.registrations.all()
        results = olympiad.results.all()
        
        # Calculations
        reg_count = registrations.count()
        submission_count = results.filter(status='COMPLETED').count()
        paying_count = registrations.filter(is_paid=True).count()
        disqualified_count = results.filter(status='DISQUALIFIED').count()
        
        avg_score = results.filter(status='COMPLETED').aggregate(models.Avg('score'))['score__avg'] or 0
        max_score = results.filter(status='COMPLETED').aggregate(models.Max('score'))['score__max'] or 0
        
        # Region breakdown
        regions = User.objects.filter(olympiad_registrations__olympiad=olympiad).values('region').annotate(count=models.Count('id')).order_by('-count')
        
        return Response({
            'success': True,
            'stats': {
                'total_registrations': reg_count,
                'total_submissions': submission_count,
                'total_paid': paying_count,
                'total_disqualified': disqualified_count,
                'avg_score': round(avg_score, 1),
                'max_score': max_score,
                'region_breakdown': list(regions)
            }
        })



    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def start(self, request, pk=None):
        """Start the olympiad test"""
        try:
            attempt = OlympiadService.start_test(request.user, pk)
            serializer = TestResultSerializer(attempt)
            return Response({
                'success': True,
                'attempt': serializer.data
            })
        except ValidationError as e:
             return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
             
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def submit_answer(self, request, pk=None):
        """Submit a single answer"""
        question_id = request.data.get('question_id')
        answer = request.data.get('answer')
        
        if not question_id or answer is None:
             return Response({'error': 'question_id and answer required'}, status=status.HTTP_400_BAD_REQUEST)
             
        try:
            attempt = OlympiadService.submit_answer(request.user, pk, question_id, answer)
            return Response({'success': True})
        except ValidationError as e:
             return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def finish(self, request, pk=None):
        """Finish the test"""
        try:
            olympiad = self.get_object()
            attempt = OlympiadService.finish_test(request.user, pk)
            
            # Check result time
            now = timezone.now()
            if olympiad.result_time and now < olympiad.result_time:
                return Response({
                    'success': True,
                    'status': 'WAITING_RESULTS',
                    'result_time': olympiad.result_time,
                    'message': 'Test yakunlandi. Natijalar kutilmoqda.'
                })

            serializer = TestResultSerializer(attempt)
            return Response({
                'success': True,
                'status': 'COMPLETED',
                'result': serializer.data
            })
        except Exception as e:
             return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)



    @action(detail=False, methods=['get'])
    def results_with_winners(self, request):
        """Get olympiads with top 3 winners for carousel"""
        # Get active or completed olympiads
        olympiads = self.get_queryset().filter(status__in=['COMPLETED', 'ACTIVE']).order_by('-start_date')[:10]
        data = []
        
        for olym in olympiads:
            # Get top 3 winners
            results = olym.results.all().select_related('user').order_by('-score', 'time_taken')[:3]
            
            winners_data = []
            for idx, res in enumerate(results):
                winners_data.append({
                    'id': res.id,
                    'rank': idx + 1,
                    'student_name': f"{res.user.first_name} {res.user.last_name}",
                    'region': res.user.region,
                    'score': res.score,
                    'max_score': 100 # Assuming max is 100 or calculate from questions
                })
            
            data.append({
                'id': olym.id,
                'title': olym.title,
                'subject': olym.subject,
                'date': olym.start_date.isoformat(),
                'stage': 'Respublika' if 'Respublika' in olym.title else 'Viloyat',
                'participants_count': olym.registrations.count(),
                'winners': winners_data
            })
            
        return Response(data)
    
    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def results(self, request, pk=None):
        """Get test results"""
        olympiad = self.get_object()
        try:
            result = TestResult.objects.get(user=request.user, olympiad=olympiad)
            return Response({
                'success': True,
                'my_result': TestResultSerializer(result).data
            })
        except TestResult.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Natijalar topilmadi'
            }, status=status.HTTP_404_NOT_FOUND)
    
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def add_question(self, request, pk=None):
        """Add question to olympiad (Admin only)"""
        if request.user.role != 'ADMIN':
            return Response({'error': 'Admin huquqi talab qilinadi'}, status=status.HTTP_403_FORBIDDEN)
        
        olympiad = self.get_object()
        serializer = QuestionAdminSerializer(data=request.data)
        if serializer.is_valid():
            question = serializer.save(olympiad=olympiad)
            return Response({
                'success': True,
                'message': 'Savol qo\'shildi',
                'question': QuestionAdminSerializer(question).data
            }, status=status.HTTP_201_CREATED)
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_results(self, request):
        """Get user's test results"""
        results = TestResult.objects.filter(user=request.user).select_related('olympiad').order_by('-submitted_at')
        return Response({
            'success': True,
            'results': TestResultSerializer(results, many=True).data
        })
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_registrations(self, request):
        """Get user's olympiad registrations"""
        registrations = OlympiadRegistration.objects.filter(user=request.user).select_related('olympiad')
        return Response({
            'success': True,
            'registrations': OlympiadRegistrationSerializer(registrations, many=True).data
        })

    @action(detail=True, methods=['post'], parser_classes=[MultiPartParser, FormParser], permission_classes=[IsAuthenticated, IsTeacherOrAdmin])
    def import_questions(self, request, pk=None):
        """Import questions from Excel/CSV/Word"""
        olympiad = self.get_object()
        
        if 'file' not in request.FILES:
            return Response({'error': 'File not provided'}, status=400)
            
        file = request.FILES['file']
        ext = os.path.splitext(file.name)[1].lower()
        
        created_count = 0
        
        try:
            questions_data = []
            
            # --- IMPORT LOGIC START ---
            if ext in ['.xlsx', '.xls', '.csv']:
                # Read via Pandas
                if ext == '.csv':
                    df = pd.read_csv(file)
                else:
                    df = pd.read_excel(file)
                
                # Expected columns: text, type, options, correct_answer, points, time_limit, explanation
                # Map simple columns to standard names if needed
                df.columns = [str(c).lower().strip() for c in df.columns]
                
                for _, row in df.iterrows():
                    # Safely get values
                    text = str(row.get('text', '') or row.get('savol', '')).strip()
                    if not text: continue
                    
                    q_type = str(row.get('type', 'MCQ')).upper()
                    if q_type not in ['MCQ', 'TEXT', 'NUMERIC', 'CODE']: q_type = 'MCQ'
                    
                    # Options (comma separated or JSON)
                    options_raw = row.get('options', '') or row.get('variantlar', '')
                    options = []
                    if options_raw and pd.notna(options_raw):
                        raw_str = str(options_raw)
                        options = raw_str.split('|') if '|' in raw_str else raw_str.split(',')
                        options = [o.strip() for o in options if o.strip()]
                    
                    # Ensure minimal options for MCQ if empty in 'options' column
                    if q_type == 'MCQ' and len(options) < 2:
                        # Fallback: maybe A, B, C columns exist?
                        opts = []
                        for char in ['a', 'b', 'c', 'd']:
                            val = row.get(char, '')
                            if val and pd.notna(val): opts.append(str(val))
                        if opts: options = opts
                    
                    correct = str(row.get('correct_answer', '') or row.get('javob', '0')).strip()
                    points = int(row.get('points', 1)) if pd.notna(row.get('points', 1)) else 1

                    # Fix MCQ Answer (Convert Text/A/B to Index)
                    if q_type == 'MCQ' and options:
                        # 1. Check if it's A/B/C/D
                        if len(correct) == 1 and correct.upper() in ['A', 'B', 'C', 'D', 'E']:
                            idx = ord(correct.upper()) - ord('A')
                            if idx < len(options):
                                correct = str(idx)
                        
                        # 2. Check if it matches an Option Text perfectly
                        elif correct in options:
                            correct = str(options.index(correct))
                        
                        # 3. Check if it matches Option Text (case insensitive)
                        else:
                            for idx, opt in enumerate(options):
                                if opt.lower().strip() == correct.lower().strip():
                                    correct = str(idx)
                                    break

                    questions_data.append({
                        'text': text,
                        'type': q_type,
                        'options': options,
                        'correct_answer': correct,
                        'points': points,
                        'explanation': str(row.get('explanation', '')) if pd.notna(row.get('explanation', '')) else '',
                        'time_limit': int(row.get('time_limit', 0)) if pd.notna(row.get('time_limit', 0)) else 0
                    })

            elif ext == '.docx':
                # Basic Word Parser
                from docx import Document
                doc = Document(file)
                
                current_q = None
                
                for para in doc.paragraphs:
                    line = para.text.strip()
                    if not line: continue
                    
                    # Detect New Question (Starts with Digit + Dot)
                    # Heuristic parsing
                    is_new_q = False
                    if len(line) > 2 and line[0].isdigit():
                        # Check if dots/parenthesis follow
                        idx = 0
                        while idx < len(line) and line[idx].isdigit(): idx += 1
                        if idx < len(line) and line[idx] in ['.', ')']:
                            is_new_q = True
                    
                    if is_new_q:
                        # Save previous
                        if current_q: questions_data.append(current_q)
                        
                        # Start new
                        clean_text = line.split('.', 1)[-1].strip() if '.' in line else line
                        clean_text = clean_text.split(')', 1)[-1].strip() if ')' in clean_text[:5] else clean_text
                        
                        current_q = {
                            'text': clean_text,
                            'type': 'MCQ',
                            'options': [],
                            'correct_answer': '',
                            'points': 1,
                            'explanation': '',
                            'time_limit': 0
                        }
                    
                    elif current_q:
                        # Parse Options (A), a), etc.)
                        first_word = line.split(' ')[0].replace('.', '').replace(')', '').upper()
                        if len(first_word) == 1 and first_word in ['A', 'B', 'C', 'D', 'E']:
                            opt_text = line[len(first_word)+1:].strip().replace(')', '', 1).replace('.', '', 1).strip()
                            current_q['options'].append(opt_text)
                        
                        # Parse Answer
                        elif line.lower().startswith('javob:') or line.lower().startswith('answer:'):
                            ans = line.split(':', 1)[1].strip().upper()
                            # If answer is 'A', convert to index 0
                            if ans in ['A', 'B', 'C', 'D']:
                                current_q['correct_answer'] = str(ord(ans) - ord('A'))
                            else:
                                current_q['correct_answer'] = ans
                
                # Append last
                if current_q: questions_data.append(current_q)

            else:
                 return Response({'error': 'Unsupported file format. Use .xlsx, .csv or .docx'}, status=400)

            # --- SAVE TO DB ---
            current_order = olympiad.questions.count() + 1
            
            for q in questions_data:
                Question.objects.create(
                    olympiad=olympiad,
                    text=q['text'],
                    type=q.get('type', 'MCQ'),
                    options=q.get('options', []),
                    correct_answer=str(q.get('correct_answer', '')),
                    points=q.get('points', 1),
                    explanation=q.get('explanation', ''),
                    time_limit=q.get('time_limit', 0),
                    order=current_order
                )
                current_order += 1
            
            created_count = len(questions_data)
            
        except Exception as e:
            print(f"Import Error: {e}")
            return Response({'error': f"Import failed: {str(e)}"}, status=400)

        return Response({
            'success': True,
            'message': f"{created_count} ta savol yuklandi",
            'count': created_count
        })


# ============= CERTIFICATE VIEWS =============

class CertificateViewSet(viewsets.ModelViewSet):
    queryset = Certificate.objects.all()
    serializer_class = CertificateSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['cert_number', 'user__username', 'user__email']
    ordering = ['-issued_at']
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'ADMIN':
            queryset = Certificate.objects.all()
        elif user.role == 'TEACHER':
            # Teachers see their students' certificates
            from django.db.models import Q
            queryset = Certificate.objects.filter(
                Q(course__teacher=user) | Q(user=user)
            )
        else:
            queryset = Certificate.objects.filter(user=user)
        
        # Filters
        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param.upper())
        
        cert_type = self.request.query_params.get('type')
        if cert_type:
            queryset = queryset.filter(cert_type=cert_type.upper())
        
        return queryset.select_related('user', 'course', 'olympiad', 'verified_by')

    
    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def verify(self, request):
        """Verify certificate by number (Public)"""
        cert_number = request.query_params.get('number')
        if not cert_number:
            return Response({
                'success': False,
                'error': 'Sertifikat raqami talab qilinadi'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            cert = Certificate.objects.select_related('user', 'course', 'olympiad').get(cert_number=cert_number)
            return Response({
                'success': True,
                'valid': cert.status == 'VERIFIED',
                'certificate': CertificateVerifySerializer(cert).data
            })
        except Certificate.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Sertifikat topilmadi'
            }, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def approve(self, request, pk=None):
        """Approve certificate (Admin or Teacher)"""
        if request.user.role not in ['ADMIN', 'TEACHER']:
            return Response({'error': 'Admin yoki Teacher huquqi talab qilinadi'}, status=status.HTTP_403_FORBIDDEN)
        
        cert = self.get_object()
        
        # Teachers can only approve certificates for their own courses
        if request.user.role == 'TEACHER':
            if cert.course and cert.course.teacher != request.user:
                return Response({'error': "Faqat o'z kurslaringiz uchun sertifikat tasdiqlashingiz mumkin"}, 
                              status=status.HTTP_403_FORBIDDEN)
        
        cert.status = 'VERIFIED'
        cert.verified_at = timezone.now()
        cert.verified_by = request.user
        cert.rejection_reason = ''  # Clear any previous rejection
        cert.save()
        
        return Response({
            'success': True,
            'message': 'Sertifikat tasdiqlandi',
            'certificate': CertificateSerializer(cert, context={'request': request}).data
        })
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def reject(self, request, pk=None):
        """Reject certificate with reason (Admin or Teacher)"""
        if request.user.role not in ['ADMIN', 'TEACHER']:
            return Response({'error': 'Admin yoki Teacher huquqi talab qilinadi'}, status=status.HTTP_403_FORBIDDEN)
        
        cert = self.get_object()
        
        # Teachers can only reject certificates for their own courses
        if request.user.role == 'TEACHER':
            if cert.course and cert.course.teacher != request.user:
                return Response({'error': "Faqat o'z kurslaringiz uchun sertifikat rad etishingiz mumkin"}, 
                              status=status.HTTP_403_FORBIDDEN)
        
        reason = request.data.get('reason', '')
        if not reason or len(reason) < 10:
            return Response({'error': 'Rad etish sababi kamida 10 belgi bo\'lishi kerak'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        cert.status = 'REJECTED'
        cert.rejection_reason = reason
        cert.verified_by = request.user
        cert.verified_at = timezone.now()
        cert.save()
        
        return Response({
            'success': True,
            'message': 'Sertifikat rad etildi',
            'certificate': CertificateSerializer(cert, context={'request': request}).data
        })
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated], url_path='my-certificates')
    def my_certificates(self, request):
        """Get current user's certificates"""
        certs = Certificate.objects.filter(user=request.user).select_related('course', 'olympiad', 'verified_by')
        page = self.paginate_queryset(certs)
        if page is not None:
            serializer = CertificateSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        serializer = CertificateSerializer(certs, many=True, context={'request': request})
        return Response(serializer.data)

    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def batch_approve(self, request):
        """Batch approve certificates (Admin only)"""
        if request.user.role != 'ADMIN':
            return Response({'error': 'Admin huquqi talab qilinadi'}, status=status.HTTP_403_FORBIDDEN)
        
        cert_ids = request.data.get('ids', [])
        if not cert_ids:
            return Response({'error': 'ID lar talab qilinadi'}, status=status.HTTP_400_BAD_REQUEST)
        
        updated = Certificate.objects.filter(id__in=cert_ids, status='PENDING').update(
            status='VERIFIED',
            verified_at=timezone.now(),
            verified_by=request.user.get_full_name() or request.user.username
        )
        
        return Response({
            'success': True,
            'message': f'{updated} ta sertifikat tasdiqlandi'
        })
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def batch_reject(self, request):
        """Batch reject certificates (Admin only)"""
        if request.user.role != 'ADMIN':
            return Response({'error': 'Admin huquqi talab qilinadi'}, status=status.HTTP_403_FORBIDDEN)
        
        cert_ids = request.data.get('ids', [])
        if not cert_ids:
            return Response({'error': 'ID lar talab qilinadi'}, status=status.HTTP_400_BAD_REQUEST)
        
        updated = Certificate.objects.filter(id__in=cert_ids, status='PENDING').update(status='REJECTED')
        
        return Response({
            'success': True,
            'message': f'{updated} ta sertifikat rad etildi'
        })
    
    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def download(self, request, pk=None):
        """Download certificate PDF"""
        cert = self.get_object()
        
        # Check permission - user can only download their own or admin/teacher can download any
        if cert.user != request.user and request.user.role not in ['ADMIN', 'TEACHER']:
            return Response({'error': 'Ruxsat yo\'q'}, status=status.HTTP_403_FORBIDDEN)
        
        if cert.status != 'VERIFIED':
            return Response({'error': 'Sertifikat hali tasdiqlanmagan'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Generate PDF if not exists
        if not cert.pdf_file:
            from .certificate_generator import generate_certificate_pdf, generate_qr_code
            try:
                pdf_file = generate_certificate_pdf(cert)
                cert.pdf_file.save(pdf_file.name, pdf_file, save=True)
                
                qr_file = generate_qr_code(cert)
                cert.qr_code.save(qr_file.name, qr_file, save=True)
            except Exception as e:
                return Response({'error': f'PDF yaratishda xatolik: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Return PDF URL
        pdf_url = request.build_absolute_uri(cert.pdf_file.url)
        return Response({
            'success': True,
            'pdf_url': pdf_url,
            'qr_url': request.build_absolute_uri(cert.qr_code.url) if cert.qr_code else None
        })
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def regenerate_pdf(self, request, pk=None):
        """Regenerate certificate PDF (Admin only)"""
        if request.user.role != 'ADMIN':
            return Response({'error': 'Admin huquqi talab qilinadi'}, status=status.HTTP_403_FORBIDDEN)
        
        cert = self.get_object()
        
        if cert.status != 'VERIFIED':
            return Response({'error': 'Faqat tasdiqlangan sertifikatlar uchun PDF yaratish mumkin'}, status=status.HTTP_400_BAD_REQUEST)
        
        from .certificate_generator import generate_certificate_pdf, generate_qr_code
        try:
            pdf_file = generate_certificate_pdf(cert)
            cert.pdf_file.save(pdf_file.name, pdf_file, save=True)
            
            qr_file = generate_qr_code(cert)
            cert.qr_code.save(qr_file.name, qr_file, save=True)
            
            return Response({
                'success': True,
                'message': 'PDF qayta yaratildi',
                'pdf_url': request.build_absolute_uri(cert.pdf_file.url)
            })
        except Exception as e:
            return Response({'error': f'PDF yaratishda xatolik: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============= SUPPORT VIEWS =============

class SupportTicketViewSet(viewsets.ModelViewSet):
    queryset = SupportTicket.objects.all()
    serializer_class = SupportTicketSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['ticket_number', 'subject', 'user__username']
    ordering = ['-created_at']
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'ADMIN':
            queryset = SupportTicket.objects.all()
        else:
            queryset = SupportTicket.objects.filter(user=user)
        
        # Filters
        status_param = self.request.query_params.get('status')
        priority = self.request.query_params.get('priority')
        category = self.request.query_params.get('category')
        
        if status_param:
            queryset = queryset.filter(status=status_param.upper())
        if priority:
            queryset = queryset.filter(priority=priority.upper())
        if category:
            queryset = queryset.filter(category__iexact=category)
        
        return queryset.select_related('user').prefetch_related('messages')

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def stats(self, request):
        """Get support ticket statistics"""
        # 1. Category Distribution
        categories = SupportTicket.objects.values('category').annotate(count=Count('id'))
        category_data = [
            {'name': item['category'], 'value': item['count']}
            for item in categories
        ]
        
        # 2. Weekly Performance (Last 7 Days)
        from django.utils import timezone
        import datetime
        
        today = timezone.now().date()
        performance_data = []
        
        # We want data for the last 7 days including today
        for i in range(6, -1, -1):
            date = today - datetime.timedelta(days=i)
            day_start = timezone.make_aware(datetime.datetime.combine(date, datetime.time.min))
            day_end = timezone.make_aware(datetime.datetime.combine(date, datetime.time.max))
            
            created_count = SupportTicket.objects.filter(created_at__range=(day_start, day_end)).count()
            resolved_count = SupportTicket.objects.filter(
                updated_at__range=(day_start, day_end), 
                status='RESOLVED'
            ).count()
            
            performance_data.append({
                'name': date.strftime('%a'), # Mon, Tue...
                'date': date.strftime('%Y-%m-%d'),
                'open': created_count,
                'resolved': resolved_count
            })
            
        # 3. Response Time (Last 7 days avg per day)
        response_time_data = []
        for i in range(6, -1, -1):
            date = today - datetime.timedelta(days=i)
            day_start = timezone.make_aware(datetime.datetime.combine(date, datetime.time.min))
            day_end = timezone.make_aware(datetime.datetime.combine(date, datetime.time.max))
            
            # Find tickets created on this day that have messages
            tickets = SupportTicket.objects.filter(
                created_at__range=(day_start, day_end)
            ).prefetch_related('messages')
            
            total_time_minutes = 0
            count = 0
            
            for ticket in tickets:
                first_reply = ticket.messages.filter(is_internal=False).exclude(sender_id=ticket.user.id).first()
                if first_reply:
                    diff = first_reply.created_at - ticket.created_at
                    minutes = diff.total_seconds() / 60
                    total_time_minutes += minutes
                    count += 1
            
            avg_time = round(total_time_minutes / count) if count > 0 else 0
            
            response_time_data.append({
                'name': date.strftime('%a'),
                'time': avg_time
            })
            
        return Response({
            'success': True,
            'categories': category_data,
            'performance': performance_data,
            'response_time': response_time_data
        })
    
    def create(self, request, *args, **kwargs):
        """Create a new ticket"""
        serializer = CreateTicketSerializer(data=request.data)
        if serializer.is_valid():
            ticket_number = generate_unique_id('TCK', 4)
            ticket = SupportTicket.objects.create(
                ticket_number=ticket_number,
                user=request.user,
                subject=serializer.validated_data['subject'],
                category=serializer.validated_data['category'],
                priority=serializer.validated_data['priority']
            )
            
            # Add initial message
            TicketMessage.objects.create(
                ticket=ticket,
                sender_id=str(request.user.id),
                sender_name=request.user.get_full_name() or request.user.username,
                message=serializer.validated_data['message']
            )
            
            return Response({
                'success': True,
                'message': 'Murojaat yuborildi',
                'ticket': SupportTicketSerializer(ticket).data
            }, status=status.HTTP_201_CREATED)
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def reply(self, request, pk=None):
        """Add reply to ticket"""
        ticket = self.get_object()
        message = request.data.get('message')
        is_internal = request.data.get('is_internal', False)
        
        if not message:
            return Response({
                'success': False,
                'error': 'Xabar talab qilinadi'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Only admins can write internal notes
        if is_internal and request.user.role != 'ADMIN':
            is_internal = False
        
        reply = TicketMessage.objects.create(
            ticket=ticket,
            sender_id=str(request.user.id),
            sender_name=request.user.get_full_name() or request.user.username,
            message=message,
            is_internal=is_internal
        )
        
        # Update ticket status
        if request.user.role == 'ADMIN' and ticket.status == 'OPEN':
            ticket.status = 'IN_PROGRESS'
            ticket.save(update_fields=['status', 'updated_at'])
        
        # Create notification for user if admin replied (not internal)
        if request.user.role == 'ADMIN' and not is_internal:
            Notification.objects.create(
                user=ticket.user,
                title="Murojaatingizga javob berildi",
                message=f"Murojaat #{ticket.ticket_number}: {message[:50]}...",
                notification_type='SYSTEM',
                link=f"/support" 
            )
        
        return Response({
            'success': True,
            'message': 'Javob yuborildi',
            'reply': TicketMessageSerializer(reply, context={'request': request}).data
        })

    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        """Close/Resolve ticket"""
        ticket = self.get_object()
        ticket.status = 'RESOLVED'
        ticket.save(update_fields=['status', 'updated_at'])
        return Response({
            'success': True,
            'message': 'Murojaat yopildi'
        })

    @action(detail=False, methods=['post'], permission_classes=[IsAdmin])
    def bulk_resolve(self, request):
        """Bulk resolve tickets"""
        ids = request.data.get('ids', [])
        if not ids:
            return Response({
                'success': False,
                'error': 'IDlar berilmagan'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        updated = SupportTicket.objects.filter(id__in=ids).update(
            status='RESOLVED',
            updated_at=timezone.now()
        )
        
        return Response({
            'success': True,
            'message': f'{updated} ta murojaat yopildi'
        })
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def update_status(self, request, pk=None):
        """Update ticket status (Admin only)"""
        if request.user.role != 'ADMIN':
            return Response({'error': 'Admin huquqi talab qilinadi'}, status=status.HTTP_403_FORBIDDEN)
        
        ticket = self.get_object()
        new_status = request.data.get('status', '').upper()
        
        valid_statuses = dict(SupportTicket.STATUS_CHOICES).keys()
        if new_status not in valid_statuses:
            return Response({
                'success': False,
                'error': f'Noto\'g\'ri status. Mumkin bo\'lgan qiymatlar: {list(valid_statuses)}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        ticket.status = new_status
        ticket.save(update_fields=['status', 'updated_at'])
        
        return Response({
            'success': True,
            'message': 'Status yangilandi',
            'ticket': SupportTicketSerializer(ticket).data
        })
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def escalate(self, request, pk=None):
        """Escalate ticket (Admin only)"""
        if request.user.role != 'ADMIN':
            return Response({'error': 'Admin huquqi talab qilinadi'}, status=status.HTTP_403_FORBIDDEN)
        
        ticket = self.get_object()
        ticket.status = 'ESCALATED'
        ticket.priority = 'HIGH'
        ticket.save(update_fields=['status', 'priority', 'updated_at'])
        
        return Response({
            'success': True,
            'message': 'Murojaat yuqori darajaga ko\'tarildi'
        })


# ============= PAYMENT VIEWS =============

class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination
    
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'type', 'method', 'user']
    search_fields = ['transaction_id', 'user__username', 'user__first_name', 'user__phone', 'user__last_name', 'reference_id']
    ordering_fields = ['created_at', 'amount', 'completed_at']
    
    def calculate_unique_amount(self, original_amount):
        """
        Generate unique amount by adding random 1-99 tiyin/so'm
        Check if amount is already pending to avoid collision (optional but recommended)
        """
        import random
        from decimal import Decimal
        
        # Simple implementation: just random
        unique_add = random.randint(1, 99)
        final_amount = Decimal(str(original_amount)) + Decimal(str(unique_add)) # Or 0.01 * unique_add if using tiyin
        # Note: If it's tiyin, it should be / 100. If user request says "1-99 so'm", then whole numbers.
        # User example: 2000 + 7 = 2007. So whole numbers.
        
        return unique_add, final_amount

    def get_queryset(self):
        user = self.request.user
        if user.role == 'ADMIN':
            return Payment.objects.all().select_related('user')
        return Payment.objects.filter(user=user)

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def demo_topup(self, request):
        """Demo TopUp - Instant Balance Add"""
        amount = request.data.get('amount')
        method = request.data.get('method', 'PAYME')
        
        if not amount:
             return Response({'error': 'Summa kiritilmadi'}, status=status.HTTP_400_BAD_REQUEST)
             
        try:
            amount = float(amount)
            if amount < 1000:
                return Response({'error': 'Minimal summa 1000 so\'m'}, status=status.HTTP_400_BAD_REQUEST)
        except:
             return Response({'error': 'Noto\'g\'ri summa'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Create Completed Payment
        payment = Payment.objects.create(
            user=request.user,
            amount=amount,
            type='TOPUP',
            reference_id='wallet',
            method=method,
            status='COMPLETED',
            completed_at=timezone.now(),
            transaction_id=generate_unique_id('DEMO')
        )
        
        # Update Balance
        request.user.balance += Decimal(str(amount)) # Ensure decimal compat
        request.user.save(update_fields=['balance'])
        
        return Response({
            'success': True,
            'message': 'Hisobingiz to\'ldirildi (Demo)',
            'payment': PaymentSerializer(payment).data,
            'new_balance': request.user.balance
        })
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def initiate(self, request):
        """Initiate a payment"""
        payment_type = request.data.get('type')  # COURSE or OLYMPIAD
        reference_id = request.data.get('reference_id')
        method = request.data.get('method', 'PAYME')
        
        if not payment_type or not reference_id:
            return Response({
                'success': False,
                'error': 'Type va reference_id talab qilinadi'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get amount
        if payment_type == 'COURSE':
            try:
                item = Course.objects.get(id=reference_id)
                amount = item.price
            except Course.DoesNotExist:
                return Response({'error': 'Kurs topilmadi'}, status=status.HTTP_404_NOT_FOUND)
        elif payment_type == 'OLYMPIAD':
            try:
                item = Olympiad.objects.get(id=reference_id)
                amount = item.price
            except Olympiad.DoesNotExist:
                return Response({'error': 'Olimpiada topilmadi'}, status=status.HTTP_404_NOT_FOUND)
        elif payment_type == 'COURSE_CREATION_FEE':
            amount = 50000  # Fixed fee
            reference_id = 'fee' # Dummy ref
        elif payment_type == 'PREMIUM':
            amount = 150000 # Premium subscription
            reference_id = 'premium'
        elif payment_type == 'TOPUP':
            amount = request.data.get('amount')
            if not amount or float(amount) <= 0:
                return Response({'error': 'Noto\'g\'ri summa'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({'error': 'Noto\'g\'ri type'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Create pending payment
        import datetime
        from django.utils import timezone
        
        # unique_add, final_amount = self.calculate_unique_amount(amount)
        unique_add = 0
        final_amount = amount
        expires_at = timezone.now() + datetime.timedelta(minutes=15)
        
        payment = Payment.objects.create(
            user=request.user,
            amount=amount, # Store pure amount
            original_amount=amount,
            unique_add=unique_add,
            final_amount=final_amount,
            expires_at=expires_at,
            type=payment_type,
            reference_id=reference_id,
            method=method,
            status='PENDING',
            transaction_id=generate_unique_id('PAY')
        )
        
        response_data = {
            'success': True,
            'payment_id': payment.id,
            'amount': payment.amount,
            'transaction_id': payment.transaction_id,
            'unique_amount_details': {
                'original': amount,
                'unique_add': 0,
                'final': amount,
                'expires_at': expires_at
            }
        }

        if method == 'USERBOT':
             bot_url = ""
             bot_config = BotConfig.objects.filter(is_active=True).first()
             # Try to get bot username from config if we add it, or fetching me.
             # Ideally we should store username in BotConfig.
             # For now, let's assume we can fetch it or just use a helper.
             # We will update BotConfig model later or just fetch here.
             # Let's use a safe fallback or fetch from API if token exists.
             if bot_config:
                 try:
                     import requests
                     res = requests.get(f"https://api.telegram.org/bot{bot_config.bot_token}/getMe", timeout=5).json()
                     if res.get('ok'):
                         bot_username = res['result']['username']
                         bot_url = f"https://t.me/{bot_username}?start=pay_{payment.id}"
                 except:
                     pass
             
             response_data['bot_url'] = bot_url

        return Response(response_data)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def confirm(self, request, pk=None):
        """Confirm a pending payment"""
        payment = self.get_object()
        
        if payment.status != 'PENDING':
             return Response({'error': 'To\'lov allaqachon yakunlangan'}, status=status.HTTP_400_BAD_REQUEST)
             
        payment.status = 'COMPLETED'
        payment.completed_at = timezone.now()
        payment.save()
        
        # Logic to add balance/enroll/etc based on type
        # For 'TOPUP' or 'USERBOT', add to balance
        if payment.type in ['TOPUP', 'USERBOT'] or payment.method == 'USERBOT': 
             # Note: USERBOT method usually means manual transfer via bot, so we add to balance
             payment.user.balance += payment.amount
             payment.user.save()
             

             # Notify User via Telegram
             if payment.user.telegram_id:
                 try:
                     TelegramService.send_message(
                         payment.user.telegram_id, 
                         f"✅ <b>To'lov tasdiqlandi!</b>\n\nAdmin sizning to'lovingizni tasdiqladi.\nHisobingizga {int(payment.amount)} AC qo'shildi."
                     )
                 except: 
                     pass
        
        # Update Admin Message
        if payment.admin_message_ids:
            try:
                for msg_data in payment.admin_message_ids:
                    chat_id = msg_data.get('chat_id')
                    message_id = msg_data.get('message_id')
                    if chat_id and message_id:
                        new_caption = (
                            f"✅ <b>To'lov tasdiqlandi!</b>\n\n"
                            f"👤 <b>User:</b> {payment.user.first_name} ({payment.user.phone})\n"
                            f"🪙 <b>Coin:</b> {int(payment.amount)} AC\n"
                            f"💵 <b>Summa:</b> {payment.amount:,.0f} so'm\n" # Assuming amount is same as money for now or pure amount
                            f"📅 <b>Sana:</b> {payment.created_at.strftime('%d.%m.%Y %H:%M')}\n"
                            f"✅ <b>Status:</b> TASDIQLANGAN"
                        )
                        TelegramService.edit_message_caption(chat_id, message_id, new_caption)
            except Exception:
                pass


        return Response({'success': True, 'status': 'COMPLETED'})

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def reject(self, request, pk=None):
        """Reject a pending payment"""
        payment = self.get_object()
        
        if payment.status != 'PENDING':
             return Response({'error': 'To\'lov allaqachon yakunlangan'}, status=status.HTTP_400_BAD_REQUEST)
             
        payment.status = 'FAILED'
        payment.save()
        
        # Notify User via Telegram
        if payment.user.telegram_id:
             try:
                 TelegramService.send_message(
                     payment.user.telegram_id, 
                     f"❌ <b>To'lov rad etildi.</b>\n\nAdmin sizning to'lovingizni rad etdi. Iltimos, qayta tekshirib yuboring."
                 )
             except: 
                 pass

        # Update Admin Message
        if payment.admin_message_ids:
            try:
                for msg_data in payment.admin_message_ids:
                    chat_id = msg_data.get('chat_id')
                    message_id = msg_data.get('message_id')
                    if chat_id and message_id:
                        new_caption = (
                            f"❌ <b>To'lov rad etildi!</b>\n\n"
                            f"👤 <b>User:</b> {payment.user.first_name} ({payment.user.phone})\n"
                            f"🪙 <b>Coin:</b> {int(payment.amount)} AC\n"
                            f"💵 <b>Summa:</b> {payment.amount:,.0f} so'm\n"
                            f"📅 <b>Sana:</b> {payment.created_at.strftime('%d.%m.%Y %H:%M')}\n"
                            f"❌ <b>Status:</b> RAD ETILDI"
                        )
                        TelegramService.edit_message_caption(chat_id, message_id, new_caption)
            except Exception:
                pass

        return Response({'success': True, 'status': 'FAILED'})

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def refund(self, request, pk=None):
        """Refund a completed payment"""
        payment = self.get_object()
        
        if payment.status != 'COMPLETED':
             return Response({'error': 'Faqat bajarilgan to\'lovlarni qaytarish mumkin'}, status=status.HTTP_400_BAD_REQUEST)
             
        payment.status = 'REFUNDED'
        payment.save()
        
        # Deduct balance if it was a TOPUP
        if payment.type in ['TOPUP', 'USERBOT'] or payment.method == 'USERBOT':
            if payment.user.balance >= payment.amount:
                payment.user.balance -= payment.amount
                payment.user.save()
            else:
                 # What if user spent it? 
                 # For now, we just deduct what connects, or allow negative? 
                 # Let's deduct and allow negative or just deduct max possible?
                 # Safest: deduct anyway, let balance go negative or strictly check.
                 # Let's Deduct.
                 payment.user.balance -= payment.amount
                 payment.user.save()
        
        # Note: If it was a COURSE purchase, we usually DO NOT revoke access automatically 
        # unless specifically requested, to avoid accidental data loss.
        # But we marked it REFUNDED, so stats will be correct.
        
        return Response({'success': True, 'status': 'REFUNDED'})

    @action(detail=False, methods=['get'], permission_classes=[IsAdminUser])
    def export(self, request):
        """Export payments to CSV"""
        import csv
        from django.http import HttpResponse

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="payments.csv"'

        writer = csv.writer(response)
        writer.writerow(['ID', 'User', 'Type', 'Amount', 'Method', 'Status', 'Date', 'Transaction ID'])

        queryset = self.filter_queryset(self.get_queryset())
        for payment in queryset:
            writer.writerow([
                payment.id,
                payment.user.username,
                payment.type,
                payment.amount,
                payment.method,
                payment.status,
                payment.created_at.strftime('%Y-%m-%d %H:%M'),
                payment.transaction_id
            ])

        return response

        
        # Get Bot Config
        bot_config = BotConfig.objects.filter(is_active=True).first()
        humo_url = bot_config.humo_bot_url if bot_config else None
        
        return Response({
            'success': True,
            'payment': PaymentSerializer(payment).data,
            'pay_url': humo_url if method == 'HUMO' else (f"https://my.click.uz/..." if method == 'CLICK' else None),
            'unique_amount_details': {
                'original': amount,
                'unique_add': unique_add,
                'final': final_amount,
                'expires_at': expires_at
            }
        })
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def complete(self, request, pk=None):
        """Complete a payment (Mock for testing)"""
        payment = self.get_object()
        
        if payment.status != 'PENDING':
            return Response({
                'success': False,
                'error': 'To\'lov allaqachon amalga oshirilgan'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Mark as completed
        payment.status = 'COMPLETED'
        payment.completed_at = timezone.now()
        payment.transaction_id = generate_unique_id('TXN', 12)
        payment.save()
        
        # Handle post-payment logic
        if payment.type == 'TOPUP':
            payment.user.balance += payment.amount
            payment.user.save(update_fields=['balance'])
        elif payment.type == 'COURSE':
            try:
                course = Course.objects.get(id=payment.reference_id)
                first_lesson = course.lessons.all().order_by('module__order', 'order').first()
                Enrollment.objects.get_or_create(
                    user=payment.user, 
                    course=course,
                    defaults={'current_lesson': first_lesson}
                )
                course.students_count += 1
                course.save(update_fields=['students_count'])
            except Course.DoesNotExist:
                pass
        elif payment.type == 'OLYMPIAD':
            try:
                olympiad = Olympiad.objects.get(id=payment.reference_id)
                OlympiadRegistration.objects.get_or_create(
                    user=payment.user,
                    olympiad=olympiad,
                    defaults={'is_paid': True}
                )
            except Olympiad.DoesNotExist:
                pass
        
        return Response({
            'success': True,
            'message': 'To\'lov muvaffaqiyatli amalga oshirildi',
            'payment': PaymentSerializer(payment).data
        })

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def pay_with_balance(self, request):
        """Pay for item using wallet balance"""
        payment_type = request.data.get('type') # COURSE or OLYMPIAD
        reference_id = request.data.get('reference_id')
        user = request.user
        
        if not payment_type or not reference_id:
            return Response({'error': 'Ma\'lumotlar yetarli emas'}, status=status.HTTP_400_BAD_REQUEST)
            
        # Get Item and Price
        if payment_type == 'COURSE':
            try:
                item = Course.objects.get(id=reference_id)
                # Check if already enrolled
                if Enrollment.objects.filter(user=user, course=item).exists():
                     return Response({'error': 'Siz bu kursga allaqachon a\'zo algansiz'}, status=status.HTTP_400_BAD_REQUEST)
            except Course.DoesNotExist:
                return Response({'error': 'Kurs topilmadi'}, status=status.HTTP_404_NOT_FOUND)
        elif payment_type == 'OLYMPIAD':
            try:
                item = Olympiad.objects.get(id=reference_id)
                # Check if already registered
                if OlympiadRegistration.objects.filter(user=user, olympiad=item).exists():
                     return Response({'error': 'Siz allaqachon ro\'yxatdan o\'tgansiz'}, status=status.HTTP_400_BAD_REQUEST)
            except Olympiad.DoesNotExist:
                return Response({'error': 'Olimpiada topilmadi'}, status=status.HTTP_404_NOT_FOUND)
        else:
            return Response({'error': 'Noto\'g\'ri type'}, status=status.HTTP_400_BAD_REQUEST)
            
        price = item.price
        
        # Check Balance
        if user.balance < price:
            return Response({
                'success': False, 
                'error': 'Mablag\' yetarli emas',
                'required': float(price),
                'balance': float(user.balance)
            }, status=status.HTTP_402_PAYMENT_REQUIRED)
            
        # Deduct Balance
        user.balance -= price
        user.save(update_fields=['balance'])
        
        # Create Payment Record
        payment = Payment.objects.create(
            user=user,
            amount=price,
            type=payment_type,
            reference_id=reference_id,
            method='WALLET',
            status='COMPLETED',
            completed_at=timezone.now(),
            transaction_id=generate_unique_id('WAL', 12)
        )
        
        # Grant Access
        if payment_type == 'COURSE':
            first_lesson = item.lessons.all().order_by('module__order', 'order').first()
            Enrollment.objects.create(
                user=user, 
                course=item,
                current_lesson=first_lesson
            )
            item.students_count += 1
            item.save(update_fields=['students_count'])
            
        elif payment_type == 'OLYMPIAD':
            OlympiadRegistration.objects.create(
                user=user,
                olympiad=item,
                is_paid=True
            )
            
        return Response({
            'success': True,
            'message': 'To\'lov amalga oshirildi',
            'new_balance': float(user.balance)
        })


# ============= USER MANAGEMENT (ADMIN) =============

class UserViewSet(viewsets.ModelViewSet):
    """User management for admins"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering = ['-date_joined']
    
    def get_queryset(self):
        queryset = User.objects.all()
        
        role = self.request.query_params.get('role')
        is_active = self.request.query_params.get('is_active')
        
        if role:
            queryset = queryset.filter(role=role.upper())
        if is_active:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        return queryset

    def get_object(self):
        """Allow lookup by 'me' for current user"""
        pk = self.kwargs.get('pk')
        if pk == 'me':
            return self.request.user
        return super().get_object()

    def get_permissions(self):
        """Allow authenticated self-service for teacher onboarding actions."""
        if self.action in ['update_teacher_profile', 'verify_teacher']:
            return [IsAuthenticated()]
        return [permission() for permission in self.permission_classes]
    
    @action(detail=True, methods=['post'])
    def change_role(self, request, pk=None):
        """Change user role"""
        user = self.get_object()
        new_role = request.data.get('role', '').upper()
        
        if new_role not in ['STUDENT', 'TEACHER', 'ADMIN']:
            return Response({
                'success': False,
                'error': 'Noto\'g\'ri rol'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        user.role = new_role
        user.is_staff = (new_role == 'ADMIN')
        user.save(update_fields=['role', 'is_staff'])
        
        # If becoming teacher, ensure profile exists
        if new_role == 'TEACHER':
            TeacherProfile.objects.get_or_create(user=user)
        
        return Response({
            'success': True,
            'message': f'Foydalanuvchi roli {new_role} ga o\'zgartirildi'
        })
    
    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        """Toggle user active status"""
        user = self.get_object()
        user.is_active = not user.is_active
        user.save(update_fields=['is_active'])
        
        return Response({
            'success': True,
            'message': f'Foydalanuvchi {"faollashtirildi" if user.is_active else "bloklandi"}'
        })

    @action(detail=True, methods=['post'])
    def grant_vip(self, request, pk=None):
        """Admin grants VIP status to a teacher"""
        user = self.get_object()
        
        if user.role != 'TEACHER':
            return Response({'error': 'Faqat o\'qituvchilarga VIP berilishi mumkin'}, status=status.HTTP_400_BAD_REQUEST)
            
        duration_days = int(request.data.get('duration_days', 30))
        reason = request.data.get('reason', '')
        
        from .models import TeacherProfile, VIPLog
        from django.utils import timezone
        from datetime import timedelta
        
        profile, _ = TeacherProfile.objects.get_or_create(user=user)
        
        old_type = profile.teacher_type
        
        if duration_days == -1:
            profile.is_lifetime_vip = True
            profile.vip_expire_date = None
        else:
            profile.is_lifetime_vip = False
            if profile.vip_expire_date and profile.vip_expire_date > timezone.now():
                profile.vip_expire_date += timedelta(days=duration_days)
            else:
                profile.vip_expire_date = timezone.now() + timedelta(days=duration_days)
                
        profile.teacher_type = 'VIP'
        profile.save()
        
        VIPLog.objects.create(
            teacher=user,
            given_by=request.user,
            prev_type=old_type,
            new_type='VIP',
            duration_days=duration_days,
            reason=reason
        )
        
        return Response({
            'success': True,
            'message': f'"{user.get_full_name() or user.username}" uchun VIP berildi.',
            'is_vip': profile.is_vip,
            'vip_expire_date': profile.vip_expire_date
        })

    @action(detail=False, methods=['post'])
    def bulk_status_update(self, request):
        """Bulk update user status"""
        user_ids = request.data.get('user_ids', [])
        is_active = request.data.get('is_active')
        
        if not isinstance(user_ids, list) or is_active is None:
            return Response({'error': 'user_ids va is_active talab qilinadi'}, status=status.HTTP_400_BAD_REQUEST)
            
        User.objects.filter(id__in=user_ids).exclude(role='ADMIN').update(is_active=is_active)
        
        return Response({
            'success': True,
            'message': 'Tanlangan foydalanuvchilar holati yangilandi'
        })

    @action(detail=False, methods=['post'])
    def bulk_role_update(self, request):
        """Bulk update user roles"""
        user_ids = request.data.get('user_ids', [])
        new_role = request.data.get('role', '').upper()
        
        if new_role not in ['STUDENT', 'TEACHER', 'ADMIN']:
            return Response({'error': 'Noto\'g\'ri rol'}, status=status.HTTP_400_BAD_REQUEST)
            
        users = User.objects.filter(id__in=user_ids).exclude(role='ADMIN')
        count = 0
        
        for user in users:
            user.role = new_role
            user.is_staff = (new_role == 'ADMIN')
            user.save(update_fields=['role', 'is_staff'])
            
            if new_role == 'TEACHER':
                TeacherProfile.objects.get_or_create(user=user)
            count += 1
                
        return Response({
            'success': True,
            'message': f'{count} ta foydalanuvchi roli {new_role} ga o\'zgartirildi'
        })

    @action(detail=True, methods=['post'])
    def verify_teacher(self, request, pk=None):
        """Update teacher verification status with full flow"""
        user = self.get_object()
        status_val = request.data.get('status', '').upper()
        rejection_reason = request.data.get('rejection_reason', '')
        is_admin = request.user.role == 'ADMIN'
        is_self_request = user == request.user
        
        if status_val not in ['APPROVED', 'REJECTED', 'BLOCKED', 'PENDING']:
            return Response({'error': 'Noto\'g\'ri status'}, status=status.HTTP_400_BAD_REQUEST)
            
        profile, _ = TeacherProfile.objects.get_or_create(user=user)

        if not is_admin:
            if not is_self_request:
                return Response({'error': 'Ruxsat yo\'q'}, status=status.HTTP_403_FORBIDDEN)
            if request.user.role != 'TEACHER':
                return Response(
                    {'error': 'Faqat o\'qituvchi hisoblari onboarding arizasini yubora oladi'},
                    status=status.HTTP_403_FORBIDDEN
                )
            if status_val != 'PENDING':
                return Response(
                    {'error': 'Faqat PENDING statusini yuborishingiz mumkin'},
                    status=status.HTTP_403_FORBIDDEN
                )

            profile.verification_status = 'PENDING'
            profile.rejection_reason = ""
            profile.save(update_fields=['verification_status', 'rejection_reason'])

            return Response({
                'success': True,
                'message': 'Ariza moderatorga yuborildi',
                'user_role': user.role
            })

        profile.verification_status = status_val
        
        if status_val == 'APPROVED':
            user.role = 'TEACHER'
            user.is_staff = False
            user.is_active = True
            user.save(update_fields=['role', 'is_staff', 'is_active'])
            
            profile.approved_at = timezone.now()
            profile.approved_by = request.user
            profile.rejection_reason = ""
            
            Notification.objects.create(
                user=user,
                title="Tabriklaymiz!",
                message="Sizning o'qituvchi sifatidagi arizangiz tasdiqlandi. Endi kurslar yaratishingiz mumkin.",
                notification_type='SYSTEM'
            )
            
        elif status_val == 'REJECTED':
            profile.rejection_reason = rejection_reason
            Notification.objects.create(
                user=user,
                title="Ariza rad etildi",
                message=f"Sizning o'qituvchi sifatidagi arizangiz rad etildi. Sabab: {rejection_reason}",
                notification_type='SYSTEM'
            )
            
        elif status_val == 'BLOCKED':
            user.is_active = False
            user.save(update_fields=['is_active'])
        elif status_val == 'PENDING':
            profile.rejection_reason = ""
            
        profile.save()
        
        return Response({
            'success': True, 
            'message': f'Status {status_val} ga o\'zgartirildi',
            'user_role': user.role
        })

    @action(detail=True, methods=['post'])
    def update_teacher_profile(self, request, pk=None):
        """Update teacher profile fields (Onboarding/Edit)"""
        user = self.get_object()
        # Allow own profile update or admin update
        if request.user != user and not request.user.role == 'ADMIN':
            return Response({'error': 'Ruxsat yo\'q'}, status=status.HTTP_403_FORBIDDEN)
            
        profile, _ = TeacherProfile.objects.get_or_create(user=user)
        
        data = request.data
        for field in ['bio', 'experience_years', 'specialization', 'telegram_username', 
                      'instagram_username', 'youtube_channel', 'linkedin_profile']:
            if field in data:
                setattr(profile, field, data[field])
        
        profile.save()
        
        # Handle avatar if included in user data or separate
        if 'first_name' in data: user.first_name = data['first_name']
        if 'last_name' in data: user.last_name = data['last_name']
        if 'avatar' in request.FILES:
            user.avatar = request.FILES['avatar']
        
        # Handle identity document
        if 'identity_document' in request.FILES:
            profile.identity_document = request.FILES['identity_document']
            profile.save()
            
        user.save()
        return Response({'success': True, 'message': 'Profil yangilandi'})

    @action(detail=True, methods=['post'])
    def send_notification(self, request, pk=None):
        """Send a manual notification to a user"""
        user = self.get_object()
        title = request.data.get('title')
        message = request.data.get('message')
        notification_type = request.data.get('notification_type', 'SYSTEM')
        channel = request.data.get('channel', 'WEB') 
        
        if not title or not message:
            return Response({'error': 'Sarlavha va xabar kiritilishi shart'}, status=status.HTTP_400_BAD_REQUEST)

        Notification.objects.create(
            user=user,
            title=title,
            message=message,
            notification_type=notification_type,
            channel=channel
        )
        
        return Response({'success': True, 'message': 'Bildirishnoma yuborildi'})

    @action(detail=True, methods=['get'])
    def teacher_stats(self, request, pk=None):
        """Get summarized teacher statistics"""
        user = self.get_object()
        if user.role != 'TEACHER':
             return Response({'error': 'Foydalanuvchi o\'qituvchi emas'}, status=status.HTTP_400_BAD_REQUEST)
             
        serializer = self.get_serializer(user)
        data = serializer.data
        
        return Response({
            'courses': data.get('courses_count', 0),
            'students': data.get('students_count', 0),
            'revenue': data.get('total_revenue', 0.0),
            'olympiads': data.get('olympiads_count', 0),
            'rating': 5.0, # Placeholder or calculate
            'is_verified': user.teacher_profile.verification_status == 'APPROVED' if hasattr(user, 'teacher_profile') else False,
            'is_identity_verified': user.teacher_profile.is_identity_verified if hasattr(user, 'teacher_profile') else False
        })

    @action(detail=True, methods=['post'])
    def toggle_identity_verification(self, request, pk=None):
        """Toggle identity verification status"""
        user = self.get_object()
        profile, _ = TeacherProfile.objects.get_or_create(user=user)
        profile.is_identity_verified = not profile.is_identity_verified
        profile.save()
        
        return Response({
            'success': True, 
            'is_identity_verified': profile.is_identity_verified,
            'message': 'Shaxsni tasdiqlash holati o\'zgartirildi'
        })

    @action(detail=True, methods=['get'])
    def performance_report(self, request, pk=None):
        """Full performance report for a student"""
        user = self.get_object()
        
        # Security: Only admin, teacher or the user themselves
        if not (request.user.role in ['ADMIN', 'TEACHER'] or request.user == user):
            return Response({'error': 'Ruxsat yo\'q'}, status=status.HTTP_403_FORBIDDEN)
            
        # 1. Course Stats
        enrollments = Enrollment.objects.filter(user=user).select_related('course')
        course_data = []
        for en in enrollments:
            # Get lessons count
            total_lessons = Lesson.objects.filter(module__course=en.course).count()
            completed_lessons = LessonProgress.objects.filter(user=user, lesson__module__course=en.course, is_completed=True).count()
            
            course_data.append({
                'id': en.course.id,
                'title': en.course.title,
                'progress': float(en.progress),
                'total_lessons': total_lessons,
                'completed_lessons': completed_lessons,
                'last_accessed': en.last_accessed_at,
                'is_completed': en.completed_at is not None
            })
            
        # 2. Olympiad Stats
        olympiad_results = TestResult.objects.filter(user=user).select_related('olympiad')
        olympiad_data = []
        for res in olympiad_results:
            # Rank calculation
            rank = TestResult.objects.filter(
                olympiad=res.olympiad,
                score__gt=res.score
            ).count() + 1
            
            olympiad_data.append({
                'rank': rank,
                'id': res.olympiad.id,
                'title': res.olympiad.title,
                'score': res.score,
                'percentage': float(res.percentage or 0),
                'status': res.status,
                'date': res.created_at
            })
            
        # 3. Overall Stats
        total_xp = user.xp
        level = user.level
        
        return Response({
            'success': True,
            'user': {
                'id': user.id,
                'full_name': user.get_full_name() or user.username,
                'username': user.username,
                'xp': total_xp,
                'level': level,
                'role': user.role
            },
            'summary': {
                'courses_enrolled': enrollments.count(),
                'courses_completed': enrollments.filter(completed_at__isnull=False).count(),
                'olympiads_participated': olympiad_results.count(),
                'avg_olympiad_score': olympiad_results.aggregate(models.Avg('score'))['score__avg'] or 0
            },
            'courses': course_data,
            'olympiads': olympiad_data
        })

    @action(detail=True, methods=['post'])
    def reset_password(self, request, pk=None):
        """Reset user password (Admin)"""
        user = self.get_object()
        new_password = request.data.get('new_password')
        
        if not new_password or len(new_password) < 6:
            return Response({
                'success': False,
                'error': 'Yangi parol kamida 6 ta belgidan iborat bo\'lishi kerak'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        user.set_password(new_password)
        user.save()
        
        return Response({
            'success': True,
            'message': 'Parol yangilandi'
        })


# ============= ADMIN STATS VIEW =============

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_stats(request):
    """Get comprehensive admin dashboard statistics"""
    if request.user.role != 'ADMIN':
        return Response({'error': 'Admin huquqi talab qilinadi'}, status=status.HTTP_403_FORBIDDEN)
    
    today = timezone.now().date()
    this_month_start = today.replace(day=1)
    last_month_start = (this_month_start - timedelta(days=1)).replace(day=1)
    
    # User stats
    total_users = User.objects.count()
    new_users_this_month = User.objects.filter(date_joined__gte=this_month_start).count()
    new_users_last_month = User.objects.filter(
        date_joined__gte=last_month_start,
        date_joined__lt=this_month_start
    ).count()
    
    user_growth = 0
    if new_users_last_month > 0:
        user_growth = ((new_users_this_month - new_users_last_month) / new_users_last_month) * 100
    
    # Course stats
    total_courses = Course.objects.count()
    total_enrollments = Enrollment.objects.count()
    avg_course_rating = Course.objects.aggregate(avg=Avg('rating'))['avg'] or 0
    
    # Olympiad stats
    total_olympiads = Olympiad.objects.count()
    active_olympiads = Olympiad.objects.filter(status='ACTIVE').count()
    upcoming_olympiads = Olympiad.objects.filter(status='UPCOMING').count()
    total_participants = OlympiadRegistration.objects.count()
    
    # Certificate stats
    total_certificates = Certificate.objects.count()
    pending_certificates = Certificate.objects.filter(status='PENDING').count()
    verified_certificates = Certificate.objects.filter(status='VERIFIED').count()
    
    # Support stats
    total_tickets = SupportTicket.objects.count()
    open_tickets = SupportTicket.objects.filter(status='OPEN').count()
    in_progress_tickets = SupportTicket.objects.filter(status='IN_PROGRESS').count()
    high_priority_tickets = SupportTicket.objects.filter(priority='HIGH', status__in=['OPEN', 'IN_PROGRESS']).count()
    
    # Finance stats
    total_revenue = Payment.objects.filter(status='COMPLETED').aggregate(sum=Sum('amount'))['sum'] or 0
    this_month_revenue = Payment.objects.filter(
        status='COMPLETED',
        completed_at__gte=this_month_start
    ).aggregate(sum=Sum('amount'))['sum'] or 0
    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_count = Payment.objects.filter(created_at__gte=today_start).count()
    refunded_amount = Payment.objects.filter(status='CANCELLED').aggregate(sum=Sum('amount'))['sum'] or 0
    
    pending_payments = Payment.objects.filter(status='PENDING').count()
    
    # Top courses by enrollment
    top_courses = Course.objects.order_by('-students_count')[:5].values('id', 'title', 'students_count')
    
    # Top subjects by revenue
    subject_revenue = Course.objects.values('subject').annotate(
        total=Sum('enrollments__id')
    ).order_by('-total')[:5]
    
    stats = {
        'users': {
            'total': total_users,
            'students': User.objects.filter(role='STUDENT').count(),
            'admins': User.objects.filter(role='ADMIN').count(),
            'new_this_month': new_users_this_month,
            'growth_percent': round(user_growth, 1),
            'active': User.objects.filter(is_active=True).count(),
        },
        'courses': {
            'total': total_courses,
            'active': Course.objects.filter(is_active=True).count(),
            'featured': Course.objects.filter(is_featured=True).count(),
            'total_enrollments': total_enrollments,
            'avg_rating': round(float(avg_course_rating), 2),
            'top_courses': list(top_courses),
        },
        'olympiads': {
            'total': total_olympiads,
            'upcoming': upcoming_olympiads,
            'active': active_olympiads,
            'completed': Olympiad.objects.filter(status='COMPLETED').count(),
            'total_participants': total_participants,
            'avg_score': TestResult.objects.aggregate(avg=Avg('percentage'))['avg'] or 0,
        },
        'certificates': {
            'total': total_certificates,
            'pending': pending_certificates,
            'verified': verified_certificates,
            'rejected': Certificate.objects.filter(status='REJECTED').count(),
        },
        'support': {
            'total': total_tickets,
            'open': open_tickets,
            'in_progress': in_progress_tickets,
            'resolved': SupportTicket.objects.filter(status='RESOLVED').count(),
            'high_priority': high_priority_tickets,
        },
        'finance': {
            'total_revenue': float(total_revenue),
            'this_month': float(this_month_revenue),
            'pending_payments': pending_payments,
            'completed_payments': Payment.objects.filter(status='COMPLETED').count(),
            'today_count': today_count,
            'refunded_amount': float(refunded_amount),
        },
        'recent_activity': {
            'recent_enrollments': Enrollment.objects.count(),
            'recent_tests': TestResult.objects.filter(submitted_at__gte=this_month_start).count(),
            'recent_tickets': SupportTicket.objects.filter(created_at__gte=this_month_start).count(),
        }
    }
    
    return Response({
        'success': True,
        'stats': stats,
        'generated_at': timezone.now()
    })


# ============= BOT CONFIG & LINKING VIEWS =============

class BotConfigViewSet(viewsets.ModelViewSet):
    """Admin-only viewset for Bot Configuration"""
    queryset = BotConfig.objects.all()
    serializer_class = BotConfigSerializer
    # permission_classes = [IsAuthenticated, IsAdmin]

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsAdmin()]

    def get_serializer_class(self):
        if self.request.user and self.request.user.role == 'ADMIN':
            return BotConfigSerializer
        return PublicBotConfigSerializer

    def list(self, request, *args, **kwargs):
        config = BotConfig.objects.first()
        if not config:
            # Create a default config if it doesn't exist
            config = BotConfig.objects.create(
                bot_token="YOUR_TOKEN_HERE",
                admin_chat_id="0",
                is_active=False
            )
        # Get real-time stats
        bot_users_count = User.objects.filter(telegram_id__isnull=False).exclude(telegram_id=0).count()
        total_users_count = User.objects.filter(role='STUDENT').count()
        
        # Get Manual Payment Config
        manual_config = PaymentProviderConfig.objects.filter(type='MANUAL').first()
        card_number = ""
        card_holder = ""
        if manual_config and manual_config.config:
            card_number = manual_config.config.get('card_number', "")
            card_holder = manual_config.config.get('holder_name', "")

        serializer = self.get_serializer(config)
        data = serializer.data
        data['card_number'] = card_number
        data['card_holder'] = card_holder
        
        return Response({
            'success': True, 
            'config': data,
            'stats': {
                'bot_users_count': bot_users_count,
                'total_users_count': total_users_count
            }
        })

    @action(detail=False, methods=['post'])
    def save_config(self, request):
        config = BotConfig.objects.first()
        if config:
            serializer = self.get_serializer(config, data=request.data, partial=True)
        else:
            serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
            serializer.save()
            
            # Save Card Config
            card_number = request.data.get('card_number')
            card_holder = request.data.get('card_holder')
            
            if card_number is not None or card_holder is not None:
                manual_config = PaymentProviderConfig.objects.filter(type='MANUAL').first()
                if not manual_config:
                    manual_config = PaymentProviderConfig.objects.create(
                        name="Bank Karta (Manual)",
                        type='MANUAL',
                        provider='CARD',
                        is_active=True,
                        config={}
                    )
                
                new_config = manual_config.config or {}
                if card_number is not None:
                    new_config['card_number'] = card_number
                if card_holder is not None:
                    new_config['holder_name'] = card_holder
                
                manual_config.config = new_config
                manual_config.save()

            return Response({
                'success': True,
                'message': 'Bot sozlamalari saqlandi',
                'config': serializer.data
            })
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def broadcast_message(self, request):
        """Send message to all users who have linked their Telegram"""
        from .bot_service import BotService
        
        message_text = request.data.get('message')
        if not message_text:
            return Response({'success': False, 'error': 'Xabar matni talab qilinadi'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get all users with telegram_id
        users = User.objects.filter(telegram_id__isnull=False).exclude(telegram_id=0)
        
        count = 0
        for user in users:
            sent = BotService.send_message(user.telegram_id, message_text)
            if sent:
                count += 1
        
        return Response({
            'success': True,
            'message': f'Xabar {count} ta foydalanuvchiga muvaffaqiyatli yuborildi'
        })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def get_telegram_linking_token(request):
    """Generate a unique token to link Telegram account"""
    user = request.user
    
    # Generate a random 20-char token
    token = ''.join(random.choices(string.ascii_letters + string.digits, k=20))
    user.telegram_linking_token = token
    user.save(update_fields=['telegram_linking_token'])
    
    # Get bot username from config
    config = BotConfig.objects.filter(is_active=True).first()
    bot_username = "ardentsoft_olimpiada_bot" # Fallback
    if config:
        # We could potentially store bot username in config too
        pass

    return Response({
        'success': True,
        'token': token,
        'bot_url': f"https://t.me/{bot_username}?start={token}"
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def telegram_webhook(request):
    """
    Webhook endpoint for Telegram Bot
    This will process updates and handle user linking
    """
    from .bot_service import BotService
    
    update = request.data
    
    def show_main_menu(chat_id, text="Nima bilan yordam bera olaman?"):
        reply_markup = {
            "keyboard": [
                [{"text": "🏆 Mening Olimpiadalarim"}, {"text": "📚 Mening Kurslarim"}],
                [{"text": "🎥 Meetinglar"}, {"text": "📊 Natijalarim"}],
                [{"text": "❓ Yordam"}]
            ],
            "resize_keyboard": True
        }
        return BotService.send_message(chat_id, text, reply_markup=reply_markup)

    # Handle incoming message
    if 'message' in update:
        message = update['message']
        chat_id = message['chat']['id']
        text = message.get('text', '')
        
        # Handle /start with token: /start <token>
        if text.startswith('/start'):
            parts = text.split()
            if len(parts) > 1:
                token = parts[1]
                user = BotService.link_user(chat_id, token)
                
                if user:
                    welcome_text = f"✅ <b>Tabriklaymiz, {user.first_name}!</b>\n\nSizning platformadagi hisobingiz muvaffaqiyatli bog'landi."
                    show_main_menu(chat_id, welcome_text)
                else:
                    BotService.send_message(chat_id, "❌ <b>Xatolik!</b>\n\nToken yaroqsiz yoki muddati o'tgan. Iltimos, platformadan qaytadan urinib ko'ring.")
            else:
                user = User.objects.filter(telegram_id=chat_id).first()
                if user:
                    show_main_menu(chat_id, f"Qaytganingizdan xursandmiz, <b>{user.first_name}</b>!")
                else:
                    welcome_text = "👋 <b>Hogwords Olimpiada botiga xush kelibsiz!</b>\n\nHisobingizni bog'lash uchun platformadagi profilingizdan foydalaning."
                    reply_markup = {
                        "inline_keyboard": [[
                            {"text": "🚀 Platformada ro'yxatdan o'tish", "url": "https://hogwords.uz/auth"}
                        ]]
                    }
                    BotService.send_message(chat_id, welcome_text, reply_markup=reply_markup)
        
        # Handle location sharing
        elif 'location' in message:
            location = message['location']
            lat = location.get('latitude')
            lon = location.get('longitude')
            
            user = User.objects.filter(telegram_id=chat_id).first()
            if user:
                # Check for contacted winner prize
                prize = WinnerPrize.objects.filter(student=user, status='CONTACTED').order_by('-awarded_at').first()
                if prize:
                    PrizeAddress.objects.update_or_create(
                        prize=prize,
                        defaults={
                            'latitude': lat,
                            'longitude': lon
                        }
                    )
                    prize.status = 'ADDRESS_RECEIVED'
                    prize.save()
                    BotService.send_message(chat_id, "✅ <b>Manzil qabul qilindi!</b>\n\nTez orada sovriningizni yuboramiz. Rahmat!")
                    BotService.send_to_admin(f"📦 <b>Yangi manzil!</b>\nStudent: {user.get_full_name()}\nOlimpiada: {prize.olympiad.title}\nTur: Lokatsiya")
                else:
                    BotService.send_message(chat_id, "Manzil uchun rahmat!")

        # Handle menu buttons
        elif text == "🏆 Mening Olimpiadalarim":
            user = User.objects.filter(telegram_id=chat_id).first()
            if user:
                registrations = user.olympiad_registrations.all()[:5]
                if registrations:
                    resp = "🏆 <b>Sizning olimpiadalaringiz:</b>\n\n"
                    for reg in registrations:
                        status_emoji = "⏳" if reg.olympiad.status == 'UPCOMING' else "🚀"
                        resp += f"{status_emoji} <b>{reg.olympiad.title}</b>\n"
                        resp += f"📅 {reg.olympiad.start_date.strftime('%d.%m %H:%M')}\n\n"
                    BotService.send_message(chat_id, resp)
                else:
                    BotService.send_message(chat_id, "Siz hali hech qanday olimpiadaga ro'yxatdan o'tmagansiz.")
        
        # Handle address text if not a menu command
        elif text and text not in ["📚 Mening Kurslarim", "🎥 Meetinglar", "📊 Natijalarim", "❓ Yordam"]:
             user = User.objects.filter(telegram_id=chat_id).first()
             if user:
                prize = WinnerPrize.objects.filter(student=user, status='CONTACTED').order_by('-awarded_at').first()
                if prize:
                    PrizeAddress.objects.update_or_create(
                        prize=prize,
                        defaults={'address_text': text}
                    )
                    prize.status = 'ADDRESS_RECEIVED'
                    prize.save()
                    BotService.send_message(chat_id, "✅ <b>Manzil qabul qilindi!</b>\n\nTez orada sovriningizni yuboramiz. Rahmat!")
                    BotService.send_to_admin(f"📦 <b>Yangi manzil!</b>\nStudent: {user.get_full_name()}\nOlimpiada: {prize.olympiad.title}\nTur: Matn: {text}")
        
        elif text == "📚 Mening Kurslarim":
            user = User.objects.filter(telegram_id=chat_id).first()
            if user:
                enrollments = user.enrollments.all()[:5]
                if enrollments:
                    resp = "📚 <b>Sizning kurslaringiz:</b>\n\n"
                    for enr in enrollments:
                        resp += f"📘 <b>{enr.course.title}</b>\n"
                        resp += f"📈 Progress: {float(enr.progress):.0f}%\n\n"
                    BotService.send_message(chat_id, resp)
                else:
                    BotService.send_message(chat_id, "Siz hali hech qanday kursga yozilmagansiz.")

        elif text == "🎥 Meetinglar":
            # In a real app, you would fetch from a Meetings model
            BotService.send_message(chat_id, "📅 <b>Yaqinlashayotgan meetinglar:</b>\n\nHozircha rejalashtirilgan meetinglar yo'q.")

        elif text == "📊 Natijalarim":
            user = User.objects.filter(telegram_id=chat_id).first()
            if user:
                results = user.test_results.order_by('-submitted_at')[:5]
                if results:
                    resp = "📊 <b>Sizning so'nggi natijalaringiz:</b>\n\n"
                    for res in results:
                        resp += f"📝 <b>{res.olympiad.title}</b>\n"
                        resp += f"✅ Ball: {res.score} ({float(res.percentage):.1f}%)\n"
                        resp += f"📅 {res.submitted_at.strftime('%d.%m.%Y')}\n\n"
                    BotService.send_message(chat_id, resp)
                else:
                    BotService.send_message(chat_id, "Siz hali olimpiadalarda qatnashmagansiz.")

        elif text == "❓ Yordam":
            help_text = """
❓ <b>Yordam markazi</b>

Bot orqali siz:
• Olimpiada va darslar haqida eslatmalar olasiz
• Kurslaringiz progressini kuzatasiz
• Imtihon natijalarini ko'rasiz

Agar savollaringiz bo'lsa, @admin_user ga murojaat qiling yoki platformadagi "Yordam" bo'limidan foydalaning.
"""
            BotService.send_message(chat_id, help_text)

    return Response({'status': 'ok'})

# ============= WALLET VIEWS =============

class WalletViewSet(viewsets.GenericViewSet):
    """
    Wallet API endpoints
    
    POST /api/wallet/top-up/ - Top up balance (Simulation)
    POST /api/wallet/purchase/ - Purchase item with balance
    """
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'], url_path='top-up')
    def top_up(self, request):
        """
        Simulate Top-Up via Payment System (Payme/Click)
        Body: { amount, method }
        """
        amount = request.data.get('amount')
        method = request.data.get('method', 'PAYME')
        
        if not amount or float(amount) <= 0:
            return Response({'error': 'Noto\'g\'ri summa'}, status=status.HTTP_400_BAD_REQUEST)
        
        amount_decimal = float(amount)
        
        # 1. Create Payment Record
        payment = Payment.objects.create(
            user=request.user,
            amount=amount_decimal,
            type='WALLET_TOPUP',
            reference_id='WALLET',
            method=method,
            status='COMPLETED', # In simulation we complete immediately
            transaction_id=f"TRX-{generate_unique_id('WL')}"
        )
        payment.completed_at = timezone.now()
        payment.save()
        
        # 2. Update User Balance
        request.user.balance = float(request.user.balance) + amount_decimal
        request.user.save(update_fields=['balance'])
        
        return Response({
            'success': True,
            'message': 'Hisob muvaffaqiyatli to\'ldirildi',
            'balance': request.user.balance,
            'payment': PaymentSerializer(payment).data
        })

    @action(detail=False, methods=['post'])
    def purchase(self, request):
        """
        Purchase Item (Course/Olympiad) using Wallet Balance
        Body: { type: 'COURSE'|'OLYMPIAD', id: <id> }
        """
        item_type = request.data.get('type')
        item_id = request.data.get('id')
        
        if not item_type or not item_id:
            return Response({'error': 'error.missing_data'}, status=status.HTTP_400_BAD_REQUEST)
            
        user = request.user
        price = 0
        item_title = ""
        
        # 1. Resolve Item & Price
        try:
            if item_type == 'COURSE':
                item = Course.objects.get(id=item_id)
                price = item.price
                item_title = item.title
                
                # Check if already enrolled
                if Enrollment.objects.filter(user=user, course=item).exists():
                    return Response({'error': 'error.already_enrolled'}, status=status.HTTP_400_BAD_REQUEST)
                    
            elif item_type == 'OLYMPIAD':
                item = Olympiad.objects.get(id=item_id)
                price = item.price
                item_title = item.title
                
                # Check if already registered
                if OlympiadRegistration.objects.filter(user=user, olympiad=item).exists():
                    return Response({'error': 'error.already_registered'}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({'error': 'error.invalid_type'}, status=status.HTTP_400_BAD_REQUEST)
                
        except (Course.DoesNotExist, Olympiad.DoesNotExist):
            return Response({'error': 'error.not_found'}, status=status.HTTP_404_NOT_FOUND)
            
        # 2. Check Balance
        if user.balance < price:
            return Response({
                'success': False,
                'error': 'error.insufficient_balance',
                'required': price,
                'balance': user.balance
            }, status=status.HTTP_402_PAYMENT_REQUIRED)
            
        # 3. Deduct Balance
        user.balance = float(user.balance) - float(price)
        user.save(update_fields=['balance'])
        
        # 4. Create Payment Record (Internal Transfer)
        Payment.objects.create(
            user=user,
            amount=price,
            type=item_type,
            reference_id=str(item_id),
            method='WALLET',
            status='COMPLETED',
            transaction_id=f"INT-{generate_unique_id('PAY')}",
            completed_at=timezone.now()
        )
        
        # 5. Fulfill Service
        if item_type == 'COURSE':
            first_lesson = item.lessons.all().order_by('module__order', 'order').first()
            Enrollment.objects.create(
                user=user, 
                course=item,
                current_lesson=first_lesson
            )
            # No immediate XP for buying course, only for completion? User said "hp har bir oquvchi bir kurs tugatganida beriladi" -> OK. 
            # But "olimpiadada qancha hp berislhari" -> usually participation XP?
            # Let's give minimal XP for purchase action itself? No, stick to completion/participation.
            
        elif item_type == 'OLYMPIAD':
            OlympiadRegistration.objects.create(user=user, olympiad=item, is_paid=True)
            # Give participation XP immediately? 
            # item.xp_reward is for ? Let's assume participation.
            user.add_xp(item.xp_reward, 'OLYMPIAD_PARTICIPATION', f"Olimpiada sotib olindi: {item.title}")
            
            # Notify Bot
            try:
                BotService.notify_olympiad(user, item, message_type="registration")
            except Exception as e:
                print(f"Bot notification error: {e}")

        # Send Receipt Email
        EmailService.send_receipt(user, item, price)
            
        return Response({
            'success': True,
            'message': 'success.purchase_completed',
            'item_title': item_title,
            'balance': user.balance
        })
    
    @action(detail=False, methods=['get'])
    def balance(self, request):
        """Get teacher's wallet balance (for teacher dashboard)"""
        user = request.user
        
        if user.role != 'TEACHER':
            return Response({'error': 'Only teachers have wallets'}, status=status.HTTP_403_FORBIDDEN)
        
        from .services.wallet_service import WalletService
        from .serializers import TeacherWalletSerializer
        
        wallet = WalletService.get_or_create_wallet(user)
        serializer = TeacherWalletSerializer(wallet)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def transactions(self, request):
        """Get teacher transaction history"""
        user = request.user
        
        if user.role != 'TEACHER':
            return Response({'error': 'Only teachers can view transactions'}, status=status.HTTP_403_FORBIDDEN)
        
        from .models import Transaction
        from .serializers import TransactionSerializer
        
        transactions = Transaction.objects.filter(user=user).order_by('-created_at')[:50]
        serializer = TransactionSerializer(transactions, many=True)
        return Response(serializer.data)


class LevelRewardViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Get rewards list for levels.
    """
    queryset = LevelReward.objects.all()
    serializer_class = LevelRewardSerializer
    permission_classes = [AllowAny]


class StreakViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def status(self, request):
        """Get current user streak status"""
        streak = StreakService.get_user_streak(request.user)
        return Response({
            'current_streak': streak.current_streak,
            'max_streak': streak.max_streak,
            'last_activity': streak.last_activity_date,
            'freeze_count': streak.freeze_count,
            'is_active_today': streak.last_activity_date == timezone.localdate()
        })

    @action(detail=False, methods=['post'], url_path='buy-freeze')
    def buy_freeze(self, request):
        """Buy a streak freeze for 500 ArdCoins"""
        user = request.user
        price = 500
        
        if user.balance < price:
            return Response({
                'success': False,
                'error': 'Mablag\' yetarli emas'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Deduct balance
        user.balance -= price
        user.save()
        
        # Add freeze
        streak = StreakService.get_user_streak(user)
        streak.freeze_count += 1
        streak.save()
        
        return Response({
            'success': True,
            'message': 'Streak Freeze sotib olindi',
            'freeze_count': streak.freeze_count,
            'new_balance': user.balance
        })


class GamificationViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """Aggregate data for Gamification Dashboard 3.0"""
        user = request.user
        
        # 1. Streak Info
        from .streak_service import StreakService
        streak_data = StreakService.get_user_streak(user)
        
        # 2. Daily Mission (Logic: Pick first unfinished lesson of first active course)
        mission = None
        enrollment = Enrollment.objects.filter(user=user, completed_at__isnull=True).order_by('-created_at').first()
        if not enrollment:
             enrollment = Enrollment.objects.filter(user=user, completed_at__isnull=True).first()
             
        if enrollment:
            # Find next lesson
            current_lesson_order = int(enrollment.course.lessons_count * (float(enrollment.progress) / 100))
            if current_lesson_order == 0: current_lesson_order = 1
            
            next_lesson = Lesson.objects.filter(course=enrollment.course, order__gte=current_lesson_order).first()
            if next_lesson:
                mission = {
                    'type': 'LESSON',
                    'title': next_lesson.title,
                    'subtitle': enrollment.course.title,
                    'duration': f"{next_lesson.video_duration // 60} daqiqa" if next_lesson.video_duration else "15 daqiqa",
                    'xp_reward': next_lesson.xp_amount,
                    'link': f"/course/{enrollment.course.id}/lesson/{next_lesson.id}",
                    # User request: Task should not stop. Always show next lesson as available.
                    'is_completed': False, 
                    'is_streak_saved': streak_data.is_active_today
                }
        
        if not mission:
            # Check if user has any enrollments at all
            has_enrollments = Enrollment.objects.filter(user=user).exists()
            mission = {
                'type': 'GENERIC',
                'title': "dashboard.mission.today",
                'subtitle': "dashboard.mission.enroll_course" if not has_enrollments else "dashboard.mission.any_lesson",
                'duration': "15 daqiqa",
                'xp_reward': 20,
                'link': "/my-courses" if has_enrollments else "/courses",
                'is_completed': streak_data.is_active_today
            }

        # 3. Calendar (Last 7 days)
        today = timezone.localdate()
        week_data = []
        for i in range(6, -1, -1):
            date = today - timedelta(days=i)
            has_activity = ActivityLog.objects.filter(user=user, created_at__date=date).exists()
            status = 'COMPLETED' if has_activity else 'MISSED'
            if date == today and not has_activity:
                status = 'PENDING'
            
            week_data.append({
                'day': date.strftime("%a"),
                'date': date.strftime("%d.%m"),
                'status': status
            })

        # 4. Enrolled Courses Progress
        enrolled_courses = []
        for enr in user.enrollments.all().select_related('course'):
            # Calculate XP earned in this course
            course_xp = LessonProgress.objects.filter(
                user=user, 
                lesson__course=enr.course, 
                is_completed=True
            ).aggregate(Sum('lesson__xp_amount'))['lesson__xp_amount__sum'] or 0
            
            if enr.completed_at:
                course_xp += enr.course.xp_reward

            enrolled_courses.append({
                'id': enr.course.id,
                'title': enr.course.title,
                'thumbnail': enr.course.thumbnail.url if enr.course.thumbnail else None,
                'progress': float(enr.progress),
                'xp_earned': course_xp,
                'total_xp_available': (enr.course.lessons.aggregate(Sum('xp_amount'))['xp_amount__sum'] or 0) + enr.course.xp_reward
            })

        # 5. Subject Stats
        subject_stats = []
        # Filter subjects that have at least one course OR at least one olympiad
        all_subjects = Subject.objects.filter(is_active=True).annotate(
            courses_count=Count('courses', filter=Q(courses__is_active=True)),
            olympiads_count=Count('olympiads_api', filter=Q(olympiads_api__is_active=True, olympiads_api__status__in=['UPCOMING', 'ONGOING']))
        ).filter(Q(courses_count__gt=0) | Q(olympiads_count__gt=0))
        
        for subj in all_subjects:
            # XP from lessons in this subject
            lesson_xp = LessonProgress.objects.filter(
                user=user, 
                lesson__course__subject=subj, 
                is_completed=True
            ).aggregate(Sum('lesson__xp_amount'))['lesson__xp_amount__sum'] or 0
            
            # XP from olympiads in this subject
            olympiad_xp = 0
            for res in TestResult.objects.filter(user=user, olympiad__subject_id=subj, status='COMPLETED'):
                olympiad_xp += int(res.score * 2)
                if res.percentage >= 70:
                    olympiad_xp += 20
            
            # Added bonus if user completed a course in this subject
            course_completion_xp = Enrollment.objects.filter(
                user=user, 
                course__subject=subj, 
                completed_at__isnull=False
            ).aggregate(Sum('course__xp_reward'))['course__xp_reward__sum'] or 0

            subject_stats.append({
                'id': subj.id,
                'name': subj.name,
                'icon': subj.icon,
                'color': subj.color,
                'courses_count': subj.courses_count,
                'olympiads_count': subj.olympiads_count,
                'xp_earned': lesson_xp + olympiad_xp + course_completion_xp
            })

        # 6. Active Profession Roadmap
        active_prof = UserProfessionProgress.objects.filter(user=user).select_related('profession').first()
        profession_data = None
        if active_prof:
            profession_data = {
                'id': active_prof.profession.id,
                'name': active_prof.profession.name,
                'progress': float(active_prof.progress_percent),
                'roadmap_steps': [
                    {
                        'id': step.id,
                        'title': step.title,
                        'type': step.step_type,
                        'is_completed': False # Need more logic to check if course/test is done
                    } for step in active_prof.profession.roadmap_steps.all()[:5]
                ]
            }

        # Check if user has active courses
        has_active_courses = len(enrolled_courses) > 0
        
        # Recommended courses, subjects, and professions for empty state
        recommended_courses = []
        featured_subjects = []
        featured_professions = []

        if not has_active_courses:
            from .serializers import CourseSerializer, SubjectSerializer, ProfessionSerializer
            
            # Courses
            courses = Course.objects.filter(
                is_active=True,
                is_featured=True
            ).select_related('subject').order_by('-created_at')[:3]
            recommended_courses = CourseSerializer(courses, many=True).data

            # Subjects
            subjects = Subject.objects.filter(is_active=True, is_featured=True).order_by('order')[:4]
            featured_subjects = SubjectSerializer(subjects, many=True).data

            # Professions
            professions = Profession.objects.filter(is_active=True).order_by('?')[:3]
            featured_professions = ProfessionSerializer(professions, many=True).data

        return Response({
            'success': True,
            'has_active_courses': has_active_courses,
            'recommended_courses': recommended_courses,
            'featured_subjects': featured_subjects,
            'featured_professions': featured_professions,
            'hero': {
                'user_name': user.first_name or user.username,
                'balance': float(user.balance),
                'ranking': user.ranking,
                'certificates_count': user.certificates_count,
                'title': f"{streak_data.current_streak}",
                'subtitle': "dashboard.streak.warning_msg" if not streak_data.is_active_today else "dashboard.streak.saved_msg",
                'streak_count': streak_data.current_streak,
                'is_danger': not streak_data.is_active_today and streak_data.time_since_last > 20, 
                'hours_left': streak_data.seconds_until_reset // 3600,
                'seconds_until_reset': streak_data.seconds_until_reset,
                'is_active_today': streak_data.is_active_today,
                'last_activity': streak_data.last_activity_date
            },
            'mission': mission,
            'calendar': week_data,
            'level': user.level_progress,
            'enrolled_courses': enrolled_courses,
            'subject_stats': subject_stats,
            'active_profession': profession_data,
            'telegram': {
                'is_connected': bool(user.telegram_id),
                'bot_username': "@ardent_olimpiada_bot"
            }
        })


# ============= HOMEPAGE CMS VIEWS =============

class HomePageViewSet(viewsets.ViewSet):
    """
    Homepage Configuration ViewSet
    """
    permission_classes = [AllowAny]
    
    def get_permissions(self):
        if self.action in ['update_config', 'update_stats']:
            return [IsAuthenticated(), IsAdmin()]
        return [AllowAny()]

    @action(detail=False, methods=['get'])
    def get_config(self, request):
        """Get homepage configuration"""
        config = HomePageConfig.objects.first()
        if not config:
            config = HomePageConfig.objects.create()
        return Response({
            'success': True,
            'config': HomePageConfigSerializer(config).data
        })

    @action(detail=False, methods=['get'])
    def hero(self, request):
        """Get hero section data for landing page"""
        config = HomePageConfig.objects.first()
        if not config:
            config = HomePageConfig.objects.create()
        # Return as list as expected by frontend mock
        return Response([{
            'id': config.id,
            'title_uz': config.hero_title,
            'title_ru': config.hero_title,
            'subtitle_uz': config.hero_subtitle,
            'subtitle_ru': config.hero_subtitle,
            'button_text_uz': config.hero_button_text,
            'button_text_ru': config.hero_button_text,
            'button_link': config.hero_button_link,
            'background_image': config.hero_image.url if config.hero_image else None,
            'is_active': True
        }])

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get homepage stats"""
        stats = HomeStat.objects.filter(is_active=True)
        return Response(HomeStatSerializer(stats, many=True).data)

    @action(detail=False, methods=['get'])
    def winners(self, request):
        """Get featured winners (flat list)"""
        winners = Winner.objects.all()[:10]
        return Response(WinnerSerializer(winners, many=True).data)

    @action(detail=False, methods=['get'], url_path='pride-results')
    def pride_results(self, request):
        """Get grouped olympiad results for Pride Carousel"""
        # Get last 5 completed olympiads
        completed = Olympiad.objects.filter(status='COMPLETED', is_active=True).order_by('-end_date')[:5]
        data = []
        for o in completed:
            # Get top 3 results
            top_results = TestResult.objects.filter(olympiad=o).order_by('-score')[:3]
            winners = []
            for i, r in enumerate(top_results):
                winners.append({
                    'id': r.id,
                    'rank': i + 1,
                    'student_name': r.user.get_full_name() or r.user.username,
                    'region': r.user.region or "O'zbekiston",
                    'score': r.score,
                    'max_score': o.questions.count()
                })
            
            # If no real test results yet, skip or use mock winners if exists
            if not winners:
                continue

            data.append({
                'id': o.id,
                'title': o.title,
                'subject': o.subject,
                'date': o.end_date.strftime("%Y-%m-%d"),
                'stage': "Respublika",
                'participants_count': o.registrations.count(),
                'winners': winners
            })
        
        # If no completed olympiads with results, return empty or sample
        return Response(data)

    @action(detail=False, methods=['get'], url_path='upcoming-olympiads')
    def upcoming_olympiads(self, request):
        """Get upcoming and ongoing olympiads for homepage"""
        olympiads = Olympiad.objects.filter(status__in=['UPCOMING', 'ONGOING'], is_active=True).order_by('start_date')[:6]
        return Response(OlympiadSerializer(olympiads, many=True, context={'request': request}).data)

    @action(detail=False, methods=['get'], url_path='featured-courses')
    def featured_courses(self, request):
        """Get featured courses for homepage"""
        courses = Course.objects.filter(is_featured=True, status='APPROVED', is_active=True).order_by('home_order')[:6]
        return Response(CourseSerializer(courses, many=True, context={'request': request}).data)

    @action(detail=False, methods=['get'])
    def professions(self, request):
        """Get professions for carousel"""
        professions = Profession.objects.filter(is_active=True).order_by('order')[:8]
        data = []
        for p in professions:
            data.append({
                'id': p.id,
                'name_uz': p.name,
                'name_ru': p.name,
                'salary': "5,000,000 - 15,000,000",
                'courses_count': p.enrollments.count() if hasattr(p, 'enrollments') else 0,
                'roadmap_link': f"/profession/{p.id}",
                'icon': p.icon
            })
        return Response(data)

    @action(detail=False, methods=['get'])
    def testimonials(self, request):
        """Get testimonials for carousel"""
        testimonials = Testimonial.objects.filter(is_active=True)
        return Response(TestimonialSerializer(testimonials, many=True).data)

    @action(detail=False, methods=['get'])
    def mentors(self, request):
        """Get mentors for teachers section (Only approved ones with profiles)"""
        mentors = User.objects.filter(
            role='TEACHER', 
            teacher_profile__verification_status='APPROVED'
        ).select_related('teacher_profile').annotate(
            total_students=Sum('courses__students_count')
        ).order_by('?')[:8]
        
        data = []
        for m in mentors:
            tp = getattr(m, 'teacher_profile', None)
            
            # Use data from profile if available, otherwise fallbacks
            pos = tp.specialization if tp and tp.specialization else "O'qituvchi"
            exp = tp.experience_years if tp else 5
            students = m.total_students or 0
            bio = tp.bio if tp else ""
            soc = {
                'telegram': tp.telegram_username if tp else '',
                'linkedin': tp.linkedin_profile if tp else '',
                'instagram': tp.instagram_username if tp else ''
            }

            data.append({
                'id': m.id,
                'name': m.get_full_name() or m.username,
                'position': pos,
                'company': "Hogwords Mentor", # Branding updated
                'experience': exp,
                'students_count': students,
                'bio_uz': bio,
                'bio_ru': bio,
                'social_links': soc,
                'image': m.avatar.url if (m.avatar and hasattr(m.avatar, 'url')) else "https://github.com/shadcn.png"
            })
        return Response(data)

    @action(detail=False, methods=['get'], url_path='mentors/(?P<mentor_id>[^/.]+)')
    def mentor_detail(self, request, mentor_id=None):
        """Get detailed info for a single mentor"""
        mentor = get_object_or_404(User, id=mentor_id, role='TEACHER')
        tp = getattr(mentor, 'teacher_profile', None)
        
        pos = tp.specialization if tp and tp.specialization else "O'qituvchi"
        exp = tp.experience_years if tp else 5
        students = mentor.courses.aggregate(total=Sum('students_count'))['total'] or 0
        bio = tp.bio if tp else ""
        soc = {
            'telegram': tp.telegram_username if tp else '',
            'linkedin': tp.linkedin_profile if tp else '',
            'instagram': tp.instagram_username if tp else ''
        }

        return Response({
            'id': mentor.id,
            'name': mentor.get_full_name() or mentor.username,
            'position': pos,
            'company': "Hogwords Mentor",
            'experience': exp,
            'students_count': students,
            'bio_uz': bio,
            'bio_ru': bio,
            'social_links': soc,
            'image': mentor.avatar.url if (mentor.avatar and hasattr(mentor.avatar, 'url')) else "https://github.com/shadcn.png"
        })
    
    @action(detail=False, methods=['get'], url_path='featured-subjects')
    def featured_subjects(self, request):
        """Get featured subjects for interactive grid"""
        subjects = Subject.objects.filter(is_active=True, is_featured=True).order_by('order')[:6]
        return Response(SubjectSerializer(subjects, many=True, context={'request': request}).data)
    
    @action(detail=False, methods=['post', 'put'])
    def update_config(self, request):
        """Update homepage configuration (Admin)"""
        config = HomePageConfig.objects.first()
        if not config:
            config = HomePageConfig.objects.create()
            
        serializer = HomePageConfigSerializer(config, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Bosh sahifa sozlamalari yangilandi',
                'config': serializer.data
            })
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)




class BannerViewSet(viewsets.ModelViewSet):
    """
    CRUD for Homepage Banners
    """
    queryset = Banner.objects.all().order_by('order', '-created_at')
    serializer_class = BannerSerializer
    permission_classes = [IsOwnerOrAdmin] # Actually should be Admin only for write, AllowAny for read?
    # No, usually CMS is public read, admin write.
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAdmin()]


class TestimonialViewSet(viewsets.ModelViewSet):
    """
    CRUD for Testimonials
    """
    queryset = Testimonial.objects.all().order_by('-created_at')
    serializer_class = TestimonialSerializer
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAdmin()]


class HomeStatViewSet(viewsets.ModelViewSet):
    """Manage Homepage Stats"""
    queryset = HomeStat.objects.all()
    serializer_class = HomeStatSerializer
    permission_classes = [AllowAny]
    pagination_class = None
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsAdmin()]
        return [AllowAny()]


class HomeStepViewSet(viewsets.ModelViewSet):
    """Manage How It Works Steps"""
    queryset = HomeStep.objects.all()
    serializer_class = HomeStepSerializer
    permission_classes = [AllowAny]
    pagination_class = None

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsAdmin()]
        return [AllowAny()]


class HomeAdvantageViewSet(viewsets.ModelViewSet):
    """Manage Advantages/Trust Items"""
    queryset = HomeAdvantage.objects.all()
    serializer_class = HomeAdvantageSerializer
    permission_classes = [AllowAny]
    pagination_class = None
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsAdmin()]
        return [AllowAny()]


class FreeCourseSectionViewSet(viewsets.ModelViewSet):
    """Manage Free Course Section CMS"""
    queryset = FreeCourseSection.objects.all()
    serializer_class = FreeCourseSectionSerializer
    permission_classes = [AllowAny]
    pagination_class = None
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsAdmin()]
        return [AllowAny()]


class FreeCourseLessonCardViewSet(viewsets.ModelViewSet):
    """Manage Free Course Lesson Cards"""
    queryset = FreeCourseLessonCard.objects.filter(is_active=True)
    serializer_class = FreeCourseLessonCardSerializer
    permission_classes = [AllowAny]
    pagination_class = None
    
    def get_queryset(self):
        # For admin actions, show all cards
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return FreeCourseLessonCard.objects.all()
        # For public, only show active cards
        return FreeCourseLessonCard.objects.filter(is_active=True)
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsAdmin()]
        return [AllowAny()]



class SubjectViewSet(viewsets.ModelViewSet):
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer
    permission_classes = [AllowAny]
    lookup_field = 'slug'
    
    def get_queryset(self):
        queryset = Subject.objects.all().annotate(
            active_courses_count=Count('courses', filter=Q(courses__is_active=True)),
            active_olympiads_count=Count('olympiads_api', filter=Q(olympiads_api__is_active=True, olympiads_api__status__in=['UPCOMING', 'ONGOING']))
        )
        # Only show active subjects for non-admin users
        if not (self.request.user.is_authenticated and self.request.user.role == 'ADMIN'):
            queryset = queryset.filter(is_active=True)
            # Filter out subjects with no courses AND no olympiads
            queryset = queryset.filter(Q(active_courses_count__gt=0) | Q(active_olympiads_count__gt=0))
            
        if self.request.query_params.get('featured'):
            queryset = queryset.filter(is_featured=True)
        return queryset
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return SubjectDetailSerializer
        return SubjectSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsAdmin()]
        return [AllowAny()]
    
    def get_object(self):
        """Allow lookup by ID or slug"""
        lookup = self.kwargs.get('slug')
        if lookup and lookup.isdigit():
            return Subject.objects.get(id=int(lookup))
        return super().get_object()


class TeacherViewSet(viewsets.ViewSet):
    """
    Teacher Portal Endpoints
    """
    permission_classes = [IsTeacherOrAdmin]

    def get_permissions(self):
        if self.action in ['students', 'courses', 'stats']:
            return [IsAuthenticated()]
        return [IsTeacherOrAdmin()]

    @action(detail=False, methods=['get'])
    def stats(self, request):
        user = request.user
        
        # Ensure user is teacher (permission handles role check generally, but for safety)
        if user.role not in ['TEACHER', 'ADMIN']:
             return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)

        # 1. Total Students (Unique students enrolled in teacher's courses/co-taught courses)
        courses = Course.objects.filter(Q(teacher=user) | Q(teachers=user)).distinct()
        students_count = Enrollment.objects.filter(course__in=courses).values('user').distinct().count()

        # 2. Active Courses
        active_courses_count = courses.filter(is_active=True).count()
        
        # 3. Average Rating
        avg_rating = courses.aggregate(avg=Avg('rating'))['avg'] or 5.0

        # 4. Total Lessons Taught (or just total lessons created)
        total_lessons = Lesson.objects.filter(course__in=courses).count()

        # 5. Average Score (Across all teacher's courses/olympiads)
        course_avg = Enrollment.objects.filter(course__in=courses).aggregate(avg=Avg('progress'))['avg'] or 0
        
        olympiads = Olympiad.objects.filter(teacher=user)
        oly_avg = TestResult.objects.filter(olympiad__in=olympiads, status='COMPLETED').aggregate(avg=Avg('percentage'))['avg'] or 0
        
        # Weighted average or simple average of both? Let's take simple average for now
        avg_score = (course_avg + float(oly_avg)) / 2 if (course_avg and oly_avg) else (course_avg or float(oly_avg))

        return Response({
            'students_count': students_count,
            'active_courses': active_courses_count,
            'rating': round(avg_rating, 1),
            'total_lessons': total_lessons,
            'avg_score': round(avg_score, 1)
        })

    @action(detail=False, methods=['get'])
    def students(self, request):
        """List unique students enrolled in teacher's courses with progress"""
        user = request.user
        courses = Course.objects.filter(Q(teacher=user) | Q(teachers=user)).distinct()
        enrollments = Enrollment.objects.filter(course__in=courses).select_related('user', 'course').order_by('-created_at')
        
        data = []
        seen = set()
        
        for enroll in enrollments:
            try:
                # Basic safety check to ensure enrollment has both user and course
                if not enroll.user or not enroll.course:
                    print(f"Skipping enrollment {enroll.id} due to missing user/course")
                    continue
                    
                data.append({
                    'id': enroll.id,
                    'student_id': enroll.user.id,
                    'student_name': enroll.user.get_full_name() or enroll.user.username,
                    'student_phone': enroll.user.phone,
                    'student_avatar': enroll.user.avatar.url if (enroll.user.avatar and hasattr(enroll.user.avatar, 'url')) else None,
                    'course_title': enroll.course.title,
                    'progress': enroll.progress,
                    'enrolled_at': enroll.created_at
                })
            except Exception as e:
                print(f"Error processing enrollment {enroll.id}: {e}")
                continue
            
        return Response({
            'count': len(data),
            'results': data
        })

    @action(detail=False, methods=['get'])
    def courses(self, request):
        """Get teacher's courses (management view)"""
        user = request.user
        if user.role == 'ADMIN':
             courses = Course.objects.all().order_by('-created_at')
        else:
             courses = Course.objects.filter(Q(teacher=user) | Q(teachers=user)).distinct().order_by('-created_at')
        
        serializer = CourseSerializer(courses, many=True)
        return Response({
            'count': courses.count(),
            'results': serializer.data
        })

    def retrieve(self, request, pk=None):
        """Get detailed course info for editing"""
        user = request.user
        if user.role == 'ADMIN':
            course = get_object_or_404(Course, pk=pk)
        else:
            course = get_object_or_404(Course, Q(teacher=user) | Q(teachers=user), pk=pk)
        
        serializer = TeacherCourseDetailSerializer(course)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def olympiads(self, request):
        """Get teacher's olympiads"""
        user = request.user
        if user.role == 'ADMIN':
             olympiads = Olympiad.objects.all().order_by('-created_at')
        else:
             olympiads = Olympiad.objects.filter(
                 Q(teacher=user) | Q(checker=user) | Q(moderator=user)
             ).distinct().order_by('-created_at')
        
        serializer = OlympiadSerializer(olympiads, many=True)
        return Response({
            'count': olympiads.count(),
            'results': serializer.data
        })

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated, IsAdmin])
    def set_teacher_type(self, request):
        """Admin: Set teacher type (NORMAL, VIP, INTERNAL)"""
        teacher_id = request.data.get('teacher_id')
        new_type = request.data.get('teacher_type')
        duration_days = request.data.get('duration_days')
        reason = request.data.get('reason', '')

        if not teacher_id or not new_type:
            return Response({'error': 'teacher_id va teacher_type kerak'}, status=status.HTTP_400_BAD_REQUEST)

        if new_type not in ['NORMAL', 'VIP', 'INTERNAL']:
            return Response({'error': "teacher_type faqat NORMAL, VIP yoki INTERNAL bo'lishi mumkin"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            teacher = User.objects.get(id=teacher_id, role='TEACHER')
        except User.DoesNotExist:
            return Response({'error': "O'qituvchi topilmadi"}, status=status.HTTP_404_NOT_FOUND)

        profile, _ = TeacherProfile.objects.get_or_create(user=teacher)
        prev_type = profile.teacher_type

        profile.teacher_type = new_type

        # Set expiration for VIP
        if new_type == 'VIP' and duration_days:
            profile.vip_expire_date = timezone.now() + timedelta(days=int(duration_days))
        elif new_type == 'INTERNAL':
            profile.vip_expire_date = None  # Internal never expires
        elif new_type == 'NORMAL':
            profile.vip_expire_date = None

        profile.save()

        # Log the change
        from .models import VIPLog
        VIPLog.objects.create(
            teacher=teacher,
            given_by=request.user,
            prev_type=prev_type,
            new_type=new_type,
            duration_days=int(duration_days) if duration_days else None,
            reason=reason
        )

        return Response({
            'success': True,
            'message': f"O'qituvchi statusi {prev_type} → {new_type} ga o'zgartirildi",
            'teacher_type': new_type,
            'vip_expire_date': profile.vip_expire_date
        })

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated, IsAdmin])
    def all_teachers(self, request):
        """Admin: List all teachers with their type/status"""
        teacher_type = request.query_params.get('type')
        teachers = User.objects.filter(role='TEACHER').order_by('-date_joined')
        
        if teacher_type:
            teachers = teachers.filter(teacher_profile__teacher_type=teacher_type)

        data = []
        for t in teachers:
            profile = getattr(t, 'teacher_profile', None)
            data.append({
                'id': t.id,
                'username': t.username,
                'full_name': t.get_full_name(),
                'phone': t.phone,
                'avatar': t.avatar.url if t.avatar else None,
                'teacher_type': profile.teacher_type if profile else 'NORMAL',
                'vip_expire_date': profile.vip_expire_date if profile else None,
                'verification_status': profile.verification_status if profile else 'PENDING',
                'courses_count': t.courses.count(),
                'students_count': Enrollment.objects.filter(course__teacher=t).values('user').distinct().count(),
                'date_joined': t.date_joined,
            })

        return Response({
            'count': len(data),
            'results': data
        })



# ============= NOTIFICATION VIEWSET =============

class NotificationViewSet(viewsets.ModelViewSet):
    """
    Manage User Notifications
    """
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        count = self.get_queryset().filter(is_read=False).count()
        return Response({'count': count})

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        self.get_queryset().filter(is_read=False).update(is_read=True)
        return Response({'success': True, 'message': 'All notifications marked as read'})

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({'success': True})

    @action(detail=False, methods=['post'], permission_classes=[IsAdminUser])
    def broadcast(self, request):
        """
        Send notification to multiple users.
        Body: {
            recipients: 'ALL' | 'STUDENTS' | 'TEACHERS' | [user_ids],
            title: str,
            message: str,
            type: str,
            channel: str
        }
        """
        data = request.data
        recipients = data.get('recipients')
        title = data.get('title')
        message = data.get('message')
        n_type = data.get('type', 'SYSTEM')
        channel = data.get('channel', 'WEB')
        link = data.get('link')

        if not title or not message:
            return Response({'error': 'Title and message are required'}, status=400)

        targets = []
        if recipients == 'ALL':
            targets = User.objects.filter(is_active=True)
        elif recipients == 'STUDENTS':
            targets = User.objects.filter(role='STUDENT', is_active=True)
        elif recipients == 'TEACHERS':
            targets = User.objects.filter(role='TEACHER', is_active=True)
        elif isinstance(recipients, list):
            targets = User.objects.filter(id__in=recipients)
        else:
             return Response({'error': 'Invalid recipients'}, status=400)

        count = 0
        from .services.notification_service import NotificationService
        
        for user in targets:
            NotificationService.create_notification(
                user=user,
                title=title,
                message=message,
                notification_type=n_type,
                channel=channel,
                link=link
            )
            count += 1

        return Response({'success': True, 'count': count})

class NotificationTemplateViewSet(viewsets.ModelViewSet):
    queryset = NotificationTemplate.objects.all().order_by('-created_at')
    serializer_class = NotificationTemplateSerializer
    permission_classes = [IsAdmin]

class NotificationBroadcastViewSet(viewsets.ModelViewSet):
    queryset = NotificationBroadcast.objects.all().order_by('-created_at')
    serializer_class = NotificationBroadcastSerializer
    permission_classes = [IsAdmin]

    @action(detail=True, methods=['post'])
    def trigger(self, request, pk=None):
        """Manually trigger a re-send or initial send of a broadcast"""
        from .services.notification_service import NotificationService
        broadcast = self.get_object()
        count = NotificationService.broadcast_notification(broadcast.id)
        return Response({
            'success': True,
            'count': count,
            'message': f'{count} nafar foydalanuvchiga yuborildi'
        })

    def perform_create(self, serializer):
        broadcast = serializer.save(created_by=self.request.user)
        # Auto-trigger if not scheduled for future
        if not broadcast.scheduled_at or broadcast.scheduled_at <= timezone.now():
            try:
                from .services.notification_service import NotificationService
                NotificationService.broadcast_notification(broadcast.id)
            except Exception as e:
                print(f"BROADCAST ERROR: {e}")
                # Update status to FAILED if triggering failed
                broadcast.status = 'FAILED' 
                broadcast.save(update_fields=['status'])


# ============= PROFESSION VIEWS =============

class ProfessionViewSet(viewsets.ModelViewSet):
    """
    API for Professions (Career Paths)
    """
    queryset = Profession.objects.filter(is_active=True)
    serializer_class = ProfessionSerializer
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAuthenticated()]

    @action(detail=True, methods=['POST'])
    def enroll(self, request, pk=None):
        """Enroll in a professional roadmap"""
        profession = self.get_object()
        progress, created = UserProfessionProgress.objects.get_or_create(
            user=request.user,
            profession=profession
        )
        # Recalculate progress right away
        self._recalculate_progress(request.user, profession, progress)
        return Response({
            'success': True,
            'message': 'Roadmapga muvaffaqiyatli qo\'shildingiz',
            'progress': UserProfessionProgressSerializer(progress).data
        })

    @action(detail=True, methods=['GET'])
    def progress(self, request, pk=None):
        """Get Career Engine progress for a profession"""
        profession = self.get_object()
        try:
            from .services.career_engine_service import CareerEngineService
            state = CareerEngineService.get_or_create_state(request.user, profession)
            data = {
                'total_xp': state.total_xp,
                'status': state.status,
                'current_level_id': state.current_level_id if state.current_level else None,
                'current_level_title': state.current_level.title if state.current_level else None,
            }
            return Response({'success': True, 'progress': data})
        except Exception as e:
            return Response({'success': False, 'message': str(e)}, status=400)

    @action(detail=True, methods=['POST'])
    def sync_builder(self, request, pk=None):
        """Sync the entire Career Engine graph (Levels & Nodes) from the Admin Builder"""
        from .models import ProfessionLevel, ProfessionNode
        from django.db import transaction
        
        profession = self.get_object()
        levels_data = request.data.get('levels', [])
        
        try:
            with transaction.atomic():
                # Keep track of active level IDs to delete removed ones
                active_level_ids = []
                
                for l_data in levels_data:
                    # Update or Create Level
                    if l_data.get('id'):
                        level = ProfessionLevel.objects.get(id=l_data['id'], profession=profession)
                        level.level_number = l_data.get('level_number', level.level_number)
                        level.title = l_data.get('title', level.title)
                        level.unlock_xp = l_data.get('unlock_xp', level.unlock_xp)
                        level.order = l_data.get('order', level.order)
                        level.is_prestige_only = l_data.get('is_prestige_only', level.is_prestige_only)
                        level.save()
                    else:
                        level = ProfessionLevel.objects.create(
                            profession=profession,
                            level_number=l_data.get('level_number', 1),
                            title=l_data.get('title', ''),
                            unlock_xp=l_data.get('unlock_xp', 0),
                            order=l_data.get('order', 0),
                            is_prestige_only=l_data.get('is_prestige_only', False)
                        )
                    active_level_ids.append(level.id)
                    
                    # Sync Nodes for this Level
                    active_node_ids = []
                    nodes_data = l_data.get('nodes', [])
                    
                    for n_data in nodes_data:
                        if n_data.get('id'):
                            node = ProfessionNode.objects.get(id=n_data['id'], level=level)
                            node.title = n_data.get('title', node.title)
                            node.node_type = n_data.get('node_type', node.node_type)
                            node.reference_id = n_data.get('reference_id', node.reference_id)
                            node.is_required = n_data.get('is_required', node.is_required)
                            node.xp_reward = n_data.get('xp_reward', node.xp_reward)
                            node.unlock_condition = n_data.get('unlock_condition', node.unlock_condition)
                            node.order = n_data.get('order', node.order)
                            node.save()
                        else:
                            node = ProfessionNode.objects.create(
                                level=level,
                                title=n_data.get('title', ''),
                                node_type=n_data.get('node_type', 'course'),
                                reference_id=n_data.get('reference_id', None),
                                is_required=n_data.get('is_required', True),
                                xp_reward=n_data.get('xp_reward', 0),
                                unlock_condition=n_data.get('unlock_condition', None),
                                order=n_data.get('order', 0)
                            )
                        active_node_ids.append(node.id)
                        
                    # Delete removed nodes in this level
                    level.nodes.exclude(id__in=active_node_ids).delete()
                    
                # Delete removed levels in this profession
                profession.levels.exclude(id__in=active_level_ids).delete()
                
            return Response({'success': True, 'message': 'Graph synchronized successfully.'})
        except Exception as e:
            return Response({'success': False, 'message': str(e)}, status=400)

    @action(detail=False, methods=['POST'], url_path='node/(?P<node_id>[^/.]+)/complete')
    def complete_node(self, request, node_id=None):
        """Complete a specific Career Engine node"""
        from .models import ProfessionNode
        from .services.career_engine_service import CareerEngineService
        from django.shortcuts import get_object_or_404
        
        node = get_object_or_404(ProfessionNode, id=node_id)
        score = request.data.get('score', 0)
        
        try:
            progress, _ = CareerEngineService.complete_node(request.user, node, score=int(score))
            return Response({
                'success': True,
                'message': 'Tugun yakunlandi va XP qo\'shildi!',
            })
        except ValueError as e:
            return Response({'success': False, 'message': str(e)}, status=400)
        except Exception as e:
            return Response({'success': False, 'message': 'Xatolik yuz berdi'}, status=500)

    def _recalculate_progress(self, user, profession, progress_item=None):
        """Helper to calculate % of mandatory courses completed in this roadmap"""
        if not progress_item:
            progress_item = UserProfessionProgress.objects.filter(user=user, profession=profession).first()
        
        if not progress_item:
            return 0
            
        mandatory_steps = profession.roadmap_steps.filter(is_mandatory=True, course__isnull=False)
        total_mandatory = mandatory_steps.count()
        
        if total_mandatory == 0:
            progress_item.progress_percent = 100
            progress_item.status = 'COMPLETED'
            progress_item.save()
            return 100
            
        completed_count = 0
        for step in mandatory_steps:
            if Enrollment.objects.filter(user=user, course=step.course, progress__gte=100).exists():
                completed_count += 1
                
        percent = int((completed_count / total_mandatory) * 100)
        progress_item.progress_percent = percent
        if percent == 100:
            progress_item.status = 'COMPLETED'
        progress_item.save()
        return percent



class TestResultViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API for retrieving test results
    """
    serializer_class = TestResultSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return TestResult.objects.filter(user=self.request.user).order_by('-submitted_at')


class LeadViewSet(viewsets.ModelViewSet):
    """
    Handle Leads from Landing Page.
    Public can create (POST).
    Only Admin can list/view (GET).
    """
    queryset = Lead.objects.all()
    serializer_class = LeadSerializer
    
    def get_permissions(self):
        if self.action == 'create':
            permission_classes = [AllowAny]
        else:
            permission_classes = [IsAdminUser]
        return [permission() for permission in permission_classes]
    
    def perform_create(self, serializer):
        """Override to send notifications when lead is created"""
        lead = serializer.save()
        
        # Send Telegram notification to admin
        try:
            from .bot_service import BotService
            BotService.notify_new_lead(lead)
        except Exception as e:
            print(f"Error sending telegram notification for lead: {e}")
        
        # Create in-app notification for all admins
        try:
            admin_users = User.objects.filter(role='ADMIN')
            for admin in admin_users:
                Notification.objects.create(
                    user=admin,
                    title='Yangi murojaat',
                    message=f'{lead.name} ({lead.phone}) bog\'lanish uchun murojaat qildi.',
                    type='INFO',
                    link=f'/admin/leads'
                )
        except Exception as e:
            print(f"Error creating admin notification for lead: {e}")



# ============= ADMIN DASHBOARD VIEWS =============

class AdminDashboardViewSet(viewsets.ViewSet):
    """
    Admin Dashboard Analytics Endpoints
    """
    permission_classes = [IsAuthenticated, IsAdmin]

    @action(detail=False, methods=['get'])
    def overview(self, request):
        """
        Comprehensive dashboard overview for Admin
        GET /api/admin/dashboard/overview/
        """
        today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        month_start = today.replace(day=1)
        
        # 1. KPIs
        kpis = {
            'total_users': User.objects.count(),
            'teachers_count': User.objects.filter(role='TEACHER').count(),
            'active_courses': Course.objects.filter(status='APPROVED').count(),
            'active_olympiads': Olympiad.objects.filter(status__in=['UPCOMING', 'ONGOING']).count(),
            'revenue_today': float(Payment.objects.filter(status='COMPLETED', completed_at__gte=today).aggregate(sum=Sum('amount'))['sum'] or 0),
            'revenue_month': float(Payment.objects.filter(status='COMPLETED', completed_at__gte=month_start).aggregate(sum=Sum('amount'))['sum'] or 0),
            'new_users_today': User.objects.filter(date_joined__gte=today).count(),
        }
        
        # 2. Alerts (Attention Required)
        alerts = {
            'pending_courses': Course.objects.filter(status='PENDING').count(),
            'pending_certificates': Certificate.objects.filter(status='PENDING').count(),
            'open_tickets': SupportTicket.objects.filter(status='OPEN').count(),
        }
        
        # 3. Activity Feed (Merged)
        # We'll take latest 5 of each type and merge
        activities = []
        
        # Recent Registrations
        for u in User.objects.order_by('-date_joined')[:5]:
            activities.append({
                'type': 'USER_JOIN',
                'title': f"Yangi foydalanuvchi: {u.get_full_name() or u.username}",
                'subtitle': u.email or u.phone,
                'time': u.date_joined,
                'icon': 'UserPlus'
            })
            
        # Recent Payments
        for p in Payment.objects.filter(status='COMPLETED').select_related('user').order_by('-completed_at')[:5]:
            activities.append({
                'type': 'PAYMENT',
                'title': f"To'lov muvaffaqiyatli: {p.amount:,.0f} so'm",
                'subtitle': f"{p.user.username} - {p.type}",
                'time': p.completed_at or p.created_at, # Fallback to created_at
                'icon': 'CreditCard'
            })
            
        # Recent Olympiad Registrations
        for reg in OlympiadRegistration.objects.select_related('user', 'olympiad').order_by('-registered_at')[:5]:
            activities.append({
                'type': 'OLYMPIAD_REG',
                'title': f"Olimpiadaga ro'yxatdan o'tdi",
                'subtitle': f"{reg.user.username} -> {reg.olympiad.title}",
                'time': reg.registered_at,
                'icon': 'Trophy'
            })

        # Sort all by time desc (handle None safely)
        activities.sort(key=lambda x: x['time'] or timezone.now(), reverse=True)
        activities = activities[:15] # Keep top 15 total

        return Response({
            'success': True,
            'kpis': kpis,
            'alerts': alerts,
            'activities': activities
        })

    @action(detail=False, methods=['get'])
    def chart(self, request):
        """
        Get chart data
        GET /api/admin/dashboard/chart/
        """
        # 1. User Growth & Revenue (Last 6 months)
        current_date = timezone.now()
        chart_data = []
        
        for i in range(5, -1, -1):
            date = current_date - timedelta(days=i*30) 
            month_start = date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            # Simple next month calculation
            if month_start.month == 12:
                next_month_start = month_start.replace(year=month_start.year + 1, month=1)
            else:
                next_month_start = month_start.replace(month=month_start.month + 1)
            
            # Count users joined in this month
            users_count = User.objects.filter(
                date_joined__gte=month_start, 
                date_joined__lt=next_month_start
            ).count()
            
            # Sum revenue for this month
            revenue_sum = Payment.objects.filter(
                status='COMPLETED',
                created_at__gte=month_start,
                created_at__lt=next_month_start
            ).aggregate(sum=Sum('amount'))['sum'] or 0
            
            chart_data.append({
                'name': month_start.strftime("%b").lower(), # jan, feb, etc.
                'users': users_count,
                'revenue': float(revenue_sum)
            })
            
        return Response({
            'success': True,
            'chart_data': chart_data
        })

class AIAssistantFAQViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Hogwords AI (Smart FAQ Assistant)
    """
    queryset = AIAssistantFAQ.objects.all()
    serializer_class = AIAssistantFAQSerializer
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'query', 'rate']:
            return [AllowAny()]
        return [IsAuthenticated(), IsAdmin()]

    def get_queryset(self):
        queryset = AIAssistantFAQ.objects.all()
        
        # Non-admins only see active ones
        user = self.request.user
        is_admin = user.is_authenticated and user.role == 'ADMIN'
        
        if not is_admin:
            queryset = queryset.filter(is_active=True)
            
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category.upper())
            
        return queryset

    @action(detail=False, methods=['POST'], permission_classes=[AllowAny])
    def query(self, request):
        from .services.ai_service import AIService
        data = request.data
        question = data.get('question')
        session_id = data.get('session_id')
        context_url = data.get('context_url')
        language = data.get('language', 'uz')

        if not question:
            return Response({'error': 'Question is required'}, status=400)

        conv = AIService.get_or_create_conversation(
            user=request.user if request.user.is_authenticated else None,
            session_id=session_id,
            context_url=context_url
        )

        response = AIService.process_query(conv, question, language)
        return Response(response)

    @action(detail=False, methods=['POST'], permission_classes=[AllowAny])
    def rate(self, request):
        from .services.ai_service import AIService
        message_id = request.data.get('message_id')
        rating = request.data.get('rating')
        feedback = request.data.get('feedback')

        if AIService.rate_response(message_id, rating, feedback):
            return Response({'success': True})
        return Response({'success': False}, status=400)

class AIConversationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AIConversation.objects.all().prefetch_related('messages')
    serializer_class = AIConversationSerializer
    permission_classes = [IsAdmin]

class AIUnansweredQuestionViewSet(viewsets.ModelViewSet):
    queryset = AIUnansweredQuestion.objects.all()
    serializer_class = AIUnansweredQuestionSerializer
    permission_classes = [IsAdmin]


# ============= PUBLIC STATISTICS API =============

@api_view(['GET'])
@permission_classes([AllowAny])
def public_statistics(request):
    """
    Public statistics for home page
    GET /api/stats/public/
    """
    try:
        total_users = User.objects.filter(is_active=True).count()
        active_courses = Course.objects.filter(status='APPROVED', is_active=True).count()
        active_olympiads = Olympiad.objects.filter(
            Q(status='UPCOMING') | Q(status='ONGOING')
        ).count()
        certificates_issued = Certificate.objects.count()
        
        # Success rate (average of all test results)
        avg_score = TestResult.objects.aggregate(Avg('score'))['score__avg'] or 0
        
        return Response({
            'success': True,
            'stats': {
                'total_users': total_users,
                'active_courses': active_courses,
                'active_olympiads': active_olympiads,
                'certificates_issued': certificates_issued,
                'success_rate': round(avg_score, 1)
            }
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def featured_courses(request):
    """
    Get featured courses for home page
    GET /api/courses/featured/
    """
    try:
        courses = Course.objects.filter(
            status='APPROVED',
            is_featured=True
        ).select_related('teacher', 'subject')[:6]
        
        serializer = CourseSerializer(courses, many=True, context={'request': request})
        return Response({
            'success': True,
            'courses': serializer.data
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def upcoming_olympiads(request):
    """
    Get upcoming olympiads for home page
    GET /api/olympiads/upcoming/
    """
    try:
        olympiads = Olympiad.objects.filter(
            status__in=['UPCOMING', 'ONGOING', 'PUBLISHED'],
            is_active=True
        ).select_related('subject_id').order_by('start_date')[:8]
        
        serializer = OlympiadSerializer(olympiads, many=True, context={'request': request})
        return Response({
            'success': True,
            'olympiads': serializer.data
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class QuestionViewSet(viewsets.ModelViewSet):
    """
    Question API for Admins (CRUD)
    """
    queryset = Question.objects.all()
    serializer_class = QuestionAdminSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get_queryset(self):
        return super().get_queryset()

    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({
                'success': False,
                'error': str(e),
                'detail': traceback.format_exc(),
                'request_data': self.request.data  # Return payload for debugging
            }, status=status.HTTP_400_BAD_REQUEST)


class PayoutViewSet(viewsets.ModelViewSet):
    """
    Teacher Payout Management
    """
    queryset = Payout.objects.all()
    serializer_class = PayoutSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'ADMIN' or user.is_staff:
            return Payout.objects.all()
        return Payout.objects.filter(teacher=user)

    def perform_create(self, serializer):
        user = self.request.user
        if user.role != 'TEACHER':
            raise ValidationError({"detail": "Faqat o'qituvchilar pul yechish so'rovini yubora olishadi."})
        
        amount = serializer.validated_data.get('amount')
        wallet, created = TeacherWallet.objects.get_or_create(teacher=user)
        
        if wallet.balance < amount:
            raise ValidationError({"detail": "Balansda yetarli mablag' mavjud emas."})
            
        if amount < 100000:
            raise ValidationError({"detail": "Minimal yechib olish miqdori 100,000 so'm."})
            
        # Deduct from wallet immediately
        wallet.balance -= amount
        wallet.save()
        
        serializer.save(teacher=user, status='REQUESTED')

    @action(detail=True, methods=['post'], permission_classes=[IsAdmin])
    def approve(self, request, pk=None):
        payout = self.get_object()
        if payout.status != 'REQUESTED':
            return Response({'error': 'Ushbu so\'rov allaqachon ko\'rib chiqilgan'}, status=400)
            
        payout.status = 'APPROVED'
        payout.approved_by = request.user
        payout.approved_at = timezone.now()
        payout.save()
        
        return Response({'success': True, 'message': 'So\'rov tasdiqlandi'})

    @action(detail=True, methods=['post'], permission_classes=[IsAdmin])
    def mark_paid(self, request, pk=None):
        payout = self.get_object()
        if payout.status != 'APPROVED':
            return Response({'error': 'Avval so\'rovni tasdiqlash kerak'}, status=400)
            
        payout.status = 'PAID'
        payout.paid_at = timezone.now()
        payout.save()
        
        # Log Transaction
        Transaction.objects.create(
            transaction_type='PAYOUT',
            user=payout.teacher,
            amount=payout.amount,
            status='SUCCESS',
            description=f"Yechib olish yakunlandi: {payout.id}",
            metadata={'payout_id': payout.id}
        )
        
        # Total withdrawn update
        wallet = TeacherWallet.objects.filter(teacher=payout.teacher).first()
        if wallet:
            wallet.total_withdrawn += payout.amount
            wallet.save()
            
        return Response({'success': True, 'message': 'To\'lov yakunlandi'})


class LessonContentViewSet(viewsets.ModelViewSet):
    """
    Teacher Content Editor (Text, Files)
    """
    queryset = LessonContent.objects.all()
    serializer_class = LessonContentSerializer
    permission_classes = [IsAuthenticated, IsTeacherOrAdmin]
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class HomeworkViewSet(viewsets.ModelViewSet):
    """
    Teacher Homework Management
    """
    queryset = Homework.objects.all()
    serializer_class = HomeworkSerializer
    permission_classes = [IsAuthenticated, IsTeacherOrAdmin]


class HomeworkSubmissionViewSet(viewsets.ModelViewSet):
    """
    Student Homework Submissions
    """
    queryset = HomeworkSubmission.objects.all()
    serializer_class = HomeworkSubmissionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'STUDENT':
            return HomeworkSubmission.objects.filter(student=user)
        if user.role == 'TEACHER':
            return HomeworkSubmission.objects.filter(homework__lesson__course__teacher=user)
        return HomeworkSubmission.objects.all()
        
    def perform_create(self, serializer):
        serializer.save(student=self.request.user)

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated, IsAdmin])
def manage_commission_settings(request):
    """
    Get or Update Global Commission Settings
    GET /api/admin/settings/commissions/
    POST /api/admin/settings/commissions/ 
    Body: { "default_commission": 30, "vip_commission": 20, "internal_commission": 10 }
    """
    from .models import CommissionSettings
    settings = CommissionSettings.load()
    
    if request.method == 'GET':
        return Response({
            'default_commission': float(settings.default_commission),
            'vip_commission': float(settings.vip_commission),
            'internal_commission': float(settings.internal_commission)
        })
        
    elif request.method == 'POST':
        if 'default_commission' in request.data:
            settings.default_commission = request.data['default_commission']
        if 'vip_commission' in request.data:
            settings.vip_commission = request.data['vip_commission']
        if 'internal_commission' in request.data:
            settings.internal_commission = request.data['internal_commission']
            
        settings.save()
        return Response({
            'success': True,
            'message': 'Komissiya sozlamalari yangilandi',
            'data': {
                'default_commission': float(settings.default_commission),
                'vip_commission': float(settings.vip_commission),
                'internal_commission': float(settings.internal_commission)
            }
        })
