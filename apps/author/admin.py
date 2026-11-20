from django.contrib import admin

from .models import AuthorProfile


@admin.register(AuthorProfile)
class AuthorProfileAdmin(admin.ModelAdmin):
    list_display = ["__str__", "academic_degree", "updated_at"]

    def has_add_permission(self, request):
        return not AuthorProfile.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
