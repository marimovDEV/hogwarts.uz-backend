from rest_framework import permissions

class IsAdmin(permissions.BasePermission):
    """
    Allows access only to admin users.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'ADMIN')


class IsTeacher(permissions.BasePermission):
    """
    Allows access to teachers.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'TEACHER')


class IsTeacherOrAdmin(permissions.BasePermission):
    """
    Allows access to teachers or admins.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.role in ['ADMIN', 'TEACHER']


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Object-level permission to only allow owners of an object to edit it.
    Assumes the model instance has an `owner` attribute or `teacher` attribute.
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        # if request.method in permissions.SAFE_METHODS:
        #     return True

        if request.user.role == 'ADMIN':
            return True

        # Check for 'teacher' field
        if hasattr(obj, 'teacher'):
            return obj.teacher == request.user
            
        # Check for 'user' field (e.g., Profile)
        if hasattr(obj, 'user'):
            return obj.user == request.user
            
        return False


class HasCourseAccess(permissions.BasePermission):
    """
    Checks if the user has access to a course (purchased, teacher, or admin).
    """
    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        
        if user.role == 'ADMIN' or user.is_staff:
            return True
            
        # Get course from object
        course = None
        if hasattr(obj, 'course'):
            course = obj.course
        elif hasattr(obj, 'lesson'):
            course = obj.lesson.course
        elif hasattr(obj, 'homework'):
            course = obj.homework.lesson.course
        elif hasattr(obj, 'module'):
            course = obj.module.course
        elif hasattr(obj, 'lesson_tests'): # Special for TestResult/Submission
             # Check if it has a reference to course
             course = getattr(obj, 'course', None)
        
        # If obj is Course itself
        from .models import Course
        if isinstance(obj, Course):
            course = obj
            
        if not course:
            return True # Fallback if no course context
            
        # Teachers see their own courses
        if user.role == 'TEACHER' and course.teacher == user:
            return True
            
        # Check if student is enrolled
        from .models import Enrollment
        return Enrollment.objects.filter(user=user, course=course).exists()
