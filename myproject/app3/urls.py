from django.urls import path
from . import views

urlpatterns = [
    path('deposit/',         views.deposit,             name='deposit'),
    path('withdraw/',        views.withdraw,            name='withdraw'),
    path('transfer/',        views.transfer,            name='transfer'),
    path('verify-receiver/', views.verify_receiver,     name='verify_receiver'),
    path('history/',         views.transaction_history, name='transaction_history'),
    path('history/statement/', views.download_statement, name='download_statement'),

    path('scan-qr-transfer/', views.scan_qr_transfer, name='scan_qr_transfer'),
    
]