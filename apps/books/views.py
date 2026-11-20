from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET

from .selectors import visible_books
from .services import get_book_pdf


@require_GET
def book_pdf(request, slug):
    """Ochilgan sahifalardan yig'ilgan PDF ni brauzerda ochadi."""
    book = get_object_or_404(visible_books(request.user), slug=slug)
    for _ in range(2):  # parallel so'rov eski keshni o'chirib ulgursa, bir marta qayta urinadi
        path = get_book_pdf(book)
        if path is None:
            raise Http404("Kitobning hali birorta sahifasi ochilmagan.")
        try:
            handle = open(path, "rb")
        except FileNotFoundError:
            continue
        response = FileResponse(handle, content_type="application/pdf", filename=f"{book.slug}.pdf")
        response["Cache-Control"] = "no-cache"
        return response
    raise Http404("PDF tayyorlanmadi, sahifani yangilab ko'ring.")
