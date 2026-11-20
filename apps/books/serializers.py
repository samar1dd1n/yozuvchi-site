from django.urls import reverse
from rest_framework import serializers

from apps.core.validators import PAGE_FILE_VALIDATORS

from .models import Book, BookPage


def absolute(request, url: str | None) -> str | None:
    if not url:
        return None
    return request.build_absolute_uri(url) if request else url


# ---------- Ochiq API ----------

class BookPagePublicSerializer(serializers.ModelSerializer):
    is_open = serializers.BooleanField(read_only=True)
    file = serializers.SerializerMethodField()
    thumbnail = serializers.SerializerMethodField()

    class Meta:
        model = BookPage
        fields = ["number", "kind", "publish_at", "is_open", "file", "thumbnail"]

    # Qulflangan sahifaning fayl havolasi hech qachon berilmaydi
    def get_file(self, obj):
        return absolute(self.context.get("request"), obj.file.url) if obj.is_open else None

    def get_thumbnail(self, obj):
        if obj.is_open and obj.thumbnail:
            return absolute(self.context.get("request"), obj.thumbnail.url)
        return None


class BookListSerializer(serializers.ModelSerializer):
    spine_color = serializers.CharField(source="effective_spine_color", read_only=True)
    pages_count = serializers.IntegerField(read_only=True)
    open_pages_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Book
        fields = ["slug", "title", "cover", "spine_color", "pages_count", "open_pages_count"]


class BookDetailSerializer(serializers.ModelSerializer):
    spine_color = serializers.CharField(source="effective_spine_color", read_only=True)
    pages = BookPagePublicSerializer(many=True, read_only=True)
    pdf_url = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = [
            "slug",
            "title",
            "annotation",
            "cover",
            "back_cover",
            "cover_width",
            "cover_height",
            "spine_color",
            "pages",
            "pdf_url",
        ]

    def get_pdf_url(self, obj):
        if not any(page.is_open for page in obj.pages.all()):
            return None
        return absolute(self.context.get("request"), reverse("api:book-pdf", args=[obj.slug]))


# ---------- Admin panel ----------

class BookPanelSerializer(serializers.ModelSerializer):
    remove_back_cover = serializers.BooleanField(write_only=True, required=False)
    effective_spine_color = serializers.CharField(read_only=True)
    pages_count = serializers.SerializerMethodField()
    open_pages_count = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = [
            "id",
            "title",
            "slug",
            "annotation",
            "cover",
            "back_cover",
            "remove_back_cover",
            "spine_color",
            "auto_spine_color",
            "effective_spine_color",
            "cover_width",
            "cover_height",
            "is_published",
            "order",
            "pages_count",
            "open_pages_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["slug", "created_at", "updated_at"]

    def get_pages_count(self, obj):
        value = getattr(obj, "pages_count", None)
        return value if value is not None else obj.pages.count()

    def get_open_pages_count(self, obj):
        value = getattr(obj, "open_pages_count", None)
        return value if value is not None else sum(p.is_open for p in obj.pages.all())

    def update(self, instance, validated_data):
        if validated_data.pop("remove_back_cover", False) and "back_cover" not in validated_data:
            instance.back_cover = None
        return super().update(instance, validated_data)

    def create(self, validated_data):
        validated_data.pop("remove_back_cover", None)
        return super().create(validated_data)


class BookPagePanelSerializer(serializers.ModelSerializer):
    is_open = serializers.BooleanField(read_only=True)

    class Meta:
        model = BookPage
        fields = [
            "id",
            "book",
            "number",
            "file",
            "kind",
            "pdf_page_count",
            "thumbnail",
            "publish_at",
            "is_open",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]
        validators = []  # raqam takrorini quyida o'zbekcha xabar bilan tekshiramiz

    def validate(self, attrs):
        book = attrs.get("book", getattr(self.instance, "book", None))
        number = attrs.get("number", getattr(self.instance, "number", None))
        duplicates = BookPage.objects.filter(book=book, number=number)
        if self.instance:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise serializers.ValidationError({"number": f"{number}-sahifa bu kitobda allaqachon bor."})
        return attrs

    def update(self, instance, validated_data):
        validated_data.pop("book", None)  # sahifani boshqa kitobga ko'chirib bo'lmaydi
        return super().update(instance, validated_data)


class BulkPageUploadSerializer(serializers.Serializer):
    book = serializers.PrimaryKeyRelatedField(queryset=Book.objects.all())
    files = serializers.ListField(
        child=serializers.FileField(validators=PAGE_FILE_VALIDATORS),
        allow_empty=False,
        max_length=100,
    )
    start_number = serializers.IntegerField(min_value=1, required=False)
    start_at = serializers.DateTimeField()
    interval_days = serializers.IntegerField(min_value=0, max_value=365, default=1)

    def validate(self, attrs):
        book = attrs["book"]
        start = attrs.get("start_number")
        if start is None:
            last = book.pages.order_by("-number").values_list("number", flat=True).first()
            start = (last or 0) + 1
        numbers = range(start, start + len(attrs["files"]))
        taken = sorted(book.pages.filter(number__in=numbers).values_list("number", flat=True))
        if taken:
            raise serializers.ValidationError(
                {"start_number": f"Bu raqamli sahifalar allaqachon bor: {', '.join(map(str, taken))}."}
            )
        attrs["start_number"] = start
        return attrs
