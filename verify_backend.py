import os
import django
from rest_framework.test import APIClient
from api.models import User, Course, Module

# Setup
client = APIClient()

# Get or Create Admin User
admin_user, created = User.objects.get_or_create(username='admin_verifier', role='ADMIN')
if created:
    admin_user.set_password('admin123')
    admin_user.save()
client.force_authenticate(user=admin_user)

print("--- Starting Backend Flow Verification ---")

# 1. Create Course
print("\n[1] Creating Course...")
create_data = {
    "title": "Backend Verification Course",
    "description": "Testing the API flow directly.",
    "subject": 1, # Provided Matematika exists
    "level": "BEGINNER",
    "price": 0,
    "language": "en"
}
response = client.post('/api/courses/', create_data)
if response.status_code == 201:
    course_id = response.data['course']['id']
    print(f"✅ Course Created: ID {course_id}")
else:
    print(f"❌ Creation Failed: {response.status_code} - {response.data}")
    exit(1)

# 2. Fetch Course Details (Testing CourseDetailSerializer fix)
print("\n[2] Fetching Course Details...")
response = client.get(f'/api/courses/{course_id}/')
if response.status_code == 200:
    print("✅ Course Details Fetched (NO 500 Error)")
    if 'status_display' in response.data:
        print("✅ field 'status_display' is present")
    else:
        print("❌ field 'status_display' MISSING")
else:
    print(f"❌ Details Fetch Failed: {response.status_code} - {response.data}")
    exit(1)

# 3. Add Module (Testing ModuleSerializer fix)
print("\n[3] Adding Module...")
module_data = {
    "course": course_id,
    "title": "Verification Module",
    "order": 1
}
response = client.post('/api/modules/', module_data)
if response.status_code == 201:
    print("✅ Module Added")
else:
    print(f"❌ Module Add Failed: {response.status_code} - {response.data}")
    exit(1)

# 4. Update Status to PENDING (Testing Wizard Step 3 logic)
print("\n[4] Updating Status to PENDING...")
update_data = {
    "title": "Backend Verification Course", # Required for PUT
    "description": "Testing the API flow directly.", # Required for PUT
    "status": "PENDING",
    "is_active": False # Wizard keeps it inactive usually
}
response = client.put(f'/api/courses/{course_id}/', update_data)
if response.status_code == 200:
    course = Course.objects.get(id=course_id)
    if course.status == 'PENDING':
        print("✅ Status Updated to PENDING")
    else:
        print(f"❌ Status Update Failed: Status is {course.status}")
        exit(1)
else:
    print(f"❌ Update Failed: {response.status_code} - {response.data}")
    exit(1)

# 5. Approve Course
print("\n[5] Approving Course...")
response = client.post(f'/api/courses/{course_id}/approve/')
if response.status_code == 200:
    course.refresh_from_db()
    if course.status == 'APPROVED':
        print("✅ Course Approved Successfully!")
    else:
        print(f"❌ Approval Failed: Status is {course.status}")
else:
    print(f"❌ Approve Request Failed: {response.status_code} - {response.data}")
    exit(1)

# Cleanup
print("\n[6] Cleanup...")
Course.objects.get(id=course_id).delete()
print("✅ Test Course Deleted")
