# models.py - Модели базы данных
from datetime import datetime           # Для работы с датами
from flask_login import UserMixin       # Миксин для модели пользователя
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db               # Импорт экземпляра БД
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db

# Промежуточная таблица для связи пользователей и статей (авторы)
article_authors = db.Table('article_authors',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('article_id', db.Integer, db.ForeignKey('article.id'), primary_key=True)
)

class User(UserMixin, db.Model):
    """Модель пользователя системы"""
    
    # Уникальный идентификатор пользователя
    id = db.Column(db.Integer, primary_key=True)
    
    # Имя пользователя (уникальное, обязательно)
    username = db.Column(db.String(80), unique=True, nullable=False)
    
    # Email (уникальный, обязательно)
    email = db.Column(db.String(120), unique=True, nullable=False)
    
    # Хэш пароля (никогда не храним пароль в открытом виде!)
    password_hash = db.Column(db.String(256), nullable=False)
    
    # Флаг администратора
    is_admin = db.Column(db.Boolean, default=False)
    
    # Дата регистрации
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Связь со статьями (автор может иметь много статей)
    articles = db.relationship('Article', secondary=article_authors, 
                               backref='authors', lazy='dynamic')
    
    def set_password(self, password):
        """Установка пароля с хэшированием"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Проверка пароля"""
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        """Строковое представление для отладки"""
        return f'<User {self.username}>'


class Article(db.Model):
    """Модель статьи"""
    
    # Уникальный идентификатор статьи
    id = db.Column(db.Integer, primary_key=True)
    
    # Заголовок статьи
    title = db.Column(db.String(200), nullable=False)
    
    # Содержимое статьи (текст)
    content = db.Column(db.Text, nullable=False)
    
    # Краткое описание для анонса
    summary = db.Column(db.String(500))
    
    # Дата создания
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Дата последнего обновления
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Флаг публикации (черновик или опубликовано)
    is_published = db.Column(db.Boolean, default=False)
    
    def __repr__(self):
        return f'<Article {self.title}>'


class Page(db.Model):
    """Модель статической страницы"""
    
    # Уникальный идентификатор страницы
    id = db.Column(db.Integer, primary_key=True)
    
    # Название страницы
    title = db.Column(db.String(200), nullable=False)
    
    # URL-адрес страницы (уникальный)
    slug = db.Column(db.String(200), unique=True, nullable=False)
    
    # Содержимое страницы (HTML)
    content = db.Column(db.Text, nullable=False)
    
    # Дата создания
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Page {self.title}>'


class MenuItem(db.Model):
    """Модель пункта меню"""
    
    # Уникальный идентификатор пункта меню
    id = db.Column(db.Integer, primary_key=True)
    
    # Отображаемое название
    title = db.Column(db.String(100), nullable=False)
    
    # URL-адрес ссылки
    url = db.Column(db.String(200), nullable=False)
    
    # Порядок сортировки в меню
    order = db.Column(db.Integer, default=0)
    
    # Позиция меню: 'header', 'sidebar', 'footer'
    position = db.Column(db.String(20), default='header')
    
    # Родительский пункт (для вложенных меню)
    parent_id = db.Column(db.Integer, db.ForeignKey('menu_item.id'), nullable=True)
    
    # Связь с дочерними пунктами
    children = db.relationship('MenuItem', backref=db.backref('parent', remote_side=[id]),
                               lazy='dynamic')
    
    def __repr__(self):
        return f'<MenuItem {self.title}>'
        
