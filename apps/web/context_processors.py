from django.utils.functional import SimpleLazyObject

from apps.author.models import AuthorProfile


def site(request):
    # Shablonda ishlatilgandagina bazaga murojaat qiladi
    return {"site_author": SimpleLazyObject(AuthorProfile.load)}
