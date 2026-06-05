import os, uuid, qrcode, io
from django.conf import settings
from django.utils import timezone
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch, mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.pdfgen import canvas
import string, random

def generate_verification_code():
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=12))

def generate_qr_code(data, filename):
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    path = os.path.join(settings.MEDIA_ROOT, 'qrcodes', filename)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path)
    return f'qrcodes/{filename}'

def generate_certificate_pdf(application, certificate):
    from reportlab.pdfgen import canvas as pdfcanvas
    student = application.student
    cert_type = application.get_certificate_type_display()
    
    filename = f"certificate_{certificate.verification_code}.pdf"
    path = os.path.join(settings.MEDIA_ROOT, 'certificates', filename)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    c = canvas.Canvas(path, pagesize=A4)
    width, height = A4
    
    # Background
    c.setFillColorRGB(0.98, 0.97, 0.93)
    c.rect(0, 0, width, height, fill=1, stroke=0)
    
    # Decorative border
    c.setStrokeColorRGB(0.1, 0.3, 0.6)
    c.setLineWidth(6)
    c.rect(15, 15, width-30, height-30, fill=0, stroke=1)
    c.setStrokeColorRGB(0.8, 0.6, 0.1)
    c.setLineWidth(2)
    c.rect(22, 22, width-44, height-44, fill=0, stroke=1)
    
    # University header
    c.setFillColorRGB(0.1, 0.3, 0.6)
    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(width/2, height-80, settings.UNIVERSITY_NAME.upper())
    
    c.setFillColorRGB(0.3, 0.3, 0.3)
    c.setFont("Helvetica", 11)
    c.drawCentredString(width/2, height-100, settings.UNIVERSITY_ADDRESS)
    
    # Divider
    c.setStrokeColorRGB(0.8, 0.6, 0.1)
    c.setLineWidth(1.5)
    c.line(60, height-115, width-60, height-115)
    
    # Certificate title
    c.setFillColorRGB(0.1, 0.3, 0.6)
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(width/2, height-155, cert_type.upper())
    
    c.setStrokeColorRGB(0.3, 0.3, 0.3)
    c.setLineWidth(0.5)
    c.line(width/2 - 100, height-162, width/2 + 100, height-162)
    
    # Certificate ID
    c.setFillColorRGB(0.5, 0.5, 0.5)
    c.setFont("Helvetica", 9)
    c.drawCentredString(width/2, height-175, f"Certificate No: {certificate.verification_code}")
    
    # Body text
    c.setFillColorRGB(0.1, 0.1, 0.1)
    c.setFont("Helvetica", 11)
    
    body_y = height - 220
    body_text = f"This is to certify that {student.user.get_full_name().upper()} (Student ID: {student.student_id})"
    c.drawCentredString(width/2, body_y, body_text)
    
    body_y -= 22
    dept_text = f"studying in {student.get_department_display()} Department, Year {student.year}"
    c.drawCentredString(width/2, body_y, dept_text)
    
    body_y -= 22
    if application.certificate_type == 'bonafide':
        purpose_text = "is a Bonafide student of this institution for the current academic year."
    elif application.certificate_type == 'character':
        purpose_text = "bears good moral character and conduct during the period of study."
    elif application.certificate_type == 'transfer':
        purpose_text = "has been granted Transfer Certificate as per institutional records."
    elif application.certificate_type == 'course_completion':
        purpose_text = "has successfully completed the course requirements."
    else:
        purpose_text = f"has applied for {cert_type} which is issued for official purposes."
    
    c.drawCentredString(width/2, body_y, purpose_text)
    
    if application.purpose:
        body_y -= 22
        c.setFont("Helvetica-Oblique", 10)
        c.drawCentredString(width/2, body_y, f"Purpose: {application.purpose}")
    
    # Issue date
    body_y -= 45
    c.setFont("Helvetica", 11)
    c.drawString(80, body_y, f"Date of Issue: {certificate.issued_at.strftime('%d %B %Y')}")
    
    if application.is_tatkal:
        c.setFillColorRGB(0.8, 0.2, 0.1)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(80, body_y - 18, "★ TATKAL SERVICE")
    
    # Signature line
    sig_y = body_y - 80
    c.setFillColorRGB(0.1, 0.1, 0.1)
    c.setFont("Helvetica", 10)
    c.line(width - 220, sig_y, width - 80, sig_y)
    c.drawCentredString(width - 150, sig_y - 15, "Authorized Signatory")
    c.drawCentredString(width - 150, sig_y - 28, settings.UNIVERSITY_NAME)
    
    # QR Code
    qr_path = os.path.join(settings.MEDIA_ROOT, str(certificate.qr_code))
    if os.path.exists(qr_path):
        c.drawImage(qr_path, 60, sig_y - 60, width=65, height=65)
        c.setFont("Helvetica", 7)
        c.drawString(60, sig_y - 72, "Scan to verify")
    
    # Watermark
    c.saveState()
    c.setFont("Helvetica-Bold", 65)
    c.setFillColorRGB(0.9, 0.9, 0.9)
    c.setFillAlpha(0.15)
    c.translate(width/2, height/2)
    c.rotate(45)
    c.drawCentredString(0, 0, "OFFICIAL")
    c.restoreState()
    
    # Footer
    c.setFillColorRGB(0.5, 0.5, 0.5)
    c.setFont("Helvetica", 8)
    verify_url = f"http://localhost:8000/verify/{certificate.verification_code}/"
    c.drawCentredString(width/2, 40, f"Verify at: {verify_url}")
    c.drawCentredString(width/2, 28, "This certificate is system generated and digitally signed.")
    
    c.save()
    return f'certificates/{filename}'