class UploadedFile(db.Model):
    """Модель загруженного файла (метаданные)"""

    # Уникальный идентификатор
    id = db.Column(db.Integer, primary_key=True)

    # Оригинальное имя файла (как назвал пользователь)
    original_name = db.Column(db.String(255), nullable=False)

    # Уникальное имя файла на диске (чтобы не было коллизий)
    stored_name = db.Column(db.String(255), unique=True, nullable=False)

    # MIME-тип (например, image/jpeg, application/pdf)
    mime_type = db.Column(db.String(120))

    # Категория файла: image, video, audio, document, archive, other
    file_type = db.Column(db.String(30), nullable=False, default='other')

    # Размер файла в байтах
    size = db.Column(db.Integer, nullable=False, default=0)

    # Расширение файла (без точки): jpg, pdf, mp4
    extension = db.Column(db.String(20))

    # Дата загрузки
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    # Кто загрузил (внешний ключ на пользователя)
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    uploaded_by = db.relationship('User', backref='uploaded_files')

    # Заметка/описание (необязательно)
    description = db.Column(db.String(500))

    def size_human(self):
        """Человекочитаемый размер: 1.2 MB, 340 KB и т.д."""
        size = self.size or 0
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f'{size:.1f} {unit}' if unit != 'B' else f'{size} {unit}'
            size /= 1024
        return f'{size:.1f} TB'

    def icon(self):
        """Иконка Bootstrap Icons в зависимости от типа"""
        return {
            'image': 'bi-file-earmark-image',
            'video': 'bi-file-earmark-play',
            'audio': 'bi-file-earmark-music',
            'document': 'bi-file-earmark-text',
            'archive': 'bi-file-earmark-zip',
            'other': 'bi-file-earmark'
        }.get(self.file_type, 'bi-file-earmark')

    def __repr__(self):
        return f'<UploadedFile {self.original_name}>'
        
# models.py - дополнение: Album и Photo

# Промежуточная таблица для связи статей и альбомов (many-to-many)
article_albums = db.Table('article_albums',
    db.Column('article_id', db.Integer, db.ForeignKey('article.id'), primary_key=True),
    db.Column('album_id', db.Integer, db.ForeignKey('album.id'), primary_key=True)
)


class Album(db.Model):
    """Фотоальбом (каталог фотографий)"""

    id = db.Column(db.Integer, primary_key=True)

    # Название альбома (тема)
    title = db.Column(db.String(200), nullable=False)

    # URL-идентификатор: /gallery/<slug>
    slug = db.Column(db.String(200), unique=True, nullable=False, index=True)

    # Описание (необязательно)
    description = db.Column(db.Text)

    # ID обложки — ссылается на Photo (обложку выбираем вручную)
    cover_photo_id = db.Column(db.Integer, db.ForeignKey('photo.id', use_alter=True,
                                                         name='fk_album_cover'))
    cover_photo = db.relationship('Photo', foreign_keys=[cover_photo_id], post_update=True)

    # Флаг публикации: скрытые альбомы не видны на публичной части
    is_published = db.Column(db.Boolean, default=True, index=True)

    # Порядок сортировки в списке
    order = db.Column(db.Integer, default=0)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    # Связь с фотографиями (удаляются каскадом при удалении альбома)
    photos = db.relationship('Photo', backref='album',
                             cascade='all, delete-orphan',
                             foreign_keys='Photo.album_id',
                             order_by='Photo.order')

    # Связь со статьями (many-to-many)
    articles = db.relationship('Article', secondary=article_albums,
                               backref=db.backref('albums', lazy='dynamic'))

    def __repr__(self):
        return f'<Album {self.title}>'


class Photo(db.Model):
    """Фотография в альбоме — ссылка на UploadedFile"""

    id = db.Column(db.Integer, primary_key=True)

    # К какому альбому относится
    album_id = db.Column(db.Integer, db.ForeignKey('album.id'), nullable=False)

    # Какой файл из файлового менеджера используется
    file_id = db.Column(db.Integer, db.ForeignKey('uploaded_file.id'), nullable=False)
    file = db.relationship('UploadedFile')

    # Подпись (необязательно)
    caption = db.Column(db.String(300))

    # Порядок сортировки внутри альбома
    order = db.Column(db.Integer, default=0)

    added_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Photo {self.id} in {self.album_id}>'