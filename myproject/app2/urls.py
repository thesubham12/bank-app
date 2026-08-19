from django.urls import path
from . import views

urlpatterns = [
    path("home/", views.home, name="home"),
    path('profile/', views.profile, name='profile'),
    path('about/', views.about, name='about'),
    path('support/', views.support, name='support'),
    path("account_creation/", views.accounts, name="accounts"),
    path("saving_ac_create/", views.saving_ac_create, name="saving_ac_create"),

    # OTP-based credential change
    path('send-change-otp/',    views.send_change_otp,   name='send_change_otp'),
    path('verify-change-otp/',  views.verify_change_otp, name='verify_change_otp'),

    path('account-qr/', views.account_qr_code, name='account_qr_code'),

    path('scan-to-pay/', views.scan_to_pay_page, name='scan_to_pay'),
]