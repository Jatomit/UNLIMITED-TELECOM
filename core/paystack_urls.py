
from django.urls import path
from django.shortcuts import render
from . import paystack_views

urlpatterns = [
    path('payment/success/<str:reference>/', paystack_views.payment_success, name='payment_success'),
    path('payment/failure/', paystack_views.payment_failure, name='payment_failure'),
    path('payment/success_page/', lambda request: render(request, 'core/payment_success.html'), name='payment_success_page'),
]
