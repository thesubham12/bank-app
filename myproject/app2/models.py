from django.db import models
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from datetime import timedelta


def upload_profile_photo(instance, filename):
    return f'profile_photos/{instance.user.username}/{filename}'


class SavingsAccount(models.Model):

    customer_id = models.CharField(max_length=20, unique=True)

    user = models.OneToOneField(User, on_delete=models.CASCADE)

    full_name = models.CharField(max_length=100)

    mobile_number = models.CharField(max_length=10, unique=True)

    email = models.EmailField(unique=True)

    address = models.TextField()

    aadhaar_number = models.CharField(max_length=12, unique=True)

    pan_number = models.CharField(max_length=10, unique=True)

    account_number = models.CharField(max_length=20, unique=True)

    ifsc_code = models.CharField(max_length=15, default="APEX0001234")

    branch_name = models.CharField(max_length=100, default="Apex Main Branch")

    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    mpin = models.CharField(max_length=6)

    tpin = models.CharField(max_length=6)

    failed_mpin_attempts = models.IntegerField(default=0)
    mpin_locked_until = models.DateTimeField(null=True, blank=True)

    failed_tpin_attempts = models.IntegerField(default=0)
    tpin_locked_until = models.DateTimeField(null=True, blank=True)

    # ── NEW: profile photo ──
    photo = models.ImageField(
        upload_to=upload_profile_photo,
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.full_name
    

class OTPVerification(models.Model):
    email = models.EmailField(unique=True)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        self.expires_at = timezone.now() + timedelta(seconds=30)
        super().save(*args, **kwargs)

    def is_expired(self):
        return timezone.now() > self.expires_at

    def __str__(self):
        return self.email