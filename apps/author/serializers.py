from rest_framework import serializers

from .models import AuthorProfile

EDITABLE_FIELDS = [
    "full_name",
    "tagline",
    "bio",
    "photo",
    "academic_degree",
    "science_field",
    "telegram",
    "instagram",
    "email",
]


class AuthorPublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuthorProfile
        fields = EDITABLE_FIELDS + ["telegram_url", "instagram_url", "updated_at"]


class AuthorPanelSerializer(serializers.ModelSerializer):
    remove_photo = serializers.BooleanField(write_only=True, required=False)

    class Meta:
        model = AuthorProfile
        fields = EDITABLE_FIELDS + ["remove_photo", "updated_at"]
        read_only_fields = ["updated_at"]

    def update(self, instance, validated_data):
        if validated_data.pop("remove_photo", False) and "photo" not in validated_data:
            instance.photo = None
        return super().update(instance, validated_data)
