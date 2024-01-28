from django.contrib.auth.hashers import check_password
from django.contrib.auth.models import Group, User
from django.db import IntegrityError, transaction
from rest_framework import filters, permissions, status
from rest_framework.exceptions import MethodNotAllowed, NotAcceptable
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from communication.tasks.mail_tasks import (
    ongoing_events_mail,
    platform_registration_mail,
)
from user_profiles.models import UserProfile

from .serializers import UserLoginSerializer, UserRegistationSerializer


def create_user(data, group_names=[]):
    """
    Create a new user and associate with specified groups.
    :param data: Data for user creation
    :param group_names: List of group names to associate with the user
    """

    serializer = UserRegistationSerializer(data=data)
    if serializer.is_valid():
        validated_data = serializer.validated_data

        user_obj = serializer.save(
            is_staff=False, is_superuser=False, groups=group_names
        )
        profile = UserProfile.objects.create(user=user_obj)

        return user_obj
    else:
        errors = serializer.errors
        return errors


def validate_user(data):
    """
    :param data: Data for user creation
    """

    email = data.get("email").lower()
    password = data.get("password")

    if str(email) and str(password):
        try:
            user_obj = User.objects.get(email=email)
            # print(user_obj)
        except User.DoesNotExist as e:
            return Response(
                {"status": "error", "msg": "User does not exists"},
                status=status.HTTP_403_FORBIDDEN,
            )

        if user_obj and check_password(password, user_obj.password):
            token = RefreshToken.for_user(user_obj)

            groups = []
            permissions = []

            for group in user_obj.groups.all():
                groups.append(group.name)
                for permission in group.permissions.all():
                    permissions.append(permission.name)

            return {
                "token": str(token.access_token),
                "is_staff": user_obj.is_staff,
                "user_id": user_obj.id,
                "role": groups,
                "permissions": permissions,
            }
    else:
        return Response(
            {"status": "error", "msg": "Please check email or password"},
            status=status.HTTP_401_UNAUTHORIZED,
        )


class UserRegistrationApiView(APIView):
    """
    User registration API

    [POST] :payload:

    {
        "password": "password",
        "is_superuser": false,
        "is_staff": false,
        "username": "pranab",
        "first_name": "Pranab",
        "last_name": "Saha",
        "email": "pranabsaha@gmail.com"
    }

    """

    serializer_class = UserRegistationSerializer

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        data = request.data
        print(data)
        groups = Group.objects.all()
        staff_groups = groups[0]
        user_groups = groups[1]
        try:
            user_obj = create_user(
                data,
                group_names=[
                    user_groups if not data["is_staff"] else staff_groups
                ],
            )

            platform_registration_mail.delay(
                user_name=user_obj.first_name, recipients=[user_obj.email]
            )

            return Response(
                f"{user_obj.username} has been registered",
                status=status.HTTP_201_CREATED,
            )
        except:
            return Response(
                {"error": "Something went wrong when registering user"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class UserLoginApiView(APIView):
    """
    User login API

    [POST] :payload:

    {
    "email": "username@example.com",
    "password": "password"
    }

    """

    serializer_class = UserLoginSerializer

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        data = request.data
        try:
            res = validate_user(data)
            # print(res)

            ongoing_events_mail.delay(
                user_name=request.user.first_name,
                recipients=[request.user.email],
            )

            return Response(
                {"status": "success", "data": res}, status=status.HTTP_200_OK
            )
        except Exception as e:
            print("here", e)
            return Response(
                {"status": "error", "msg": str(e)},
                status=status.HTTP_401_UNAUTHORIZED,
            )


# class UserListApiView(APIView):
#     """
#     User list API


#     """

#     def get(self, request):
#         queryset = User.objects.all()
#         serializer = UserRegistationSerializer(queryset, many=True)
#         return Response(serializer.data, status=status.HTTP_200_OK)
