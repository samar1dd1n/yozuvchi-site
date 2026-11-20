from datetime import timedelta
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.test import Client
from django.urls import reverse
from django.utils import timezone
from pypdf import PdfReader

from apps.author.models import AuthorProfile
from apps.books.models import Book, BookPage
from apps.posts.models import Post

from .helpers import MediaTestCase, make_image, make_pdf


class AuthorTests(MediaTestCase):
    def test_singleton_and_handles(self):
        author = AuthorProfile.load()
        author.full_name = "Ali Valiyev"
        author.telegram = "https://t.me/ali_valiyev/"
        author.instagram = "@ali.v"
        author.save()
        AuthorProfile(full_name="Boshqa").save()  # baribir pk=1 ni yangilaydi

        self.assertEqual(AuthorProfile.objects.count(), 1)
        author = AuthorProfile.load()
        self.assertEqual(author.full_name, "Boshqa")
        self.assertEqual(author.telegram, "")

    def test_handle_normalization(self):
        author = AuthorProfile.load()
        author.telegram = "https://t.me/ali_valiyev/"
        author.instagram = "@ali.v"
        author.save()
        self.assertEqual(author.telegram, "ali_valiyev")
        self.assertEqual(author.instagram_url, "https://instagram.com/ali.v")

    def test_old_photo_deleted_when_replaced(self):
        author = AuthorProfile.load()
        author.photo = make_image("a.png")
        author.save()
        old_path = Path(author.photo.path)
        self.assertTrue(old_path.exists())

        with self.captureOnCommitCallbacks(execute=True):
            author.photo = make_image("b.png", color=(10, 10, 10))
            author.save()
        self.assertFalse(old_path.exists())
        self.assertTrue(Path(author.photo.path).exists())


class BookModelTests(MediaTestCase):
    def test_cover_processing_and_slug(self):
        book = Book.objects.create(
            title="Oʻzbek tili grammatikasi",
            cover=make_image(size=(500, 700), color=(200, 200, 200), left_color=(100, 50, 20)),
        )
        self.assertEqual(book.slug, "ozbek-tili-grammatikasi")
        self.assertEqual((book.cover_width, book.cover_height), (500, 700))
        self.assertTrue(book.cover.name.startswith("covers/") and book.cover.name.endswith(".jpg"))
        # chap chet rangi (100,50,20) * 0.82 ga yaqin
        r, g, b = (int(book.auto_spine_color[i : i + 2], 16) for i in (1, 3, 5))
        self.assertLess(abs(r - 82), 6)
        self.assertLess(abs(g - 41), 6)
        self.assertEqual(book.effective_spine_color, book.auto_spine_color)

        second = Book.objects.create(title="Oʻzbek tili grammatikasi", cover=make_image())
        self.assertEqual(second.slug, "ozbek-tili-grammatikasi-2")

    def test_page_kinds_and_thumbnails(self):
        book = Book.objects.create(title="Fizika", cover=make_image())
        image_page = BookPage.objects.create(book=book, number=1, file=make_image("p1.png", size=(1200, 1600)))
        pdf_page = BookPage.objects.create(book=book, number=2, file=make_pdf(pages=3))

        self.assertEqual(image_page.kind, BookPage.Kind.IMAGE)
        self.assertTrue(image_page.thumbnail)
        self.assertEqual(pdf_page.kind, BookPage.Kind.PDF)
        self.assertEqual(pdf_page.pdf_page_count, 3)
        self.assertTrue(pdf_page.thumbnail, "PDF birinchi beti thumbnail bo'lishi kerak")


