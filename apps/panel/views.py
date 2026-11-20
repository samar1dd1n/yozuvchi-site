from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import ensure_csrf_cookie


@never_cache
@ensure_csrf_cookie
def panel_page(request):
    """Admin panel — bitta sahifa, ma'lumotlarni /api/panel/ dan oladi."""
    return render(request, "panel/index.html")
