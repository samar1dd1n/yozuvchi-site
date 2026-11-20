#!/usr/bin/env bash
# Yozuvchi saytini Ubuntu serverga o'rnatadi. Serverdagi boshqa loyihalarga (bot va h.k.) tegmaydi:
# alohida papka, alohida port, alohida nginx fayli, SQLite baza.
#
# Ishlatish:   bash /opt/yozuvchi/deploy/install.sh nodira.duckdns.org
# Boshqa port: PORT=8020 bash /opt/yozuvchi/deploy/install.sh nodira.duckdns.org
# Kod yangilangach ham shu buyruqni qayta ishlatish mumkin (.env va baza saqlanib qoladi).
set -euo pipefail

DOMAIN="${1:-}"
APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PORT="${PORT:-8010}"
SERVICE=yozuvchi

say() { printf '\n==> %s\n' "$1"; }
die() { printf '\nXATO: %s\n' "$1" >&2; exit 1; }

[ -n "$DOMAIN" ] || die "Domenni yozing: bash $0 nodira.duckdns.org"
[ "$(id -u)" -eq 0 ] || die "root sifatida ishga tushiring"
command -v nginx >/dev/null || die "Serverda nginx topilmadi."

say "Portlarni tekshirish"
if ss -tlnp | grep -E ':(80|443) ' | grep -vq nginx; then
  ss -tlnp | grep -E ':(80|443) '
  die "80/443-portda nginx emas, boshqa dastur turibdi. Yuqoridagi natijani yuboring."
fi
if ss -tln | grep -q ":$PORT " && ! systemctl is-active --quiet "$SERVICE"; then
  die "$PORT-port band. Boshqa port bilan ishga tushiring: PORT=8020 bash $0 $DOMAIN"
fi

say "Kerakli paketlar"
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq python3-venv certbot python3-certbot-nginx >/dev/null

say "Python muhiti (1-2 daqiqa)"
cd "$APP_DIR"
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt
mkdir -p data media var
chown -R www-data:www-data data media var

say ".env sozlamalari"
if [ ! -f .env ]; then
  KEY="$(python3 -c 'import secrets; print(secrets.token_urlsafe(50))')"
  cat > .env <<EOF
DEBUG=False
SECRET_KEY=$KEY
ALLOWED_HOSTS=$DOMAIN
CSRF_TRUSTED_ORIGINS=https://$DOMAIN
DATABASE_URL=sqlite:///$APP_DIR/data/db.sqlite3
SECURE_COOKIES=False
EOF
else
  echo ".env bor — o'zgartirilmadi"
fi
chown root:www-data .env
chmod 640 .env

say "Baza va statik fayllar"
sudo -u www-data .venv/bin/python manage.py migrate --noinput
.venv/bin/python manage.py collectstatic --noinput -v 0

say "Saytni ishga tushirish (systemd)"
cat > "/etc/systemd/system/$SERVICE.service" <<EOF
[Unit]
Description=Yozuvchi sayti (gunicorn)
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/.venv/bin/gunicorn config.wsgi:application --bind 127.0.0.1:$PORT --workers 2 --timeout 120
Restart=always

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --quiet "$SERVICE"
systemctl restart "$SERVICE"
sleep 3
curl -fsS -o /dev/null -H "Host: $DOMAIN" "http://127.0.0.1:$PORT/" \
  || die "Sayt ishga tushmadi. Sababini ko'rish: journalctl -u $SERVICE -n 50"

say "Nginx"
NGINX_CONF="/etc/nginx/sites-available/$SERVICE"
if [ ! -f "$NGINX_CONF" ]; then
  cat > "$NGINX_CONF" <<EOF
server {
    listen 80;
    server_name $DOMAIN;
    client_max_body_size 300M;

    location /static/ { alias $APP_DIR/staticfiles/; expires 30d; }
    location /media/  { alias $APP_DIR/media/; expires 7d; }

    location / {
        proxy_pass http://127.0.0.1:$PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 120s;
    }
}
EOF
fi
ln -sf "$NGINX_CONF" "/etc/nginx/sites-enabled/$SERVICE"
if ! nginx -t; then
  rm -f "/etc/nginx/sites-enabled/$SERVICE"
  die "Nginx sozlamasida xato. O'zgarish qaytarildi, boshqa saytlar ishlashda davom etadi."
fi
systemctl reload nginx

say "HTTPS (Let's Encrypt)"
if certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos --register-unsafely-without-email --redirect; then
  sed -i 's/^SECURE_COOKIES=.*/SECURE_COOKIES=True/' .env
  systemctl restart "$SERVICE"
  URL="https://$DOMAIN"
else
  echo "Diqqat: HTTPS olinmadi. Domen hali server IP'siga ishora qilmayotgan bo'lishi mumkin."
  echo "Keyinroq qayta urining: certbot --nginx -d $DOMAIN"
  URL="http://$DOMAIN"
fi

say "Panel uchun admin"
HAS_ADMIN="$(sudo -u www-data .venv/bin/python manage.py shell -v 0 -c \
  'from django.contrib.auth import get_user_model; print(get_user_model().objects.filter(is_staff=True).exists())' | tail -n 1)"
if [ "$HAS_ADMIN" = "True" ]; then
  echo "Admin allaqachon bor"
else
  echo "Login (username) va parol o'ylab toping. Parol yozilayotganda ekranda ko'rinmaydi."
  sudo -u www-data .venv/bin/python manage.py createsuperuser
fi

say "Tayyor"
echo "Sayt:  $URL/"
echo "Panel: $URL/panel/"
