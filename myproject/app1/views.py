import random

from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from django.core.mail import EmailMultiAlternatives
from django.shortcuts import render, redirect
from django.utils import timezone
from datetime import timedelta

from app2.models import OTPVerification
from .forms import RegisterForm, OTPForm, LoginForm
from django.contrib.auth import logout


def generate_username(name):
    names = name.split()
    if len(names) >= 2:
        base = names[1].lower()
    else:
        base = names[0].lower()
    while True:
        username = f"{base}{random.randint(1000,9999)}"
        if not User.objects.filter(username=username).exists():
            return username


def _send_otp_email(email, otp, full_name, username):
    html_message = f"""
    <html>
    <body style="font-family:Arial,sans-serif;background:#f4f6fb;padding:30px;">
      <div style="max-width:480px;margin:auto;background:#fff;border-radius:12px;
                  padding:32px;box-shadow:0 4px 20px rgba(0,0,0,.08);">
        <h2 style="color:#1a73e8;margin-bottom:4px;">Apex Bank</h2>
        <p style="color:#555;margin-top:0;">Account Registration</p>
        <hr style="border:none;border-top:1px solid #eee;margin:16px 0;">
        <p style="color:#333;">Dear <strong>{full_name}</strong>,</p>
        <p style="color:#333;">Your One-Time Password (OTP) for registration is:</p>
        <div style="text-align:center;margin:24px 0;">
          <span style="font-size:36px;font-weight:700;letter-spacing:8px;color:#1a73e8;">{otp}</span>
        </div>
        <table style="width:100%;background:#f8f9fa;border-radius:8px;padding:16px;
                      margin:16px 0;border-collapse:collapse;">
          <tr>
            <td style="color:#888;padding:4px 0;">Username</td>
            <td style="color:#333;font-weight:600;">{username}</td>
          </tr>
          <tr>
            <td style="color:#888;padding:4px 0;">Valid For</td>
            <td style="color:#333;">30 seconds only</td>
          </tr>
        </table>
        <div style="background:#fdecea;border-left:4px solid #e53935;border-radius:6px;padding:12px 16px;margin:16px 0;">
          <p style="color:#e53935;font-weight:700;margin:0;">⚠️ Do not share this OTP with anyone. Apex Bank will never ask for your OTP.</p>
        </div>
        <p style="color:#888;font-size:12px;margin-top:24px;">
          This is an automated message. Do not reply to this email.
        </p>
      </div>
    </body>
    </html>
    """
    msg = EmailMultiAlternatives(
        "Apex Bank – Registration OTP",
        f"OTP: {otp} | Username: {username}",
        None,
        [email]
    )
    msg.attach_alternative(html_message, "text/html")
    msg.send()
    


def _send_welcome_email(email, full_name, username):
    html_message = f"""
    <html>
    <body style="font-family:Arial,sans-serif;background:#f4f6fb;padding:30px;">
      <div style="max-width:480px;margin:auto;background:#fff;border-radius:12px;
                  padding:32px;box-shadow:0 4px 20px rgba(0,0,0,.08);">
        <h2 style="color:#1a73e8;margin-bottom:4px;">Apex Bank</h2>
        <p style="color:#555;margin-top:0;">Welcome to Apex Bank!</p>
        <hr style="border:none;border-top:1px solid #eee;margin:16px 0;">
        <p style="color:#333;">Dear <strong>{full_name}</strong>,</p>
        <p style="color:#333;">🎉 Your account has been successfully registered!</p>
        <table style="width:100%;background:#f8f9fa;border-radius:8px;padding:16px;
                      margin:16px 0;border-collapse:collapse;">
          <tr>
            <td style="color:#888;padding:6px 0;">Username</td>
            <td style="color:#333;font-weight:600;">{username}</td>
          </tr>
          <tr>
            <td style="color:#888;padding:6px 0;">Email</td>
            <td style="color:#333;font-weight:600;">{email}</td>
          </tr>
        </table>
        <div style="background:#fdecea;border-left:4px solid #e53935;border-radius:6px;
                    padding:12px 16px;margin:16px 0;">
          <p style="color:#e53935;font-weight:700;margin:0;">
            ⚠️ Never share your password with anyone. Apex Bank will never ask for your password.
          </p>
        </div>
        <p style="color:#888;font-size:12px;margin-top:24px;">
          This is an automated message. Do not reply to this email.
        </p>
      </div>
    </body>
    </html>
    """
    msg = EmailMultiAlternatives(
        "Apex Bank – Welcome! Registration Successful",
        f"Welcome {full_name}! Your username is: {username}",
        None,
        [email]
    )
    msg.attach_alternative(html_message, "text/html")
    msg.send()


