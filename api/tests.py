from django.test import TestCase, override_settings
from django.utils import timezone
from api.models import User, Olympiad, TestResult, TeacherProfile
from rest_framework.test import APIClient
import datetime


@override_settings(SECURE_SSL_REDIRECT=False)
class OlympiadVisibilityTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='student', password='testpassword', role='STUDENT')
        self.teacher = User.objects.create_user(username='teacher', password='testpassword', role='TEACHER')
        self.olympiad = Olympiad.objects.create(
            title="Test Olympiad",
            subject="Math",
            start_date=timezone.now(),
            end_date=timezone.now() + datetime.timedelta(days=1),
            status='ONGOING',
            teacher=self.teacher,
            duration=60
        )
        # Create a result
        self.result = TestResult.objects.create(
            user=self.user,
            olympiad=self.olympiad,
            score=90,
            status='COMPLETED'
        )

    def test_leaderboard_locked_when_ongoing(self):
        """Leaderboard should be empty when status is ONGOING for student"""
        response = self.client.get(f'/api/olympiads/{self.olympiad.id}/leaderboard/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'ONGOING')
        self.assertEqual(len(response.data['leaderboard']), 0)

    def test_leaderboard_visible_when_published(self):
        """Leaderboard should be visible when status is PUBLISHED"""
        self.olympiad.status = 'PUBLISHED'
        self.olympiad.save()
        
        response = self.client.get(f'/api/olympiads/{self.olympiad.id}/leaderboard/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'PUBLISHED')
        self.assertGreater(len(response.data['leaderboard']), 0)
        self.assertEqual(response.data['leaderboard'][0]['student'], 'student')

    def test_teacher_can_see_leaderboard_anytime(self):
        """Teacher should see leaderboard even if not published"""
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get(f'/api/olympiads/{self.olympiad.id}/leaderboard/')
        self.assertEqual(response.status_code, 200)
        self.assertGreater(len(response.data['leaderboard']), 0)


@override_settings(SECURE_SSL_REDIRECT=False)
class TeacherVerificationFlowTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.student = User.objects.create_user(username='student2', password='testpassword', role='STUDENT')
        self.teacher = User.objects.create_user(username='teacher2', password='testpassword', role='TEACHER')
        self.admin = User.objects.create_user(username='admin1', password='testpassword', role='ADMIN')
        TeacherProfile.objects.create(user=self.teacher, bio='Bio', specialization='Math')

    def test_student_cannot_self_approve_teacher_role(self):
        self.client.force_authenticate(user=self.student)
        response = self.client.post('/api/users/me/verify_teacher/', {'status': 'APPROVED'}, format='json')

        self.assertEqual(response.status_code, 403)
        self.student.refresh_from_db()
        self.assertEqual(self.student.role, 'STUDENT')

    def test_teacher_can_submit_pending_for_self(self):
        self.client.force_authenticate(user=self.teacher)
        response = self.client.post('/api/users/me/verify_teacher/', {'status': 'PENDING'}, format='json')

        self.assertEqual(response.status_code, 200)
        self.teacher.refresh_from_db()
        self.assertEqual(self.teacher.role, 'TEACHER')
        self.assertEqual(self.teacher.teacher_profile.verification_status, 'PENDING')

    def test_teacher_cannot_change_other_user_verification(self):
        self.client.force_authenticate(user=self.teacher)
        response = self.client.post(f'/api/users/{self.student.id}/verify_teacher/', {'status': 'APPROVED'}, format='json')

        self.assertEqual(response.status_code, 403)
        self.student.refresh_from_db()
        self.assertEqual(self.student.role, 'STUDENT')

    def test_admin_can_approve_teacher_without_staff_access(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(f'/api/users/{self.teacher.id}/verify_teacher/', {'status': 'APPROVED'}, format='json')

        self.assertEqual(response.status_code, 200)
        self.teacher.refresh_from_db()
        self.assertEqual(self.teacher.role, 'TEACHER')
        self.assertFalse(self.teacher.is_staff)
        self.assertEqual(self.teacher.teacher_profile.verification_status, 'APPROVED')
