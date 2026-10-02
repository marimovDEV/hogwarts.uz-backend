from django_filters import rest_framework as filters
from .models import Course, Olympiad, Certificate, SupportTicket, User, Payment


class CourseFilter(filters.FilterSet):
    """Filter for courses"""
    title = filters.CharFilter(lookup_expr='icontains')
    subject = filters.CharFilter(lookup_expr='iexact')
    level = filters.ChoiceFilter(choices=Course.LEVEL_CHOICES)
    min_price = filters.NumberFilter(field_name='price', lookup_expr='gte')
    max_price = filters.NumberFilter(field_name='price', lookup_expr='lte')
    is_featured = filters.BooleanFilter()
    min_rating = filters.NumberFilter(field_name='rating', lookup_expr='gte')
    
    class Meta:
        model = Course
        fields = ['title', 'subject', 'level', 'is_featured']


class OlympiadFilter(filters.FilterSet):
    """Filter for olympiads"""
    title = filters.CharFilter(lookup_expr='icontains')
    subject = filters.CharFilter(lookup_expr='iexact')
    status = filters.ChoiceFilter(choices=Olympiad.STATUS_CHOICES)
    start_date_after = filters.DateTimeFilter(field_name='start_date', lookup_expr='gte')
    start_date_before = filters.DateTimeFilter(field_name='start_date', lookup_expr='lte')
    
    class Meta:
        model = Olympiad
        fields = ['title', 'subject', 'status']


class CertificateFilter(filters.FilterSet):
    """Filter for certificates"""
    status = filters.ChoiceFilter(choices=Certificate.STATUS_CHOICES)
    cert_number = filters.CharFilter(lookup_expr='icontains')
    user_name = filters.CharFilter(field_name='user__username', lookup_expr='icontains')
    issued_after = filters.DateTimeFilter(field_name='issued_at', lookup_expr='gte')
    issued_before = filters.DateTimeFilter(field_name='issued_at', lookup_expr='lte')
    
    class Meta:
        model = Certificate
        fields = ['status', 'cert_number']


class SupportTicketFilter(filters.FilterSet):
    """Filter for support tickets"""
    status = filters.ChoiceFilter(choices=SupportTicket.STATUS_CHOICES)
    priority = filters.ChoiceFilter(choices=SupportTicket.PRIORITY_CHOICES)
    category = filters.CharFilter(lookup_expr='iexact')
    ticket_number = filters.CharFilter(lookup_expr='icontains')
    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    
    class Meta:
        model = SupportTicket
        fields = ['status', 'priority', 'category', 'ticket_number']


class UserFilter(filters.FilterSet):
    """Filter for users (admin)"""
    username = filters.CharFilter(lookup_expr='icontains')
    email = filters.CharFilter(lookup_expr='icontains')
    role = filters.ChoiceFilter(choices=User.ROLE_CHOICES)
    is_active = filters.BooleanFilter()
    joined_after = filters.DateTimeFilter(field_name='date_joined', lookup_expr='gte')
    joined_before = filters.DateTimeFilter(field_name='date_joined', lookup_expr='lte')
    
    class Meta:
        model = User
        fields = ['username', 'email', 'role', 'is_active']


class PaymentFilter(filters.FilterSet):
    """Filter for payments"""
    status = filters.ChoiceFilter(choices=Payment.STATUS_CHOICES)
    type = filters.CharFilter(lookup_expr='iexact')
    method = filters.CharFilter(lookup_expr='iexact')
    min_amount = filters.NumberFilter(field_name='amount', lookup_expr='gte')
    max_amount = filters.NumberFilter(field_name='amount', lookup_expr='lte')
    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    
    class Meta:
        model = Payment
        fields = ['status', 'type', 'method']
