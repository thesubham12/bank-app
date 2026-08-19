import random
import json
from decimal import InvalidOperation

from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.core.mail import EmailMultiAlternatives
from django.http import JsonResponse
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.views.decorators.http import require_POST

from .models import SavingsAccount
from .forms import SavingsAccountForm
from app2.models import OTPVerification
import uuid

import qrcode
from io import BytesIO
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required

@login_required
def account_qr_code(request):
    try:
        account = SavingsAccount.objects.get(user=request.user)
    except SavingsAccount.DoesNotExist:
        return HttpResponse(status=404)

    qr_data = f"APEXBANK|{account.account_number}|{account.full_name}|{account.ifsc_code}"

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="#0b3d91", back_color="white")

    buffer = BytesIO()
    img.save(buffer, format="PNG")

    response = HttpResponse(buffer.getvalue(), content_type="image/png")

    # If ?download=1 is in the URL, force download instead of just displaying
    if request.GET.get('download') == '1':
        response['Content-Disposition'] = f'attachment; filename="apexbank_qr_{account.account_number}.png"'

    return response



# ────────────────────────────────────────────────────────────
#  helpers
# ────────────────────────────────────────────────────────────

def _send_success_email(user, credential_label):
    """Send a notification email after a credential change."""
    from django.utils import timezone
    name       = user.get_full_name() or user.username
    time_str   = timezone.localtime(timezone.now()).strftime('%d %b %Y, %I:%M %p')
    subject    = f"Apex Bank – Your {credential_label} was changed"
    text_body  = f"Hi {name}, your {credential_label} was changed successfully on {time_str}. If this wasn't you, contact support immediately."
    html_body  = f"""
    <html><body style="font-family:Arial,sans-serif;background:#f4f6fb;padding:30px;">
      <div style="max-width:480px;margin:auto;background:#fff;border-radius:12px;padding:32px;box-shadow:0 4px 20px rgba(0,0,0,.08);">
        <h2 style="color:#1a73e8;margin-bottom:4px;">Apex Bank</h2>
        <p style="color:#555;margin-top:0;">Security Alert</p>
        <hr style="border:none;border-top:1px solid #eee;margin:16px 0;">
        <p style="color:#333;">Hi <strong>{name}</strong>,</p>
        <p style="color:#333;">Your <strong>{credential_label}</strong> has been changed successfully.</p>
        <table style="width:100%;background:#f8f9fa;border-radius:8px;padding:16px;margin:16px 0;border-collapse:collapse;">
          <tr><td style="color:#888;padding:4px 0;">Action</td><td style="color:#333;font-weight:600;">{credential_label} Changed</td></tr>
          <tr><td style="color:#888;padding:4px 0;">Time</td><td style="color:#333;">{time_str}</td></tr>
          <tr><td style="color:#888;padding:4px 0;">Account</td><td style="color:#333;">{user.email}</td></tr>
        </table>
        <p style="color:#e53935;font-weight:600;">If you did not make this change, please contact Apex Bank support immediately.</p>
        <p style="color:#888;font-size:12px;margin-top:24px;">This is an automated security notification. Do not reply to this email.</p>
      </div>
    </body></html>
    """
    msg = EmailMultiAlternatives(subject, text_body, None, [user.email])
    msg.attach_alternative(html_body, "text/html")
    msg.send()


def _send_otp_email(to_email, otp, action_label):
    """Send OTP email for credential change."""
    subject = f"Apex Bank – OTP to {action_label}"
    text_body = f"Your OTP to {action_label} is: {otp}. It is valid for this session only."
    html_body = f"""
    <html><body style="font-family:Arial,sans-serif;background:#f4f6fb;padding:30px;">
      <div style="max-width:480px;margin:auto;background:#fff;border-radius:12px;padding:32px;box-shadow:0 4px 20px rgba(0,0,0,.08);">
        <h2 style="color:#1a73e8;margin-bottom:4px;">Apex Bank</h2>
        <p style="color:#555;">Security Verification</p>
        <hr style="border:none;border-top:1px solid #eee;margin:16px 0;">
        <p style="color:#333;">You requested to <strong>{action_label}</strong>.</p>
        <p style="color:#333;">Your One-Time Password (OTP) is:</p>
        <div style="text-align:center;margin:24px 0;">
          <span style="font-size:36px;font-weight:700;letter-spacing:8px;color:#1a73e8;">{otp}</span>
        </div>
        <p style="color:#888;font-size:13px;">This OTP is valid for this session only. Do not share it with anyone.</p>
        <p style="color:#888;font-size:12px;margin-top:24px;">If you did not request this, please ignore this email.</p>
      </div>
    </body></html>
    """
    msg = EmailMultiAlternatives(subject, text_body, None, [to_email])
    msg.attach_alternative(html_body, "text/html")
    msg.send()


