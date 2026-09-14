# config.py - Конфигурация приложения
import os  # Импорт модуля для работы с переменными окружения

class Config:
    """Базовый класс конфигурации"""
    
    # Секретный ключ для сессий и CSRF-защиты
    # В продакшене должен быть сложным и храниться в переменных окружения
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Путь к базе данных SQLite (для разработки на Windows)
    # В продакшене замените на PostgreSQL или MySQL
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'site.db')
    
    # Отключаем отслеживание модификаций для экономии памяти
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
       # === Директории файлового менеджера ===

    # Базовая директория проекта
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))

    # Куда складывать загруженные файлы
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')

    # Куда складывать архивы
    ARCHIVE_FOLDER = os.path.join(BASE_DIR, 'archives')

    # Максимальный размер одного файла — 32 МБ
    MAX_CONTENT_LENGTH = 32 * 1024 * 1024

    # Разрешённые расширения (пустой список = разрешить все)
    ALLOWED_EXTENSIONS = set()
    
    # === Пагинация ===
    ARTICLES_PER_PAGE = 10      # статей в админке на странице
    FILES_PER_PAGE = 20         # файлов на странице
    USERS_PER_PAGE = 20         # пользователей на странице
    PUBLIC_ARTICLES_PER_PAGE = 6  # статей на главной (публично)
    ALBUMS_PER_PAGE = 12