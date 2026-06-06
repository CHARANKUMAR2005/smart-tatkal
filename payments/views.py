from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import FileResponse, Http404
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from .models import Payment
from certificates.models import Application
from notifications.models import Notification
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import uuid, io


def _generate_receipt_bytes(payment):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    c.setFillColorRGB(0.1, 0.3, 0.6)
    c.rect(0, height - 80, width, 80, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(width / 2, height - 40, settings.UNIVERSITY_NAME)
    c.setFont("Helvetica", 11)
    c.drawCentredString(width / 2, height - 60, "Payment Receipt")

    c.setFillColorRGB(0.1, 0.1, 0.1)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(80, height - 130, "PAYMENT RECEIPT")

    rows = [
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
    for label, value in rows:
        c.setFont("Helvetica-Bold", 10)
        c.drawString(80, y, label)
        c.setFont("Helvetica", 10)
        c.drawString(230, y, str(value))
        y -= 22

    c.setFont("Helvetica-Oblique", 9)
    c.setFillColorRGB(0.5, 0.5, 0.5)
    c.drawCentredString(width / 2, 40,
                        "This is a computer-generated receipt. No signature required.")
    c.save()
    buf.seek(0)
    return buf.read()


@login_required
def payment_view(request, app_id):
    app = get_object_or_404(Application, application_id=app_id)
    if request.user.role == 'student' and app.student.user != request.user:
        raise Http404

    existing = getattr(app, 'payment', None)
    if existing and existing.status == 'success':
        messages.info(request, 'Payment already completed.')
        return redirect('application_detail', app_id=app_id)

    key_id = settings.RAZORPAY_KEY_ID
    key_secret = settings.RAZORPAY_KEY_SECRET

    # ── Demo mode (no keys configured) ───────────────────────────────────────
    if not key_id or not key_secret:
        if request.method == 'POST':
            txn_id = f"DEMO{str(uuid.uuid4())[:8].upper()}"
            payment, created = Payment.objects.get_or_create(
                application=app,
                defaults={'amount': app.fee_amount, 'payment_method': 'demo',
                          'transaction_id': txn_id, 'status': 'success'}
            )
            if not created:
                payment.transaction_id = txn_id
                payment.payment_method = 'demo'
                payment.status = 'success'
                payment.save()
            app.payment_status = 'paid'
            app.save()
            Notification.objects.create(
                user=request.user, title='Payment Successful',
                message=f'Demo payment of ₹{payment.amount} recorded. TXN: {txn_id}',
                type='success', link=f'/applications/{app.application_id}/'
            )
            messages.success(request, f'Payment of ₹{payment.amount} successful! (Demo) TXN: {txn_id}')
            return redirect('application_detail', app_id=app_id)

        return render(request, 'payments/payment.html', {
            'application': app, 'demo_mode': True
        })

    # ── Real Razorpay payment ─────────────────────────────────────────────────
    import razorpay
    client = razorpay.Client(auth=(key_id, key_secret))
    amount_paise = int(app.fee_amount * 100)  # Razorpay works in paise

    try:
        order = client.order.create({
            'amount': amount_paise,
            'currency': 'INR',
            'receipt': str(app.application_id)[:40],
            'payment_capture': 1,
        })
    except Exception as exc:
        messages.error(request, f'Could not create payment order: {exc}')
        return redirect('application_detail', app_id=app_id)

    # Upsert a pending Payment row so the callback can look it up
    payment, _ = Payment.objects.get_or_create(
        application=app,
        defaults={'amount': app.fee_amount}
    )
    payment.razorpay_order_id = order['id']
    payment.amount = app.fee_amount
    payment.status = 'pending'
    payment.save()

    return render(request, 'payments/payment.html', {
        'application': app,
        'demo_mode': False,
        'razorpay_key': key_id,
        'order_id': order['id'],
        'amount_paise': amount_paise,
        'student_name': request.user.get_full_name() or request.user.username,
        'student_email': request.user.email,
        'student_phone': getattr(request.user, 'phone', ''),
    })


@login_required
def razorpay_callback(request):
    """Receives the hidden-form POST after Razorpay checkout succeeds."""
    if request.method != 'POST':
        return redirect('dashboard')

    rpay_id = request.POST.get('razorpay_payment_id', '')
    order_id = request.POST.get('razorpay_order_id', '')
    signature = request.POST.get('razorpay_signature', '')

    if not all([rpay_id, order_id, signature]):
        messages.error(request, 'Incomplete payment response received.')
        return redirect('dashboard')

    try:
        payment = Payment.objects.select_related(
            'application__student__user'
        ).get(razorpay_order_id=order_id)
    except Payment.DoesNotExist:
        messages.error(request, 'Payment record not found.')
        return redirect('dashboard')

    import razorpay
    client = razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )

    try:
        client.utility.verify_payment_signature({
            'razorpay_order_id': order_id,
            'razorpay_payment_id': rpay_id,
            'razorpay_signature': signature,
        })
    except Exception:
        payment.status = 'failed'
        payment.gateway_response = {'error': 'Signature mismatch', 'order_id': order_id}
        payment.save()
        messages.error(
            request,
            f'Payment verification failed. If money was deducted, contact support '
            f'with Order ID: {order_id}'
        )
        return redirect('application_detail', app_id=payment.application.application_id)

    # Signature valid — mark success
    payment.transaction_id = rpay_id
    payment.status = 'success'
    payment.payment_method = 'razorpay'
    payment.gateway_response = {
        'razorpay_payment_id': rpay_id,
        'razorpay_order_id': order_id,
        'razorpay_signature': signature,
    }
    payment.save()

    app = payment.application
    app.payment_status = 'paid'
    app.save()

    Notification.objects.create(
        user=app.student.user,
        title='Payment Successful',
        message=f'Payment of ₹{payment.amount} received. ID: {rpay_id}',
        type='success',
        link=f'/applications/{app.application_id}/'
    )

    messages.success(request, f'Payment of ₹{payment.amount} successful! ID: {rpay_id}')
    return redirect('application_detail', app_id=app.application_id)


@login_required
def download_receipt_view(request, payment_id):
    payment = get_object_or_404(
        Payment.objects.select_related('application__student__user'),
        payment_id=payment_id
    )
    if request.user.role == 'student' and payment.application.student.user != request.user:
        raise Http404

    filename = f"receipt_{str(payment.payment_id)[:8]}.pdf"
    file_path = f'receipts/{filename}'
    pdf_bytes = _generate_receipt_bytes(payment)

    if default_storage.exists(file_path):
        default_storage.delete(file_path)
    default_storage.save(file_path, ContentFile(pdf_bytes))

    try:
        return redirect(default_storage.url(file_path))
    except Exception:
        return FileResponse(
            io.BytesIO(pdf_bytes), as_attachment=True, filename=filename
        )
