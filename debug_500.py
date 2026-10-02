"""
Debug script to reproduce and get the full traceback for the 500 error
on /api/olympiads/ endpoint.
"""
import os, sys, django, traceback

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from api.models import Olympiad
from api.serializers import OlympiadSerializer
from rest_framework.test import APIRequestFactory
from rest_framework.request import Request

factory = APIRequestFactory()
raw_request = factory.get('/api/olympiads/')

# Wrap in DRF Request with AnonymousUser
from django.contrib.auth.models import AnonymousUser
raw_request.user = AnonymousUser()
drf_request = Request(raw_request)

print(f"=== Testing OlympiadSerializer with {Olympiad.objects.filter(is_active=True).count()} olympiads ===\n")

# Test each olympiad individually first
for oly in Olympiad.objects.filter(is_active=True):
    try:
        serializer = OlympiadSerializer(oly, context={'request': drf_request})
        data = serializer.data
        print(f"  OK: id={oly.id} title={oly.title}")
    except Exception as e:
        print(f"\n  FAIL: id={oly.id} title={oly.title}")
        print(f"  Error: {e}")
        traceback.print_exc()
        print()

# Now test the full queryset (pagination)
print("\n=== Testing full queryset serialization ===")
try:
    qs = Olympiad.objects.filter(is_active=True)
    serializer = OlympiadSerializer(qs, many=True, context={'request': drf_request})
    data = serializer.data
    print(f"  OK: Serialized {len(data)} olympiads successfully")
except Exception as e:
    print(f"\n  FAIL: {e}")
    traceback.print_exc()

# Also test the viewset list action
print("\n=== Testing OlympiadViewSet.list() ===")
try:
    from api.views import OlympiadViewSet
    from rest_framework.test import force_authenticate

    view = OlympiadViewSet.as_view({'get': 'list'})
    request = factory.get('/api/olympiads/')
    response = view(request)
    response.render()
    print(f"  Status: {response.status_code}")
    if response.status_code >= 400:
        print(f"  Response: {response.content[:500]}")
except Exception as e:
    print(f"\n  FAIL: {e}")
    traceback.print_exc()
