"""
Certificate PDF Generator - Kreativ Dizayn
Generates beautiful, professional certificates with QR codes
"""
import os
import io
import qrcode
from datetime import datetime
from django.conf import settings
from django.core.files.base import ContentFile

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import cm, mm
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader


class CertificateGenerator:
    """Generate professional PDF certificates with QR verification"""
    
    # Certificate dimensions (A4 Landscape)
    PAGE_WIDTH, PAGE_HEIGHT = landscape(A4)
    
    # Premium Colors
    PRIMARY_COLOR = colors.HexColor('#2E1065')  # Deep Indigo
    SECONDARY_COLOR = colors.HexColor('#4338CA')  # Indigo
    ACCENT_COLOR = colors.HexColor('#7C3AED')    # Purple
    GOLD_COLOR = colors.HexColor('#D97706')     # Rich Amber/Gold
    TEXT_COLOR = colors.HexColor('#111827')     # Nero / Dark gray
    LIGHT_TEXT = colors.HexColor('#4B5563')     # Slate gray
    BORDER_COLOR = colors.HexColor('#E5E7EB')   # Light border
    
    def __init__(self, certificate):
        self.cert = certificate
        self.buffer = io.BytesIO()
        self.c = canvas.Canvas(self.buffer, pagesize=landscape(A4))
        
    def generate(self):
        """Generate the full certificate PDF"""
        self._draw_background()
        self._draw_border()
        self._draw_header()
        self._draw_recipient()
        self._draw_course_info()
        self._draw_grade()
        self._draw_qr_code()
        self._draw_footer()
        self._draw_signatures()
        
        self.c.save()
        self.buffer.seek(0)
        return self.buffer
    
    def _draw_background(self):
        """Draw sophisticated background with decorative elements"""
        c = self.c
        
        # Subtle parchment-like background
        c.setFillColor(colors.HexColor('#FCFDFE'))
        c.rect(0, 0, self.PAGE_WIDTH, self.PAGE_HEIGHT, fill=True, stroke=False)
        
        # Decorative abstract shapes (high-end look)
        c.setStrokeAlpha(0.04)
        c.setFillColor(self.ACCENT_COLOR)
        c.setFillAlpha(0.03)
        
        # Top-left large circle
        c.circle(0, self.PAGE_HEIGHT, 300, fill=True, stroke=True)
        # Bottom-right large circle
        c.circle(self.PAGE_WIDTH, 0, 250, fill=True, stroke=True)
        
        # Reset alphas
        c.setStrokeAlpha(1.0)
        c.setFillAlpha(1.0)
        
    def _draw_border(self):
        """Draw elegant multi-line border"""
        c = self.c
        margin = 30
        
        # Outer Gold Border
        c.setStrokeColor(self.GOLD_COLOR)
        c.setLineWidth(2.5)
        c.roundRect(margin, margin, self.PAGE_WIDTH - 2*margin, self.PAGE_HEIGHT - 2*margin, 20)
        
        # Inner thin Indigo Border
        c.setStrokeColor(self.SECONDARY_COLOR)
        c.setLineWidth(0.5)
        c.roundRect(margin + 8, margin + 8, self.PAGE_WIDTH - 2*margin - 16, self.PAGE_HEIGHT - 2*margin - 16, 15)
        
    def _draw_header(self):
        """Draw certificate header"""
        c = self.c
        center_x = self.PAGE_WIDTH / 2
        
        # Elegant Logo (Shield-like)
        c.setFillColor(self.ACCENT_COLOR)
        # Draw a pentagon-like shield shape
        path = c.beginPath()
        path.moveTo(center_x, self.PAGE_HEIGHT - 60)
        path.lineTo(center_x + 25, self.PAGE_HEIGHT - 75)
        path.lineTo(center_x + 20, self.PAGE_HEIGHT - 110)
        path.lineTo(center_x - 20, self.PAGE_HEIGHT - 110)
        path.lineTo(center_x - 25, self.PAGE_HEIGHT - 75)
        path.close()
        c.drawPath(path, fill=True, stroke=False)
        
        # "A" letter in shield
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 30)
        c.drawCentredString(center_x, self.PAGE_HEIGHT - 100, "A")
        
        # Platform name - Sized properly
        c.setFillColor(self.TEXT_COLOR)
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(center_x, self.PAGE_HEIGHT - 135, "ARDENT OLIMPIADA")
        
        # Certificate Subtitle
        c.setFillColor(self.SECONDARY_COLOR)
        c.setFont("Helvetica-Bold", 36)
        cert_type_text = self._get_type_text()
        c.drawCentredString(center_x, self.PAGE_HEIGHT - 185, cert_type_text)
        
        # Stylish Accent Line
        c.setStrokeColor(self.GOLD_COLOR)
        c.setLineWidth(1.5)
        c.line(center_x - 120, self.PAGE_HEIGHT - 200, center_x + 120, self.PAGE_HEIGHT - 200)
        
    def _get_type_text(self):
        """Get certificate type display text"""
        type_map = {
            'COURSE': 'KURS SERTIFIKATI',
            'OLYMPIAD': 'OLIMPIADA SERTIFIKATI', 
            'DIPLOMA': 'FAXRIY DIPLOM'
        }
        return type_map.get(self.cert.cert_type, 'SERTIFIKAT')
    
    def _draw_recipient(self):
        """Draw recipient name with normalization"""
        c = self.c
        center_x = self.PAGE_WIDTH / 2
        
        # "Ushbu sertifikat..." text
        c.setFillColor(self.LIGHT_TEXT)
        c.setFont("Helvetica", 13)
        c.drawCentredString(center_x, self.PAGE_HEIGHT - 245, "Ushbu sertifikat quyidagi shaxsga berildi:")
        
        # Recipient Name - Properly Capitalized
        user_full_name = self.cert.user.get_full_name() or self.cert.user.username
        display_name = user_full_name.title() # Capitalize Each Word
        
        c.setFillColor(self.TEXT_COLOR)
        c.setFont("Helvetica-Bold", 42)
        c.drawCentredString(center_x, self.PAGE_HEIGHT - 295, display_name.upper())
        
        # Decorative underline with spacing
        name_width = c.stringWidth(display_name.upper(), "Helvetica-Bold", 42)
        c.setStrokeColor(self.GOLD_COLOR)
        c.setLineWidth(2)
        c.line(center_x - name_width/2 - 10, self.PAGE_HEIGHT - 308, center_x + name_width/2 + 10, self.PAGE_HEIGHT - 308)
        
    def _draw_course_info(self):
        """Draw course info with capitalized title"""
        c = self.c
        center_x = self.PAGE_WIDTH / 2
        
        c.setFillColor(self.LIGHT_TEXT)
        c.setFont("Helvetica", 13)
        
        if self.cert.cert_type == 'OLYMPIAD':
            c.drawCentredString(center_x, self.PAGE_HEIGHT - 345, "quyidagi olimpiadada muvaffaqiyatli ishtirok etgani uchun:")
        else:
            c.drawCentredString(center_x, self.PAGE_HEIGHT - 345, "quyidagi kursni muvaffaqiyatli tugatgani uchun:")
        
        # Title - Capitalized properly
        title = self.cert.title
        if title:
            # Capitalize first letter if it's a single word subject, else handle carefully
            display_title = title.capitalize() if len(title.split()) == 1 else title
        else:
            display_title = "Olimpiada"
            
        c.setFillColor(self.SECONDARY_COLOR)
        c.setFont("Helvetica-Bold", 26)
        c.drawCentredString(center_x, self.PAGE_HEIGHT - 385, f'"{display_title}"')
        
    def _draw_grade(self):
        """Redesigned grade badge to fix clipping"""
        c = self.c
        center_x = self.PAGE_WIDTH / 2
        badge_y = self.PAGE_HEIGHT - 450
        
        # Normalize grade text (Handle long texts like "shtirok etdi")
        grade_text = str(self.cert.grade)
        # Fix: if it's "GOLD", "SILVER", "BRONZE", translate or format nicely
        grade_map = {
            'GOLD': "1-O'RIN (OLTIN)",
            'SILVER': "2-O'RIN (KUMUSH)",
            'BRONZE': "3-O'RIN (BRONZA)",
        }
        display_grade = grade_map.get(grade_text, grade_text).upper()
        
        # Dynamic ID for badge width
        c.setFont("Helvetica-Bold", 20)
        text_width = c.stringWidth(display_grade, "Helvetica-Bold", 20)
        badge_width = max(160, text_width + 60)
        
        # Elegant Rounded Badge
        c.setFillColor(self.ACCENT_COLOR) # Changed from primary for more pop
        c.roundRect(center_x - badge_width/2, badge_y - 25, badge_width, 55, 12, fill=True, stroke=False)
        
        # Grade Text
        c.setFillColor(colors.white)
        c.drawCentredString(center_x, badge_y + 8, display_grade)
        
        # Label below
        c.setFillColor(self.LIGHT_TEXT)
        c.setFont("Helvetica", 11)
        c.drawCentredString(center_x, badge_y - 40, "Natija")
        
    def _draw_qr_code(self):
        """QR Code with better integration"""
        c = self.c
        qr_size = 85
        qr_x = self.PAGE_WIDTH - 140
        qr_y = 70
        
        # Generate QR internally
        verify_url = f"https://hogwords.uz/certificate/verify/{self.cert.cert_number}"
        qr = qrcode.QRCode(version=1, box_size=10, border=1)
        qr.add_data(verify_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#111827", back_color="white")
        
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        
        # Draw white background for QR
        c.setFillColor(colors.white)
        c.roundRect(qr_x - 5, qr_y - 5, qr_size + 10, qr_size + 10, 8, fill=True, stroke=False)
        
        # Draw QR
        c.drawImage(ImageReader(buf), qr_x, qr_y, width=qr_size, height=qr_size)
        
        # ID and Label
        c.setFillColor(self.LIGHT_TEXT)
        c.setFont("Helvetica", 9)
        c.drawCentredString(qr_x + qr_size/2, qr_y - 18, "Tekshirish uchun skanerlang")
        
        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(self.SECONDARY_COLOR)
        c.drawCentredString(qr_x + qr_size/2, qr_y - 35, self.cert.cert_number)
        
    def _draw_footer(self):
        """Clean footer"""
        c = self.c
        center_x = self.PAGE_WIDTH / 2
        
        # Issue date
        issue_date = self.cert.issued_at.strftime("%d %B %Y")
        c.setFillColor(self.LIGHT_TEXT)
        c.setFont("Helvetica", 12)
        c.drawCentredString(center_x, 85, f"Berilgan sana: {issue_date}")
        
        # Validity text
        c.setFont("Helvetica-Oblique", 10)
        c.drawCentredString(center_x, 65, "Ushbu sertifikat cheksiz muddatga amal qiladi")
        
    def _draw_signatures(self):
        """Professional signatures section"""
        c = self.c
        sig_y = 125
        
        # Left (Director)
        left_x = 160
        c.setStrokeColor(self.BORDER_COLOR)
        c.setLineWidth(1)
        c.line(left_x - 60, sig_y, left_x + 60, sig_y)
        
        c.setFillColor(self.TEXT_COLOR)
        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(left_x, sig_y - 20, "Direktor")
        c.setFont("Helvetica", 10)
        c.drawCentredString(left_x, sig_y - 35, "Hogwords Olimpiada")
        
        # Right (Verifier)
        right_x = self.PAGE_WIDTH - 220 # Moved away from QR and center box
        c.setStrokeColor(self.BORDER_COLOR)
        c.line(right_x - 60, sig_y, right_x + 60, sig_y)
        
        verifier = "O'qituvchi"
        if self.cert.verified_by:
            verifier = self.cert.verified_by.get_full_name() or self.cert.verified_by.username
        
        c.setFillColor(self.TEXT_COLOR)
        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(right_x, sig_y - 20, verifier.title())
        c.setFont("Helvetica", 10)
        c.drawCentredString(right_x, sig_y - 35, "Tasdiqlovchi mas'ul")


def generate_certificate_pdf(certificate):
    """
    Main function to generate certificate PDF
    Returns the PDF as ContentFile for saving to model
    """
    generator = CertificateGenerator(certificate)
    pdf_buffer = generator.generate()
    
    filename = f"certificate_{certificate.cert_number}.pdf"
    return ContentFile(pdf_buffer.read(), name=filename)


def generate_qr_code(certificate):
    """
    Generate QR code image for certificate verification
    Returns ContentFile for saving to model
    """
    verify_url = f"https://ardent.uz/certificate/verify/{certificate.cert_number}"
    
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(verify_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="#7C3AED", back_color="white")
    
    buffer = io.BytesIO()
    qr_img.save(buffer, format='PNG')
    buffer.seek(0)
    
    filename = f"qr_{certificate.cert_number}.png"
    return ContentFile(buffer.read(), name=filename)
