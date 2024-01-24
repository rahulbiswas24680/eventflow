from django.contrib.auth.models import User
from rest_framework import serializers

from ..models import UserProfile, UserRSVPHistory


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        exclude = ['password', 'is_superuser',
                   'is_staff', 'user_permissions', 'groups']


class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = UserProfile
        fields = '__all__'


class UserRSVPHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = UserRSVPHistory
        fields = '__all__'


# class UserProfileWithHistorySerializer(serializers.ModelSerializer):
#     rsvp_history = UserRSVPHistorySerializer(many=True, read_only=True)

#     class Meta:
#         model = UserProfile
#         exclude = ['user']

#     # You can add additional fields or methods if needed
#     def to_representation(self, instance):
#         data = super().to_representation(instance)
#         data['username'] = instance.user.username  # Add the username for reference
#         return data
