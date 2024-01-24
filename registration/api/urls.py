from django.urls import path
from rest_framework_simplejwt.views import (TokenObtainPairView,
                                            TokenRefreshView, TokenVerifyView)

from .views import UserLoginApiView, UserRegistrationApiView

urlpatterns = [
    # path('user/list/', UserListApiView.as_view(), name='user-list'),
    path('user/signup/', UserRegistrationApiView.as_view(), name='signup'),
    path('user/login/', UserLoginApiView.as_view(), name='login'),

    # jwt token
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),
]
