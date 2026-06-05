from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import FileResponse, JsonResponse
from django.utils import timezone
from django.conf import settings
from .models import Payment
from certificates.models import Application
from notifications.models import Notification
import uuid, os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

def generate_receipt_pdf(payment, path):
    c = canvas.Canvas(path, pagesize=A4)
    width, height = A4
    c.setFillColorRGB(0.1, 0.3, 0.6)
    c.rect(0, height-80, width, 80, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(width/2, height-40, settings.UNIVERSITY_NAME)
    c.setFont("Helvetica", 11)
    c.drawCentredString(width/2, height-60, "Payment Receipt")
    
    c.setFillColorRGB(0.1, 0.1, 0.1)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(80, height-130, "PAYMENT RECEIPT")
    
    data = [
        ("Receipt No:", str(payment.payment_id)[:8].upper()),
        ("Transaction ID:", payment.transaction_id or "N/A"),
        ("Student Name:", payment.application.student.user.get_full_name()),
        ("Student ID:", payment.application.student.student_id),
        ("Certificate Type:", payment.application.get_certificate_type_display()),
        ("Service Type:", "TATKAL" if payment.application.is_tatkal else "Normal"),
        ("Amount Paid:", f"Rs. {payment.amount}"),
        ("Payment Method:", payment.get_payment_method_display()),
        ("Payment Date:", payment.created_at.strftime('%d %B %Y %H:%M')),
        ("Status:", payment.status.upper()),
    ]
    
    y = height - 180
    for label, value in data:
        c.setFont("Helvetica-Bold", 10)
        c.drawString(80, y, label)
        c.setFont("Helvetica", 10)
        c.drawString(230, y, str(value))
        y -= 22
    
    c.setFont("Helvetica-Oblique", 9)
    c.setFillColorRGB(0.5, 0.5, 0.5)
    c.drawCentredString(width/2, 40, "This is a computer-generated receipt. No signature required.")
    c.save()

@login_required
def payment_view(request, app_id):
    app = get_object_or_404(Application, application_id=app_id)
    if request.user.role == 'student' and app.student.user != request.user:
        from django.http import Http404
        raise Http404
    
    existing_payment = getattr(app, 'payment', None)
    if existing_payment and existing_payment.status == 'success':
        messages.info(request, 'Payment already completed.')
        return redirect('application_detail', app_id=app_id)
    
    if request.method == 'POST':
        method = request.POST.get('payment_method', 'demo')
        
        # Simulate payment (demo mode)
        txn_id = f"TXN{str(uuid.uuid4())[:8].upper()}"
        
        payment, created = Payment.objects.get_or_create(
            application=app,
            defaults={
                'amount': app.fee_amount,
                'payment_method': method,
                'transaction_id': txn_id,
                'status': 'success',
            }
        )
        if not created:
            payment.transaction_id = txn_id
            payment.payment_method = method
            payment.status = 'success'
            payment.save()
        
        app.payment_status = 'paid'
        app.save()
        
        Notification.objects.create(
            user=request.user,
            title='Payment Successful',
            message=f'Payment of Rs.{payment.amount} received. TXN: {txn_id}',
            type='success'
        )
        
        messages.success(request, f'Payment of ₹{payment.amount} successful! TXN: {txn_id}')
        return redirect('application_detail', app_id=app_id)
    
    return render(request, 'payments/payment.html', {
        'application': app,
        'razorpay_key': settings.RAZORPAY_KEY_ID,
    })

@login_required
def download_receipt_view(request, payment_id):
    payment = get_object_or_404(Payment, payment_id=payment_id)
    if request.user.role == 'student' and payment.application.student.user != request.user:
        from django.http import Http404
        raise Http404
    
    filename = f"receipt_{str(payment.payment_id)[:8]}.pdf"
    path = os.path.join(settings.MEDIA_ROOT, 'receipts', filename)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    generate_receipt_pdf(payment, path)
    
    return FileResponse(open(path, 'rb'), as_attachment=True, filename=filename)
