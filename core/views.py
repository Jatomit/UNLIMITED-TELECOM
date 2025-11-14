from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.conf import settings
import requests
import json

from .models import Product, Category, Cart, CartItem, Order, OrderItem

def index(request):
    """Render the new landing page."""
    products = Product.objects.filter(is_available=True)
    categories = Category.objects.all()
    context = {
        'products': products,
        'categories': categories,
    }
    return render(request, "core/index.html", context)

def signup(request):
    """Handle user signup."""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # You can log the user in directly if you want
            # login(request, user)
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'registration/signup.html', {'form': form})

def _get_cart(request):
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
    else:
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key
        cart, created = Cart.objects.get_or_create(session_key=session_key)
    return cart

@require_POST
def add_to_cart(request, product_id):
    cart = _get_cart(request)
    product = get_object_or_404(Product, id=product_id)
    quantity = int(request.POST.get('quantity', 1))
    
    cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
    if not created:
        cart_item.quantity += quantity
    else:
        cart_item.quantity = quantity
    cart_item.save()
    
    return redirect('cart_detail')

def cart_detail(request):
    cart = _get_cart(request)
    return render(request, 'core/cart_detail.html', {'cart': cart})

@login_required
def checkout(request):
    cart = _get_cart(request)
    if not cart.items.all():
        return redirect('index')
    return render(request, 'core/cart_detail.html', {'cart': cart})

@login_required
def initiate_payment(request):
    cart = _get_cart(request)
    if not cart.items.all():
        return redirect('index')

    url = 'https://api.paystack.co/transaction/initialize'
    headers = {
        'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}',
        'Content-Type': 'application/json',
    }
    data = {
        "email": request.user.email,
        "amount": cart.total_price_in_kobo,
        "callback_.pyurl": request.build_absolute_uri(f"/verify-payment/"),
    }

    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        response_data = response.json()
        if response_data['status']:
            # store the reference in the session, so we can retrieve it in the callback
            request.session['payment_ref'] = response_data['data']['reference']
            return redirect(response_data['data']['authorization_url'])
        else:
            return render(request, 'core/payment_failure.html', {'error': response_data['message']})
    except requests.exceptions.RequestException as e:
        return render(request, 'core/payment_failure.html', {'error': f"An error occurred: {e}"})

@login_required
def verify_payment(request):
    ref = request.GET.get('reference')
    if not ref:
        # if the reference is not in the get request, check the session
        ref = request.session.get('payment_ref')
        if not ref:
            return redirect('payment_failure')

    url = f'https://api.paystack.co/transaction/verify/{ref}'
    headers = {
        'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}',
    }

    try:
        response = requests.get(url, headers=headers)
        response_data = response.json()
        if response_data['status']:
            if response_data['data']['status'] == 'success':
                cart = _get_cart(request)
                order = Order.objects.create(user=request.user, is_paid=True)
                for item in cart.items.all():
                    OrderItem.objects.create(order=order, product=item.product, quantity=item.quantity)
                cart.items.all().delete()
                # clear the payment reference from the session
                if 'payment_ref' in request.session:
                    del request.session['payment_ref']
                return render(request, 'core/payment_success.html', {'order': order})
            else:
                return render(request, 'core/payment_failure.html')
        else:
            return render(request, 'core/payment_failure.html')
    except requests.exceptions.RequestException as e:
        return render(request, 'core/payment_failure.html', {'error': f"An error occurred: {e}"})