# ────────────────────────────────────────────────────────────
#  AJAX: send OTP for credential change
# ────────────────────────────────────────────────────────────

@login_required
@require_POST
def send_change_otp(request):
    """
    Called by JS when user fills in new values and clicks "Send OTP".
    Generates OTP, stores pending data in session, emails OTP.
    """
    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({'ok': False, 'error': 'Invalid request.'})

    action = data.get('action')  # 'password' | 'mpin' | 'tpin'
    user   = request.user

    # ── validate inputs before sending OTP ──
    if action == 'password':
        old_pass = data.get('old_password', '')
        new_pass = data.get('new_password', '')
        confirm  = data.get('confirm_password', '')
        if not user.check_password(old_pass):
            return JsonResponse({'ok': False, 'error': 'Current password is incorrect.'})
        if new_pass != confirm:
            return JsonResponse({'ok': False, 'error': 'New passwords do not match.'})
        if len(new_pass) < 6:
            return JsonResponse({'ok': False, 'error': 'Password must be at least 6 characters.'})
        request.session['otp_pending_action'] = 'password'
        request.session['otp_pending_data']   = {'new_password': new_pass}
        label = 'change your password'

    elif action == 'mpin':
        new_mpin     = data.get('new_mpin', '')
        confirm_mpin = data.get('confirm_mpin', '')
        if not new_mpin.isdigit() or len(new_mpin) not in [4, 6]:
            return JsonResponse({'ok': False, 'error': 'MPIN must be 4 or 6 digits.'})
        if new_mpin != confirm_mpin:
            return JsonResponse({'ok': False, 'error': 'MPINs do not match.'})
        request.session['otp_pending_action'] = 'mpin'
        request.session['otp_pending_data']   = {'new_mpin': new_mpin}
        label = 'change your MPIN'

    elif action == 'tpin':
        new_tpin     = data.get('new_tpin', '')
        confirm_tpin = data.get('confirm_tpin', '')
        if not new_tpin.isdigit() or len(new_tpin) not in [4, 6]:
            return JsonResponse({'ok': False, 'error': 'TPIN must be 4 or 6 digits.'})
        if new_tpin != confirm_tpin:
            return JsonResponse({'ok': False, 'error': 'TPINs do not match.'})
        request.session['otp_pending_action'] = 'tpin'
        request.session['otp_pending_data']   = {'new_tpin': new_tpin}
        label = 'change your TPIN'

    else:
        return JsonResponse({'ok': False, 'error': 'Unknown action.'})

    # generate & save OTP — always reset expires_at so resend gives a fresh 30s window
    from django.utils import timezone
    from datetime import timedelta

    otp = str(random.randint(100000, 999999))
    expires_at = timezone.now() + timedelta(seconds=30)
    OTPVerification.objects.update_or_create(
        email=user.email,
        defaults={'otp': otp, 'expires_at': expires_at}
    )

    # send email
    try:
        _send_otp_email(user.email, otp, label)
    except Exception as e:
        return JsonResponse({'ok': False, 'error': f'Could not send email: {e}'})

    # mask email for display
    parts = user.email.split('@')
    masked = parts[0][:2] + '****@' + parts[1] if len(parts) == 2 else user.email

    return JsonResponse({'ok': True, 'masked_email': masked})


# ────────────────────────────────────────────────────────────
#  AJAX: verify OTP and apply change
# ────────────────────────────────────────────────────────────

