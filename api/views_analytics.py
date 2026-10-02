from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from django.db.models import Sum, Count
from django.db.models.functions import TruncDate
from django.utils import timezone
from datetime import timedelta
from .models import Payment, Course, Olympiad

class AnalyticsViewSet(viewsets.ViewSet):
    permission_classes = [IsAdminUser]

    @action(detail=False, methods=['get'], url_path='finance-trend')
    def finance_trend(self, request):
        """
        Get income trend for the last N days.
        Query Params: ?days=7 (default) or 30
        """
        days_param = request.query_params.get('days', 7)
        try:
            days = int(days_param)
        except:
            days = 7
        
        start_date = timezone.now().date() - timedelta(days=days-1) # Include today
        
        # Aggregate payments by date
        # Filter: status='COMPLETED'
        trends = Payment.objects.filter(
            status='COMPLETED', 
            created_at__date__gte=start_date
        ).annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            income=Sum('amount')
        ).order_by('date')
        
        # Fill missing days with 0
        trend_dict = {t['date']: t['income'] or 0 for t in trends}
        result_data = []
        
        for i in range(days):
            date = start_date + timedelta(days=i)
            # Format: 'Jan 15'
            name = date.strftime('%b %d') 
            income = trend_dict.get(date, 0)
            result_data.append({
                'name': name,
                'income': float(income) # Ensure float
            })
            
        return Response(result_data)

    @action(detail=False, methods=['get'], url_path='top-products')
    def top_products(self, request):
        """
        Get top 5 products by revenue.
        Strategy: Group Payments by 'reference_id' and 'type'.
        """
        # Filter COMPLETED payments of type COURSE, OLYMPIAD only
        payments = Payment.objects.filter(
            status='COMPLETED',
            reference_id__isnull=False,
            type__in=['COURSE', 'OLYMPIAD']
        ).exclude(reference_id='')
        
        # 1. Aggregate grouping by reference_id and type
        stats = payments.values('type', 'reference_id').annotate(
            revenue=Sum('amount'),
            count=Count('id')
        ).order_by('-revenue')[:5]
        
        result_data = []
        
        for item in stats:
            p_type = item['type'] # 'COURSE', 'OLYMPIAD'
            ref_id = item['reference_id']
            revenue = item['revenue'] or 0
            
            name = f"#{ref_id} {p_type}"
            color = "#cbd5e1" # default slate-300
            
            p_id = 0
            try:
                p_id = int(ref_id)
            except:
                pass

            if p_type == 'COURSE' and p_id:
                course = Course.objects.filter(id=p_id).first()
                if course:
                    name = course.title
                    color = "#3b82f6" # blue
            elif p_type == 'OLYMPIAD' and p_id:
                olympiad = Olympiad.objects.filter(id=p_id).first()
                if olympiad:
                    name = olympiad.title
                    color = "#8b5cf6" # purple
            
            result_data.append({
                'name': name,
                'revenue': float(revenue), # Ensure float
                'color': color
            })
            
        return Response(result_data)
