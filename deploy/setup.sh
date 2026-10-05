#!/bin/bash
# ================================================================
# deploy/setup.sh — развёртывание myframework на чистом сервере
# ================================================================
# Требования:
#   - Debian 12 / Ubuntu 22.04 LTS
#   - Пользователь deploy с sudo
#   - git, python3, python3-venv
# ================================================================

set -e  # прервать при ошибке

APP_NAME="myframework"
APP_DIR="/home/deploy/apps/myframework"
VENV_DIR="$APP_DIR/venv"
SERVICE_USER="${SERVICE_USER:-$(whoami)}"

echo "=== SERVICE_USER = $SERVICE_USER ==="

echo "=== Развёртывание $APP_NAME ==="

# === 1. Проверки ===
if [ ! -d "$APP_DIR" ]; then
    echo "Ошибка: $APP_DIR не найден. Склонируйте репозиторий туда."
    exit 1
fi

if [ ! -f "$APP_DIR/.env" ]; then
    echo "Ошибка: $APP_DIR/.env не найден. Скопируйте env.example в .env и заполните."
    exit 1
fi

# === 2. Системные пакеты ===
echo "=== Установка системных пакетов ==="
sudo apt update
sudo apt install -y \
    python3 python3-venv python3-pip \
    nginx \
    git \
    sqlite3

# === 3. Виртуальное окружение ===
echo "=== Создание venv ==="
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
fi
source "$VENV_DIR/bin/activate"

# === 4. Зависимости Python ===
echo "=== Установка Python-зависимостей ==="
pip install --upgrade pip
pip install -r "$APP_DIR/requirements.txt"

# === 5. Миграции БД ===
echo "=== Применение миграций ==="
cd "$APP_DIR"
flask db upgrade

# === 6. Nginx ===
echo "=== Настройка Nginx ==="
sudo cp "$APP_DIR/deploy/nginx/$APP_NAME.conf" "/etc/nginx/sites-available/$APP_NAME"
sudo ln -sf "/etc/nginx/sites-available/$APP_NAME" "/etc/nginx/sites-enabled/$APP_NAME"
sudo nginx -t
sudo systemctl reload nginx

# === 7. systemd ===
echo "=== Настройка systemd ==="
tmp_service="$(mktemp)"
sed "s|__SERVICE_USER__|$SERVICE_USER|g" \
    "$APP_DIR/deploy/systemd/$APP_NAME.service" > "$tmp_service"
sudo cp "$tmp_service" "/etc/systemd/system/$APP_NAME.service"
rm -f "$tmp_service"
sudo systemctl daemon-reload
sudo systemctl enable "$APP_NAME"
sudo systemctl restart "$APP_NAME"

# === 8. sudoers ===
echo "=== Настройка sudoers ==="
for f in "$APP_DIR/deploy/sudoers/"*; do
    name=$(basename "$f")
    tmp_sudoers="$(mktemp)"
    sed "s|__SERVICE_USER__|$SERVICE_USER|g" "$f" > "$tmp_sudoers"
    sudo cp "$tmp_sudoers" "/etc/sudoers.d/$name"
    sudo chmod 0440 "/etc/sudoers.d/$name"
    sudo chown root:root "/etc/sudoers.d/$name"
    rm -f "$tmp_sudoers"
done
sudo visudo -c

# === 9. Проверка ===
echo "=== Проверка ==="
sudo systemctl status "$APP_NAME" --no-pager | head -10
curl -I http://127.0.0.1:5000/ || true

echo ""
echo "=== Готово! ==="
echo "Сервис: sudo systemctl status $APP_NAME"
echo "Логи:   sudo journalctl -u $APP_NAME -f"
echo "Сайт:   http://<IP или домен>/"