@login_required
@require_POST
def verify_change_otp(request):
    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({'ok': False, 'error': 'Invalid request.'})

    entered_otp = data.get('otp', '').strip()
    action      = request.session.get('otp_pending_action')
    pending     = request.session.get('otp_pending_data', {})

    if not action or not pending:
        return JsonResponse({'ok': False, 'error': 'Session expired. Please start again.'})

    # verify OTP
    try:
        record = OTPVerification.objects.get(email=request.user.email)
    except OTPVerification.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'OTP not found. Please request a new one.'})

    if record.otp != entered_otp:
        return JsonResponse({'ok': False, 'error': 'Incorrect OTP. Please try again.'})

    # check expiry
    if record.is_expired():
        return JsonResponse({'ok': False, 'error': 'OTP has expired. Please request a new one.'})

    # OTP correct & not expired — apply change
    user = request.user

    if action == 'password':
        user.set_password(pending['new_password'])
        user.save()
        update_session_auth_hash(request, user)
        msg = 'Password changed successfully!'
        _send_success_email(user, 'Password')

    elif action == 'mpin':
        try:
            account = SavingsAccount.objects.get(user=user)
            account.mpin = pending['new_mpin']
            account.save()
            msg = 'MPIN updated successfully!'
            _send_success_email(user, 'MPIN')
        except SavingsAccount.DoesNotExist:
            return JsonResponse({'ok': False, 'error': 'Savings account not found.'})

    elif action == 'tpin':
        try:
            account = SavingsAccount.objects.get(user=user)
            account.tpin = pending['new_tpin']
            account.save()
            msg = 'TPIN updated successfully!'
            _send_success_email(user, 'TPIN')
        except SavingsAccount.DoesNotExist:
            return JsonResponse({'ok': False, 'error': 'Savings account not found.'})

    else:
        return JsonResponse({'ok': False, 'error': 'Unknown action.'})

    # clean up session + OTP record
    record.delete()
    request.session.pop('otp_pending_action', None)
    request.session.pop('otp_pending_data', None)

    return JsonResponse({'ok': True, 'message': msg})


@login_required
def profile(request):
    try:
        account = SavingsAccount.objects.get(user=request.user)
    except SavingsAccount.DoesNotExist:
        create_url = reverse('accounts')
        messages.error(
            request,
            mark_safe(
                'You don\'t have a savings account yet. Please create one to access your profile. '
                f'<a href="{create_url}" class="btn btn-sm btn-primary ms-2">Create savings account</a>'
            )
        )
        return redirect("home")
    except InvalidOperation:
        messages.error(
            request,
            "Account data is corrupted. Please contact support."
        )
        return redirect("home")

    # ── Upload Photo ──
    if request.method == 'POST' and 'upload_photo' in request.POST:
        photo = request.FILES.get('photo')
        if photo and account:
            account.photo = photo
            account.save()
            messages.success(request, '✓ Profile photo updated successfully!')
        elif not account:
            messages.error(request, '✗ Please create a savings account first.')
        return redirect('profile')

    # ── Edit Profile ──
    if request.method == 'POST' and 'edit_profile' in request.POST:
        if account:
            account.mobile_number = request.POST.get('mobile_number', account.mobile_number)
            account.address       = request.POST.get('address', account.address)
            account.branch_name   = request.POST.get('branch_name', account.branch_name)
            account.save()
            messages.success(request, 'Profile updated successfully!')
        return redirect('profile')

    return render(request, 'profile.html', {'account': account})


def scan_to_pay_page(request):
    try:
        sender = SavingsAccount.objects.get(user=request.user)
    except SavingsAccount.DoesNotExist:
        sender = None
    return render(request, 'scan_to_pay.html', {
        'own_account_number': sender.account_number if sender else ''
    })
    

@login_required
def home(request):
    return render(request, "home.html")


@login_required
def about(request):
    return render(request, 'about.html')

@login_required
def support(request):
    return render(request, 'support.html')

@login_required
def accounts(request):
    return render(request, 'create_ac.html')

@login_required
def saving_ac_create(request):
    # Check if user already has a savings account
    if SavingsAccount.objects.filter(user=request.user).exists():
        messages.warning(request, "You already have a savings account.")
        return redirect('home')
    
    if request.method == 'POST':
        form = SavingsAccountForm(request.POST)
        if form.is_valid():
            try:
                initial_deposit = form.cleaned_data['initial_deposit']
                account_number = f"APEX{random.randint(100000000000, 999999999999)}"
                customer_id = f"CUST{uuid.uuid4().hex[:8].upper()}"

                SavingsAccount.objects.create(
                    user=request.user,
                    customer_id=customer_id,
                    full_name=form.cleaned_data['full_name'],
                    mobile_number=form.cleaned_data['mobile_number'],
                    email=form.cleaned_data['email'],
                    aadhaar_number=form.cleaned_data['aadhaar_number'],
                    pan_number=form.cleaned_data['pan_number'],
                    mpin=form.cleaned_data['mpin'],
                    tpin=form.cleaned_data['tpin'],
                    address=form.cleaned_data['address'],
                    account_number=account_number,
                    balance=initial_deposit,
                )

                messages.success(request, f'🎉 Congratulations! Your Savings Account has been created successfully!\nAccount Number: {account_number}')
                return redirect('home')

            except Exception as e:
                messages.error(request, f'Error creating account: {str(e)}')
        else:
            messages.error(request, 'Please fix the errors below.')
    else:
        form = SavingsAccountForm()

    return render(request, 'saving.html', {'form': form})
