from rest_framework import serializers

from .models import Post


class PostPublicSerializer(serializers.ModelSerializer):
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)
    excerpt = serializers.CharField(source="summary", read_only=True)

    class Meta:
        model = Post
        fields = ["slug", "title", "kind", "kind_label", "excerpt", "body", "image", "published_at"]


class PostPanelSerializer(serializers.ModelSerializer):
    remove_image = serializers.BooleanField(write_only=True, required=False)
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)
    is_live = serializers.BooleanField(read_only=True)

    class Meta:
        model = Post
        fields = [
            "id",
            "title",
            "slug",
            "kind",
            "kind_label",
            "excerpt",
            "body",
            "image",
            "remove_image",
            "is_published",
            "published_at",
            "is_live",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["slug", "created_at", "updated_at"]

    def create(self, validated_data):
        validated_data.pop("remove_image", None)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if validated_data.pop("remove_image", False) and "image" not in validated_data:
            instance.image = None
        return super().update(instance, validated_data)