class PublicBookTests(MediaTestCase):
    def setUp(self):
        now = timezone.now()
        self.book = Book.objects.create(title="Kvant fizikasi", cover=make_image())
        BookPage.objects.create(book=self.book, number=1, file=make_image("1.png"), publish_at=now - timedelta(days=2))
        BookPage.objects.create(book=self.book, number=2, file=make_pdf(pages=2), publish_at=now - timedelta(days=1))
        self.locked = BookPage.objects.create(
            book=self.book, number=3, file=make_image("3.png"), publish_at=now + timedelta(days=1)
        )

    def test_api_hides_locked_page_files(self):
        response = self.client.get(reverse("api:book-detail", args=[self.book.slug]))
        self.assertEqual(response.status_code, 200)
        pages = {p["number"]: p for p in response.json()["pages"]}
        self.assertTrue(pages[1]["is_open"])
        self.assertIsNotNone(pages[1]["file"])
        self.assertFalse(pages[3]["is_open"])
        self.assertIsNone(pages[3]["file"])
        self.assertIsNone(pages[3]["thumbnail"])
        self.assertNotIn(self.locked.file.name, response.content.decode())

    def test_pdf_contains_only_open_pages(self):
        response = self.client.get(reverse("api:book-pdf", args=[self.book.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("inline", response["Content-Disposition"])
        reader = PdfReader(BytesIO(b"".join(response.streaming_content)))
        self.assertEqual(len(reader.pages), 3)  # 1 rasm + 2 betli PDF, qulflangan sahifa yo'q

    def test_pdf_rebuilt_when_new_page_opens(self):
        self.client.get(reverse("api:book-pdf", args=[self.book.slug]))
        self.locked.publish_at = timezone.now() - timedelta(minutes=1)
        self.locked.save()
        response = self.client.get(reverse("api:book-pdf", args=[self.book.slug]))
        reader = PdfReader(BytesIO(b"".join(response.streaming_content)))
        self.assertEqual(len(reader.pages), 4)
        cached = list(Path(settings.PDF_CACHE_DIR).glob(f"book-{self.book.pk}-*.pdf"))
        self.assertEqual(len(cached), 1, "eski kesh o'chirilishi kerak")

    def test_pdf_404_when_nothing_open(self):
        empty = Book.objects.create(title="Bo'sh", cover=make_image())
        BookPage.objects.create(book=empty, number=1, file=make_image(), publish_at=timezone.now() + timedelta(days=3))
        response = self.client.get(reverse("api:book-pdf", args=[empty.slug]))
        self.assertEqual(response.status_code, 404)

    def test_hidden_book_not_public(self):
        self.book.is_published = False
        self.book.save()
        self.assertEqual(self.client.get(reverse("api:book-detail", args=[self.book.slug])).status_code, 404)
        self.assertEqual(self.client.get(reverse("web:book")).status_code, 200)  # "tez orada" holati
        self.assertContains(self.client.get(reverse("web:book")), "Kitob tez orada")

    def test_book_page_renders_3d_and_lock(self):
        response = self.client.get(reverse("web:book"))
        self.assertContains(response, 'class="book3d"')
        self.assertContains(response, "--ratio:1.4000")
        self.assertContains(response, "2 / 3 sahifa ochilgan")
        self.assertContains(response, "ochiladi")
        self.assertNotContains(response, self.locked.file.name)


class PanelApiTests(MediaTestCase):
    def setUp(self):
        self.staff = self.make_staff()
        self.book = Book.objects.create(title="Kimyo", cover=make_image())

    def test_requires_staff(self):
        self.assertEqual(self.client.get("/api/panel/books/").status_code, 403)
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get("/api/panel/books/").status_code, 200)

    def test_login_enforces_csrf(self):
        client = Client(enforce_csrf_checks=True)
        payload = {"username": "admin", "password": "kuchli-parol-123"}
        self.assertEqual(client.post("/api/auth/login/", payload, content_type="application/json").status_code, 403)

        client.get("/panel/")  # csrftoken cookie oladi
        token = client.cookies["csrftoken"].value
        response = client.post("/api/auth/login/", payload, content_type="application/json", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(client.get("/api/auth/me/").json()["username"], "admin")

    def test_wrong_password(self):
        response = self.client.post(
            "/api/auth/login/", {"username": "admin", "password": "xato"}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

    def test_bulk_upload_schedules_pages(self):
        self.client.force_login(self.staff)
        start = timezone.now() + timedelta(days=1)
        response = self.client.post(
            "/api/panel/pages/bulk/",
            {
                "book": self.book.pk,
                "files": [make_image("001.png"), make_image("002.png"), make_pdf("003.pdf")],
                "start_at": start.isoformat(),
                "interval_days": 2,
            },
        )
        self.assertEqual(response.status_code, 201, response.content)
        pages = list(self.book.pages.order_by("number"))
        self.assertEqual([p.number for p in pages], [1, 2, 3])
        self.assertEqual(pages[2].kind, BookPage.Kind.PDF)
        self.assertEqual((pages[1].publish_at - pages[0].publish_at).days, 2)
        self.assertEqual((pages[2].publish_at - pages[0].publish_at).days, 4)

    def test_duplicate_page_number_rejected(self):
        self.client.force_login(self.staff)
        BookPage.objects.create(book=self.book, number=1, file=make_image())
        response = self.client.post("/api/panel/pages/", {"book": self.book.pk, "number": 1, "file": make_image()})
        self.assertEqual(response.status_code, 400)
        self.assertIn("allaqachon bor", response.json()["number"][0])

    def test_invalid_pdf_rejected(self):
        self.client.force_login(self.staff)
        from django.core.files.uploadedfile import SimpleUploadedFile

        fake = SimpleUploadedFile("bad.pdf", b"bu pdf emas", content_type="application/pdf")
        response = self.client.post("/api/panel/pages/", {"book": self.book.pk, "number": 1, "file": fake})
        self.assertEqual(response.status_code, 400)

    def test_author_update_and_remove_photo(self):
        self.client.force_login(self.staff)
        # Django test client PATCH uchun multipart'ni o'zi yasamaydi
        from django.test.client import BOUNDARY, MULTIPART_CONTENT, encode_multipart

        body = encode_multipart(BOUNDARY, {"full_name": "Dr. Karimov", "photo": make_image()})
        response = self.client.patch("/api/panel/author/", body, content_type=MULTIPART_CONTENT)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertTrue(AuthorProfile.load().photo)

        body = encode_multipart(BOUNDARY, {"remove_photo": "true"})
        response = self.client.patch("/api/panel/author/", body, content_type=MULTIPART_CONTENT)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(AuthorProfile.load().photo)

    def test_book_spine_color_override(self):
        self.client.force_login(self.staff)
        response = self.client.patch(
            f"/api/panel/books/{self.book.pk}/", {"spine_color": "#123456"}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["effective_spine_color"], "#123456")
        response = self.client.patch(
            f"/api/panel/books/{self.book.pk}/", {"spine_color": "red"}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)


class PostTests(MediaTestCase):
    def setUp(self):
        now = timezone.now()
        self.live = Post.objects.create(title="Yangi kitob chiqdi", body="Matn", published_at=now - timedelta(hours=1))
        self.future = Post.objects.create(title="Ertangi post", published_at=now + timedelta(days=1))
        self.hidden = Post.objects.create(title="Yashirin", is_published=False)
        Post.objects.create(title="Maqola", kind=Post.Kind.ARTICLE, published_at=now - timedelta(days=2))

    def test_public_api_shows_only_live(self):
        titles = [p["title"] for p in self.client.get("/api/posts/").json()["results"]]
        self.assertEqual(titles, ["Yangi kitob chiqdi", "Maqola"])
        self.assertEqual(self.client.get(f"/api/posts/{self.future.slug}/").status_code, 404)

    def test_kind_filter(self):
        titles = [p["title"] for p in self.client.get("/api/posts/?kind=article").json()["results"]]
        self.assertEqual(titles, ["Maqola"])

    def test_pages_render(self):
        response = self.client.get(reverse("web:posts"))
        self.assertContains(response, "Yangi kitob chiqdi")
        self.assertNotContains(response, "Ertangi post")
        self.assertEqual(self.client.get(self.live.get_absolute_url()).status_code, 200)
        self.assertEqual(self.client.get(self.hidden.get_absolute_url()).status_code, 404)


class WebSmokeTests(MediaTestCase):
    def test_empty_site_renders(self):
        for url in ["/", "/kitob/", "/fikrlar/", "/robots.txt", "/panel/"]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_home_shows_author(self):
        author = AuthorProfile.load()
        author.full_name = "Dilshod Rahimov"
        author.academic_degree = "Fizika-matematika fanlari doktori"
        author.save()
        response = self.client.get("/")
        self.assertContains(response, "Dilshod Rahimov")
        self.assertContains(response, "Fizika-matematika fanlari doktori")
