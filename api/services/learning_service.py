from django.utils import timezone
from api.models import (
    Course, Module, Lesson, LessonProgress, 
    Enrollment, LessonPractice, LessonTest, User,
    Certificate
)
from api.utils import generate_unique_id
from rest_framework.exceptions import ValidationError
from django.db.models import Prefetch

class LearningService:
    @staticmethod
    def get_course_learning_state(user, course_id):
        """
        Calculates the complete learning state for a user in a course,
        including which lessons are locked and their progress.
        """
        try:
            enrollment = Enrollment.objects.get(user=user, course_id=course_id)
        except Enrollment.DoesNotExist:
            # Guest/Preview Mode
            course = Course.objects.get(id=course_id)
            # Create a temporary unsaved enrollment object for frontend compatibility
            enrollment = Enrollment(
                user=user, 
                course=course, 
                progress=0,
                created_at=timezone.now(),
                updated_at=timezone.now()
            )
            
        # Prefetch lessons with their progress for this specific user
        progress_prefetch = Prefetch(
            'lessons__user_progress',
            queryset=LessonProgress.objects.filter(user=user),
            to_attr='my_progress'
        )

        modules = Module.objects.filter(course_id=course_id).prefetch_related(
            progress_prefetch
        ).order_by('order')

        course = enrollment.course if enrollment.id else Course.objects.get(id=course_id)
        lock_strategy = course.lock_strategy

        # Flatten lessons and link progress
        flat_lessons = []
        for m in modules:
            for l in m.lessons.all():
                # Attach module info for convenience
                l.module_title = m.title
                
                # Get user progress for this lesson
                progress = getattr(l, 'my_progress', [])
                l.progress_data = progress[0] if progress else None
                flat_lessons.append(l)

        # Iterate and set is_locked based on strategy
        is_enrolled = enrollment.id is not None
        previous_completed = True # Helper for sequential strategy

        # Build a map for fast lookup of completion status
        completion_map = {l.id: (l.progress_data.is_completed if l.progress_data else False) for l in flat_lessons}

        for lesson in flat_lessons:
            if not is_enrolled:
                # Guest mode: Lock everything except free lessons
                lesson.is_locked = not lesson.is_free
            else:
                # Enrolled mode: apply lock strategy
                if lock_strategy == 'free':
                    lesson.is_locked = False
                
                elif lock_strategy == 'sequential':
                    # Sequential: lock if previous lesson is not completed
                    lesson.is_locked = not previous_completed
                
                elif lock_strategy == 'custom':
                    # Custom: use required_lesson field and is_locked flag
                    if lesson.is_locked:
                        if lesson.required_lesson_id:
                            # Use completion map to check required lesson
                            lesson.is_locked = not completion_map.get(lesson.required_lesson_id, False)
                        else:
                            # is_locked is True but no specific required_lesson? 
                            # Interpret as "locked by some unspecified rule", maybe teacher manually unlocks? 
                            # For now, if is_locked=True but no required_lesson, we keep it locked.
                            pass
                    else:
                        # is_locked is False in custom mode
                        lesson.is_locked = False
                
                # Special cases: free lessons are ALWAYS unlocked
                if lesson.is_free:
                    lesson.is_locked = False

                # Update state for next iteration (used by sequential)
                is_completed = completion_map.get(lesson.id, False)
                previous_completed = is_completed

        return {
            "enrollment": enrollment,
            "modules": modules,
            "flat_lessons": flat_lessons
        }

    @staticmethod
    def set_current_lesson(user, course_id, lesson_id):
        """Update the current lesson for an enrollment"""
        try:
            enrollment = Enrollment.objects.get(user=user, course_id=course_id)
            lesson = Lesson.objects.get(id=lesson_id, course_id=course_id)
            enrollment.current_lesson = lesson
            enrollment.save(update_fields=['current_lesson'])
            return enrollment
        except (Enrollment.DoesNotExist, Lesson.DoesNotExist):
            return None

    @staticmethod
    def update_lesson_progress(user, lesson_id, update_type, data=None):
        """
        Updates specific parts of lesson progress (video, practice, test).
        """
        lesson = Lesson.objects.get(id=lesson_id)
        
        # Check enrollment
        if not Enrollment.objects.filter(user=user, course=lesson.course).exists():
            raise ValidationError("Not enrolled")

        progress, created = LessonProgress.objects.get_or_create(
            user=user,
            lesson=lesson
        )

        if update_type == 'VIDEO_COMPLETE':
            progress.is_video_watched = True
            progress.video_last_position = data.get('position', 0) if data else 0
        
        elif update_type == 'SUBMIT_PRACTICE':
            # Handle practice logic
            try:
                practice = lesson.practice
                user_answer = data.get('answer', '')
                progress.practice_submission = user_answer
                
                # Simple auto-check for now if correct_answer is provided
                if practice.correct_answer and user_answer.strip().lower() == practice.correct_answer.strip().lower():
                    progress.practice_score = practice.points
                else:
                    # If no correct_answer or mismatch, maybe it needs teacher review?
                    # For now, mark as 0 or pending.
                    progress.practice_score = 0
            except LessonPractice.DoesNotExist:
                pass

        elif update_type == 'SUBMIT_TEST':
            # Handle test grading (similar to OlympiadService)
            try:
                test = lesson.test
                answers = data.get('answers', {}) # {question_id: value}
                score = 0
                total_q = test.questions.count()
                
                for q in test.questions.all():
                    user_val = answers.get(str(q.id))
                    if str(user_val) == str(q.correct_answer):
                        score += 1
                
                percentage = round((score / total_q * 100), 2) if total_q > 0 else 0
                progress.test_score = int(percentage)
                progress.test_attempts += 1
            except LessonTest.DoesNotExist:
                pass

        # Check if lesson is now fully complete
        LearningService._check_and_finalize_lesson(user, lesson, progress)
        
        progress.save()
        return progress

    @staticmethod
    def _check_and_finalize_lesson(user, lesson, progress):
        """
        Internal logic to determine if a lesson is finished.
        Rule: Video must be watched. If Practice exists, must be attempted (or passed).
        If Test exists, must pass min_pass_score.
        """
        has_practice = hasattr(lesson, 'practice')
        has_test = hasattr(lesson, 'test')
        
        video_done = progress.is_video_watched
        practice_done = True if not has_practice else (progress.practice_score is not None)
        test_done = True
        
        if has_test:
            test = lesson.test
            # Score must exist and be >= min_pass_score
            test_done = (progress.test_score is not None and progress.test_score >= test.min_pass_score)
        
        if video_done and practice_done and test_done:
            if not progress.is_completed:
                progress.is_completed = True
                progress.completed_at = timezone.now()
                
                # Update Streak
                from api.streak_service import StreakService
                StreakService.record_activity(user, 'LESSON_COMPLETE', f"Completed lesson: {lesson.title}")
                
                # Reward Lesson XP
                if lesson.xp_amount > 0:
                    user.add_xp(lesson.xp_amount, 'LESSON_COMPLETE', f"Dars yakunlandi: {lesson.title}")
                
                # Update Enrollment overall progress
                LearningService.update_enrollment_stats(user, lesson.course)
                
                # Check for Module Completion
                if lesson.module:
                    LearningService.check_module_completion(user, lesson.module)

    @staticmethod
    def check_module_completion(user, module):
        """Check if all published lessons in a module are completed by the user"""
        total_lessons = Lesson.objects.filter(module=module, is_published=True).count()
        completed_lessons = LessonProgress.objects.filter(
            user=user, 
            lesson__module=module, 
            is_completed=True
        ).count()
        
        if total_lessons > 0 and completed_lessons >= total_lessons:
            # All lessons completed - check if already rewarded? 
            # We can use ActivityLog to prevent double reward or just check if it's the first time
            # For simplicity, we can log it. 
            # Better: add a ModuleCompletion model or just check ActivityLog
            from api.models import ActivityLog
            if not ActivityLog.objects.filter(user=user, activity_type='MODULE_COMPLETE', description__contains=f"Module ID: {module.id}").exists():
                user.add_xp(module.xp_reward, 'MODULE_COMPLETE', f"Modul yakunlandi: {module.title} (Module ID: {module.id})")

    @staticmethod
    def update_enrollment_stats(user, course):
        """Recalculate total course progress % for an enrollment"""
        total_lessons = Lesson.objects.filter(course=course, is_published=True).count()
        completed_lessons = LessonProgress.objects.filter(
            user=user, 
            lesson__course=course, 
            is_completed=True
        ).count()
        
        progress_pct = (completed_lessons / total_lessons * 100) if total_lessons > 0 else 0
        
        enrollment = Enrollment.objects.get(user=user, course=course)
        enrollment.progress = progress_pct
        
        # Use course threshold (default 80%) for completion trigger
        threshold = getattr(course, 'completion_min_progress', 80)
        
        # PRO UPGRADE: Check Final Exam if it exists
        final_exam_passed = True
        final_test = LessonTest.objects.filter(lesson__course=course, is_final=True).first()
        if final_test:
            final_progress = LessonProgress.objects.filter(user=user, lesson=final_test.lesson).first()
            required_score = getattr(course, 'required_final_score', 70)
            if not final_progress or final_progress.test_score is None or final_progress.test_score < required_score:
                final_exam_passed = False

        if progress_pct >= threshold and final_exam_passed and not enrollment.completed_at:
            enrollment.completed_at = timezone.now()
            # Reward XP for course completion
            user.add_xp(course.xp_reward, 'COURSE_ENROLL', f"Kurs yakunlandi: {course.title}")
            
            # Update Career Progress
            from api.services.profession_service import ProfessionService
            ProfessionService.update_all_active_professions(user)
            
            # 🚀 HOGWORDS CAREER ENGINE HOOK: Auto-complete Course Nodes
            try:
                from api.models import ProfessionNode, UserProfessionState
                from api.services.career_engine_service import CareerEngineService
                
                # Get all active profession states for the user
                active_states = UserProfessionState.objects.filter(user=user, status='active')
                for state in active_states:
                    if state.current_level:
                        # Find if there's a course node in the current level for this course
                        nodes = state.current_level.nodes.filter(
                            node_type='course', 
                            reference_id=course.id
                        )
                        for node in nodes:
                            try:
                                CareerEngineService.complete_node(user, node, score=100)
                            except Exception as e:
                                print(f"CareerEngine Error completing course node: {e}")
            except Exception as e:
                print(f"CareerEngine Error: {e}")
            
            # Create certificate if not already exists AND it's enabled for course
            if course.is_certificate_enabled and not Certificate.objects.filter(user=user, course=course).exists():
                from api.utils import generate_unique_id
                cert_number = generate_unique_id('CRT')
                
                # Calculate average score for certificate
                from django.db.models import Avg
                avg_score = LessonProgress.objects.filter(
                    user=user, 
                    lesson__course=course, 
                    test_score__isnull=False
                ).aggregate(avg=Avg('test_score'))['avg'] or 0

                Certificate.objects.create(
                    cert_number=cert_number,
                    user=user,
                    course=course,
                    grade=f"{int(avg_score)}%",
                    score=int(avg_score),
                    status='PENDING' 
                )
            
            # Send notification to student
            from api.models import Notification
            Notification.objects.create(
                user=user,
                title="Tabriklaymiz! 🎓",
                message=f"Siz '{course.title}' kursini muvaffaqiyatli yakunladingiz! Bilimlaringizni amalda qo'llashda omad tilaymiz.",
                notification_type='ACHIEVEMENT',
                channel='ALL',
                link=f"/course/{course.id}"
            )
            
        enrollment.save()
