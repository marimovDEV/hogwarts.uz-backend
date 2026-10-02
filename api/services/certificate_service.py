import random
import string
from datetime import timezone
from ..models import Certificate, TestResult, Olympiad

class CertificateService:
    @staticmethod
    def generate_cert_number():
        """Generate a unique certificate number (e.g. ARD-2026-X7Y2-9ABC)"""
        import datetime
        year = datetime.datetime.now().year
        suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        return f"ARD-{year}-{suffix[:4]}-{suffix[4:]}"

    @classmethod
    def issue_olympiad_certificates(cls, olympiad_id):
        """Issue certificates to all qualified participants (>70%)"""
        olympiad = Olympiad.objects.get(id=olympiad_id)
        results = TestResult.objects.filter(olympiad=olympiad, status='COMPLETED', percentage__gte=70)
        
        issued_count = 0
        for result in results:
            # Check if already has a certificate for this olympiad
            if Certificate.objects.filter(user=result.user, olympiad=olympiad).exists():
                continue
            
            # Determine grade
            if result.percentage >= 90:
                grade = 'GOLD'
            elif result.percentage >= 80:
                grade = 'SILVER'
            else:
                grade = 'BRONZE'
                
            Certificate.objects.create(
                cert_number=cls.generate_cert_number(),
                user=result.user,
                olympiad=olympiad,
                grade=grade,
                status='VERIFIED'
            )
            issued_count += 1
            
        return issued_count
