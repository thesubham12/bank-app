from django.urls import path
from . import views

urlpatterns = [
    path("register/", views.register, name="register"),
    path("login/", views.login_view, name="login"),
    path("", views.logout_view, name="logout"),  
    path("verify-otp/", views.verify_otp, name="verify_otp"),
    path('resend-otp/', views.resend_otp, name='resend_otp'),  
]