def register(request):
    if request.method == "POST":
        full_name = request.POST.get("full_name")
        phone = request.POST.get("phone")
        email = request.POST.get("email")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        if password != confirm_password:
            return render(request, "register.html", {"error": "Passwords do not match"})

        if User.objects.filter(email=email).exists():
            return render(request, "register.html", {"error": "Email already registered"})

        otp = str(random.randint(100000, 999999))
        username = generate_username(full_name)

        request.session["generated_username"] = username
        request.session["full_name"] = full_name
        request.session["phone"] = phone
        request.session["email"] = email
        request.session["password"] = password

        OTPVerification.objects.update_or_create(
            email=email,
            defaults={
                "otp": otp,
                "expires_at": timezone.now() + timedelta(seconds=30)
            }
        )

        try:
            _send_otp_email(email, otp, full_name, username)
        except Exception as e:
            return render(request, "register.html", {"error": f"Email error: {e}"})

        return redirect("verify_otp")

    return render(request, "register.html")


def resend_otp(request):
    email     = request.session.get("email")
    full_name = request.session.get("full_name")
    username  = request.session.get("generated_username")

    if not email:
        return redirect("register")

    otp = str(random.randint(100000, 999999))

    OTPVerification.objects.update_or_create(
        email=email,
        defaults={
            "otp": otp,
            "expires_at": timezone.now() + timedelta(seconds=30)
        }
    )

    _send_otp_email(email, otp, full_name, username)
    return redirect("verify_otp")


def verify_otp(request):
    if request.method == "POST":
        user_otp = request.POST.get("otp")
        email    = request.session.get("email")

        try:
            otp_obj = OTPVerification.objects.get(email=email)

            if otp_obj.is_expired():
                return render(request, "verify_otp.html", {
                    "error": "OTP has expired. Please request a new one."
                })

            if otp_obj.otp == user_otp:
                username  = request.session["generated_username"]
                full_name = request.session.get("full_name", username)

                User.objects.create_user(
                    username=username,
                    email=email,
                    password=request.session["password"]
                )
                otp_obj.delete()
                request.session["generated_username"] = username

                # Welcome email bhejo
                _send_welcome_email(email, full_name, username)

                return redirect("login")

            return render(request, "verify_otp.html", {"error": "Invalid OTP"})

        except OTPVerification.DoesNotExist:
            return render(request, "verify_otp.html", {"error": "OTP not found. Please register again."})

    return render(request, "verify_otp.html")


def login_view(request):
    username_message = request.session.pop("generated_username", None)

    if request.method == "POST":
        username_or_email = request.POST.get("username_or_email")
        password = request.POST.get("password")
        user = None

        if "@" in username_or_email:
            try:
                user_obj = User.objects.get(email=username_or_email)
                user = authenticate(request, username=user_obj.username, password=password)
            except User.DoesNotExist:
                pass
        else:
            user = authenticate(request, username=username_or_email, password=password)

        if user:
            login(request, user)
            return redirect("home")

        return render(request, "login.html", {"error": "Invalid credentials"})

    return render(request, "login.html", {"generated_username": username_message})



def logout_view(request):
    logout(request)
    return redirect('login')