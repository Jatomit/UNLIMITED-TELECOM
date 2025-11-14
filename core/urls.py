from django.urls import path, include
from .views import index, signup, add_to_cart, cart_detail, checkout, initiate_payment, verify_payment

urlpatterns = [
    path("", index, name="index"),
    path("signup/", signup, name="signup"),
    path("accounts/", include("django.contrib.auth.urls")), # for login, logout, etc.
    path('cart/', cart_detail, name='cart_detail'),
    path('cart/add/<int:product_id>/', add_to_cart, name='add_to_cart'),
    path('checkout/', checkout, name='checkout'),
    path('initiate-payment/', initiate_payment, name='initiate_payment'),
    path('verify-payment/', verify_payment, name='verify_payment'),
]