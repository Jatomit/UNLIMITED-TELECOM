from .views import _get_cart

def cart(request):
    return {'cart': _get_cart(request)}
