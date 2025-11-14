
from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib.auth.decorators import login_required
from .models import Cart, Order, OrderItem
from django_paystack.signals import payment_verified

@login_required
def payment_success(request, reference):
    cart = Cart.objects.get(user=request.user)
    order = Order.objects.create(
        user=request.user,
        total_price=cart.total_price,
        paid=True,
        payment_reference=reference
    )
    for item in cart.items.all():
        OrderItem.objects.create(
            order=order,
            product=item.product,
            price=item.product.price,
            quantity=item.quantity
        )
    cart.items.all().delete()
    return redirect('payment_success_page')

def payment_failure(request):
    return render(request, 'core/payment_failure.html')

@payment_verified.connect
def on_payment_verified(sender, ref, amount, **kwargs):
    """
    This signal is called when a payment is successfully verified.
    """
    # You can perform actions like updating order status, sending notifications, etc.
    print(f"Payment verified for reference: {ref} and amount: {amount}")

