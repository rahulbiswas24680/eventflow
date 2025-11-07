from rest_framework import serializers
from ..models import CustomUser, Organizer, UserRSVPHistory

class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "phone",
            "profession",
            "education",
            "goal",
            "languages",
            "address",
            "country",
        ]
        read_only_fields = ["id", "email", "username"]

class OrganizerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organizer
        fields = [
            "id",
            "organizer_name",
            "organizer_email",
            "organizer_phone",
            "organizer_address",
            "organizer_slug",
            "is_active",
        ]
        read_only_fields = ["id", "organizer_slug"]


# ----------------------------------------------------------------------
# Additional serializers required by the API views
# ----------------------------------------------------------------------
class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for detailed view of a CustomUser (profile) instance.
    Includes all fields defined on the CustomUser model.
    """
    class Meta:
        model = CustomUser
        fields = "__all__"
        read_only_fields = ["id", "email", "username"]


class UserRSVPHistorySerializer(serializers.ModelSerializer):
    """
    Basic serializer for UserRSVPHistory entries.
    """
    class Meta:
        model = UserRSVPHistory
        fields = "__all__"
        read_only_fields = ["id", "created_at"]


class UserRSVPHistoryDetailsSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for UserRSVPHistory that can be extended with
    nested representations (e.g., event details) if needed.
    """
    class Meta:
        model = UserRSVPHistory
        fields = "__all__"
        read_only_fields = ["id", "created_at"]
