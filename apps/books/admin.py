from django.contrib import admin

from .models import Book, BookPage


class BookPageInline(admin.TabularInline):
    model = BookPage
    extra = 0
    fields = ["number", "file", "kind", "publish_at"]
    readonly_fields = ["kind"]
    ordering = ["number"]


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ["title", "is_published", "order", "created_at"]
    list_editable = ["is_published", "order"]
    readonly_fields = ["slug", "auto_spine_color", "cover_width", "cover_height"]
    inlines = [BookPageInline]


@admin.register(BookPage)
class BookPageAdmin(admin.ModelAdmin):
    list_display = ["book", "number", "kind", "publish_at"]
    list_filter = ["book", "kind"]
    ordering = ["book", "number"]
