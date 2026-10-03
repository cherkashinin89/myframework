# Развёртывание MyFramework

## Требования

- **ОС:** Debian 12 / Ubuntu 22.04 LTS (x86_64 или ARM)
- **Пользователь:** `admin` с правами `sudo`
- **Пакеты:** `git`, `python3.11`, `python3.11-venv`
- **Диск:** `/mnt/backup` (для бэкапов, опционально)

## Быстрый старт

```bash
# 1. Клонировать репозиторий
cd /home/admin/apps
git clone git@github.com:cherkashinin89/myframework.git

# 2. Настроить .env
cd myframework
cp deploy/env.example .env
nano .env  # заполнить SECRET_KEY, EXTERNAL_BACKUP_PATH

# 3. Запустить развёртывание
chmod +x deploy/setup.sh
./deploy/setup.sh