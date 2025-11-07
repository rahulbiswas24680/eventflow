from django.urls import path
from .views import add_to_cart, reset_cart, rsvp_checkout, checkout_success, checkout_cancel


urlpatterns = [
    path("cart/add/", add_to_cart, name="add-to-cart"),
    path("cart/reset/", reset_cart, name="reset-cart"),
    path("events/", rsvp_checkout, name='rsvp-checkout'),
    path("success/", checkout_success, name="checkout-success"),
    path("cancel/", checkout_cancel, name="checkout-cancel"),
]
