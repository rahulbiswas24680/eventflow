from typing import Dict, List

from django.contrib.auth.models import User
from rest_framework import serializers

from events.api.serializers import EventSerializer
from payments.api.serializers import TransactionSerializer

from ..models import UserProfile, UserRSVPHistory


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        exclude = [
            "password",
            "is_superuser",
            "is_staff",
            "user_permissions",
            "groups",
        ]


class UserRSVPHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = UserRSVPHistory
        # exclude = ["user_profile"]
        fields = "__all__"


class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_rsvp_history = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = UserProfile
        fields = "__all__"

    def get_user_rsvp_history(self, obj) -> List[Dict]:
        qs = UserRSVPHistory.objects.filter(user_profile=obj)
        res = UserRSVPHistorySerializer(qs, many=True)
        return res.data


class UserProfileInlineSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = UserProfile
        fields = "__all__"


class UserRSVPHistoryDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserRSVPHistory
        # exclude = ['user_profile', 'rsvp']
        fields = "__all__"

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["user_profile_details"] = UserProfileInlineSerializer(
            instance.user_profile
        ).data
        data["event_details"] = EventSerializer(instance.rsvp.event).data

        from payments.models import Transaction

        event_transaction_details_qs = Transaction.objects.filter(
            rsvp=instance.rsvp, user=instance.rsvp.attendee
        )

        data["event_transaction_details"] = TransactionSerializer(
            event_transaction_details_qs, many=True
        ).data
        return data
