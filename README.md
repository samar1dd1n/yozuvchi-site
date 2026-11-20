# Yozuvchi sayti

Ilmiy kitob muallifi uchun sayt: Django 5.2 + Django REST Framework.

**Sahifalar**

| Manzil | Nima bor |
|---|---|
| `/` | Muallif: ism, shior, tanishtiruv, rasm, ilmiy daraja, soha, bog'lanish |
| `/kitob/` | Aylanib turadigan 3D kitob (muqova — muallif yuklagan to'liq rasm). Bosilsa, ochilgan sahifalardan yig'ilgan PDF ochiladi. Pastda sahifalar: ochilganlari ko'rinadi, kelajakdagilari qulf bilan va ochilish sanasi bilan |
| `/fikrlar/` | Yangilik, maqola va rasm postlari; turi bo'yicha saralash, sahifalash |
| `/panel/` | Muallif uchun admin panel |
| `/django-admin/` | Zaxira admin (Django'ning o'zi) |

## Qanday ishlaydi

- **Sahifalarni kunma-kun ochish.** Har bir sahifaning `publish_at` (ochilish vaqti) maydoni bor. Vaqt kelmaguncha sahifa saytda qulf bilan turadi: fayl havolasi API'da ham, HTML'da ham berilmaydi, PDF'ga ham kirmaydi. Fayl nomlari tasodifiy uuid, ularni taxmin qilib bo'lmaydi.
- **Ko'p sahifani birdan yuklash.** Panelda 100 tagacha faylni tanlab, "har necha kunda bittadan" deb belgilash mumkin. Masalan 30 ta fayl va 1 kun desangiz, bir oy davomida har kuni bittadan ochiladi.
- **PDF.** `/api/books/<slug>/pdf/` ochilgan sahifalarni (rasm va PDF aralash) bitta PDF qilib yig'adi va `var/pdf_cache/` ga keshlaydi. Yangi sahifa ochilganda PDF avtomatik qayta yig'iladi, eski kesh o'chadi.
- **Muqova.** Yuklangan rasm siqiladi (2000 px gacha), 3D kitob shu rasm proporsiyasini oladi. Kitob qirrasi rangi muqovaning chap chetidan avtomatik olinadi, panelda qo'lda o'zgartirsa ham bo'ladi.
- **Rasmlar.** Telefon rasmlari burilib qolmaydi (EXIF tuzatiladi), katta rasmlar kichraytiriladi. Almashtirilgan yoki o'chirilgan fayllar diskdan ham o'chadi.

## Tuzilma

```
config/          sozlamalar, URL'lar (api_urls.py — barcha API)
apps/core/       umumiy: rasm qayta ishlash, validatorlar, fayl tozalash
apps/author/     muallif (yagona yozuv, pk=1)
apps/books/      kitob, sahifalar, selectors.py (o'qish), services.py (PDF, yuklash)
apps/posts/      fikrlar (postlar)
apps/panel/      login/logout API va /panel/ sahifasi
apps/web/        ochiq sahifalar (Django template, SEO uchun server tomonida chiziladi)
templates/       HTML shablonlar
static/          css/site.css, js/book.js (3D kitob hover), panel/ (admin panel JS+CSS)
tests/           testlar
```

## Kompyuterda ishga tushirish

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # DEBUG=True qoldiring
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Keyin http://127.0.0.1:8000/panel/ ga kiring.

Testlar:

```bash
python manage.py test tests
```

## API

Ochiq (o'qish uchun):

| Metod | Manzil | |
|---|---|---|
| GET | `/api/author/` | muallif ma'lumotlari |
| GET | `/api/books/` | kitoblar ro'yxati |
| GET | `/api/books/<slug>/` | kitob + sahifalar (qulflanganlarda `file: null`) |
| GET | `/api/books/<slug>/pdf/` | ochilgan sahifalar PDF ko'rinishida |
| GET | `/api/posts/?kind=news\|article\|photo&page=2` | postlar |
| GET | `/api/posts/<slug>/` | bitta post |

Admin panel (faqat `is_staff`, session + CSRF):

| Metod | Manzil | |
|---|---|---|
| POST | `/api/auth/login/`, `/api/auth/logout/` | kirish, chiqish |
| GET | `/api/auth/me/` | joriy foydalanuvchi |
| GET, PATCH | `/api/panel/author/` | muallif (`remove_photo=true` — rasmni olib tashlash) |
| CRUD | `/api/panel/books/` | kitoblar (`remove_back_cover=true`) |
| CRUD | `/api/panel/pages/?book=<id>` | sahifalar |
| POST | `/api/panel/pages/bulk/` | `book`, `files[]`, `start_number`, `start_at`, `interval_days` |
| CRUD | `/api/panel/posts/` | postlar (`remove_image=true`) |

## Serverga tez o'rnatish (bitta skript)

Serverda nginx bo'lsa, loyihani `/opt/yozuvchi` ga ochib, shuni ishga tushiring:

```bash
bash /opt/yozuvchi/deploy/install.sh DOMEN
```

Skript serverdagi boshqa loyihalarga tegmaydi. U quyidagilarni bajaradi:
- venv yaratadi va `.env` faylini tuzadi (baza — SQLite);
- migratsiyalarni bajaradi;
- systemd xizmatini (127.0.0.1:8010) va alohida nginx faylini yaratadi;
- Let's Encrypt orqali HTTPS ulaydi va admin yaratadi.

Kod yangilangach ham shu buyruqni qayta ishga tushirish mumkin.

## Serverga qo'lda joylash (Ubuntu VPS, Nginx, PostgreSQL, PM2)

1. **Baza:**
   ```bash
   sudo -u postgres psql -c "CREATE USER yozuvchi WITH PASSWORD 'kuchli-parol';"
   sudo -u postgres psql -c "CREATE DATABASE yozuvchi OWNER yozuvchi;"
   ```
2. **Kod va muhit:**
   ```bash
   cd /var/www && git clone <repo> yozuvchi && cd yozuvchi
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env
   ```
   `.env` ichida:
   ```
   DEBUG=False
   SECRET_KEY=<python -c "import secrets; print(secrets.token_urlsafe(50))">
   ALLOWED_HOSTS=sayt.uz,www.sayt.uz
   CSRF_TRUSTED_ORIGINS=https://sayt.uz,https://www.sayt.uz
   DATABASE_URL=postgres://yozuvchi:kuchli-parol@127.0.0.1:5432/yozuvchi
   SECURE_COOKIES=False     # HTTPS ulangach True qiling
   ```
3. **Tayyorlash:**
   ```bash
   python manage.py migrate
   python manage.py collectstatic --noinput
   python manage.py createsuperuser   # muallif uchun login
   ```
4. **Gunicorn'ni PM2 orqali ishga tushirish** (`--timeout 120`: ko'p sahifani birdan yuklash va PDF yig'ish vaqt olishi mumkin):
   ```bash
   pm2 start .venv/bin/gunicorn --name yozuvchi --interpreter none -- \
     config.wsgi:application --bind 127.0.0.1:8010 --workers 3 --timeout 120
   pm2 save
   ```
5. **Nginx:** `deploy/nginx.conf.example` ni `/etc/nginx/sites-available/yozuvchi` ga nusxalab, domen va yo'lni to'g'rilang:
   ```bash
   sudo ln -s /etc/nginx/sites-available/yozuvchi /etc/nginx/sites-enabled/
   sudo nginx -t && sudo systemctl reload nginx
   ```
6. **HTTPS:** `sudo certbot --nginx -d sayt.uz -d www.sayt.uz`, keyin `.env` da `SECURE_COOKIES=True` qilib `pm2 restart yozuvchi`.

**Zaxira nusxa:** baza (`pg_dump yozuvchi`) va `media/` papkasi. `var/pdf_cache/` kerak emas, u avtomatik qayta yig'iladi.

**Yangilash:** `git pull && pip install -r requirements.txt && python manage.py migrate && python manage.py collectstatic --noinput && pm2 restart yozuvchi`
