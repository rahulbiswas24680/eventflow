"""
Custom throttling classes for EventFlow API.
"""

from rest_framework.throttling import UserRateThrottle, AnonRateThrottle


class LoginRateThrottle(UserRateThrottle):
    """Rate throttle for login endpoints."""
    scope = 'login'


class SignupRateThrottle(AnonRateThrottle):
    """Rate throttle for signup endpoints."""
    scope = 'signup'


class PaymentRateThrottle(UserRateThrottle):
    """Rate throttle for payment endpoints."""
    scope = 'payment'


class PaymentAnonRateThrottle(AnonRateThrottle):
    """Rate throttle for anonymous payment attempts."""
    scope = 'payment'