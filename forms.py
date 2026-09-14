# forms.py - Формы приложения
from flask_wtf import FlaskForm                    # Базовый класс формы
from wtforms import StringField, PasswordField, TextAreaField, BooleanField, SelectField, IntegerField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import (StringField, PasswordField, TextAreaField, BooleanField,
                     SelectField, IntegerField, DateField, SubmitField)
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional, Regexp
from datetime import date
# forms.py - дополнение
from wtforms import (StringField, TextAreaField, BooleanField,
                     SelectMultipleField, SelectField, IntegerField, SubmitField)
from wtforms.validators import DataRequired, Length, Optional

class LoginForm(FlaskForm):
    """Форма входа в систему"""
    
    # Поле имени пользователя
    username = StringField('Имя пользователя', 
                           validators=[DataRequired(message='Введите имя пользователя')])
    
    # Поле пароля
    password = PasswordField('Пароль', 
                             validators=[DataRequired(message='Введите пароль')])


class UserForm(FlaskForm):
    """Форма создания/редактирования пользователя"""
    
    username = StringField('Имя пользователя', 
                           validators=[DataRequired(), Length(min=3, max=80)])
    
    email = StringField('Email', 
                        validators=[DataRequired(), Email()])
    
    password = PasswordField('Пароль', 
                             validators=[DataRequired(), Length(min=6)])
    
    confirm_password = PasswordField('Подтвердите пароль',
                                     validators=[DataRequired(), EqualTo('password')])
    
    is_admin = BooleanField('Администратор')


class ArticleForm(FlaskForm):
    """Форма создания/редактирования статьи"""
    
    title = StringField('Заголовок', 
                        validators=[DataRequired(), Length(max=200)])
    
    summary = TextAreaField('Краткое описание', 
                            validators=[Optional(), Length(max=500)])
    
    content = TextAreaField('Содержимое', 
                            validators=[DataRequired()])
    
    is_published = BooleanField('Опубликовать')


class PageForm(FlaskForm):
    """Форма создания/редактирования страницы"""
    
    title = StringField('Название', 
                        validators=[DataRequired(), Length(max=200)])
    
    slug = StringField('URL (slug)', 
                       validators=[DataRequired(), Length(max=200)])
    
    content = TextAreaField('Содержимое (HTML)', 
                            validators=[DataRequired()])


class MenuItemForm(FlaskForm):
    """Форма создания/редактирования пункта меню"""
    
    title = StringField('Название', 
                        validators=[DataRequired(), Length(max=100)])
    
    url = StringField('URL', 
                      validators=[DataRequired(), Length(max=200)])
    
    order = IntegerField('Порядок', default=0)
    
    position = SelectField('Позиция', 
                           choices=[('header', 'Шапка'), 
                                   ('sidebar', 'Боковое меню'), 
                                   ('footer', 'Подвал')])
    
    parent_id = SelectField('Родительский пункт', coerce=int, validators=[Optional()])
    
# forms.py - Формы приложения
from flask_wtf import FlaskForm
from wtforms import (StringField, PasswordField, TextAreaField, BooleanField,
                     SelectField, IntegerField)
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional


class LoginForm(FlaskForm):
    """Форма входа в систему"""
    username = StringField('Имя пользователя',
                           validators=[DataRequired(message='Введите имя пользователя')])
    password = PasswordField('Пароль',
                             validators=[DataRequired(message='Введите пароль')])


class UserForm(FlaskForm):
    """Форма создания/редактирования пользователя.
    
    При создании пароль обязателен. При редактировании — необязателен
    (если пусто, пароль не меняется).
    """
    username = StringField('Имя пользователя',
                           validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField('Email',
                        validators=[DataRequired(), Email()])
    
    # Пароль: проверка необязательности выполняется вручную в маршруте
    password = PasswordField('Пароль')
    confirm_password = PasswordField('Подтвердите пароль',
                                     validators=[Optional(), EqualTo('password',
                                     message='Пароли должны совпадать')])
    is_admin = BooleanField('Администратор')


class ArticleForm(FlaskForm):
    """Форма создания/редактирования статьи"""
    title = StringField('Заголовок',
                        validators=[DataRequired(), Length(max=200)])
    summary = TextAreaField('Краткое описание',
                            validators=[Optional(), Length(max=500)])
    content = TextAreaField('Содержимое',
                            validators=[DataRequired()])
    is_published = BooleanField('Опубликовать')


class PageForm(FlaskForm):
    """Форма создания/редактирования страницы"""
    title = StringField('Название',
                        validators=[DataRequired(), Length(max=200)])
    slug = StringField('URL (slug)',
                       validators=[DataRequired(), Length(max=200)])
    content = TextAreaField('Содержимое (HTML)',
                            validators=[DataRequired()])


class MenuItemForm(FlaskForm):
    """Форма создания/редактирования пункта меню"""
    title = StringField('Название',
                        validators=[DataRequired(), Length(max=100)])
    url = StringField('URL',
                      validators=[DataRequired(), Length(max=200)])
    order = IntegerField('Порядок', default=0)
    position = SelectField('Позиция',
                           choices=[('header', 'Шапка'),
                                    ('sidebar', 'Боковое меню'),
                                    ('footer', 'Подвал')])
    # parent_id — выпадающий список существующих пунктов (coerce=int)
    parent_id = SelectField('Родительский пункт', coerce=int, validators=[Optional()])
    
class UploadFileForm(FlaskForm):
    """Форма загрузки файла"""

    # Файл — обязателен
    file = FileField('Файл', validators=[FileRequired(message='Выберите файл')])

    # Описание (необязательно)
    description = StringField('Описание', validators=[Optional(), Length(max=500)])

    submit = SubmitField('Загрузить')


class ArchiveForm(FlaskForm):
    """Форма архивации файлов за период"""

    # Начало периода (по умолчанию — 30 дней назад)
    date_from = DateField('Дата с',
                          default=lambda: date.today().replace(day=1),
                          validators=[DataRequired()])

    # Конец периода (по умолчанию — сегодня)
    date_to = DateField('Дата по',
                        default=date.today,
                        validators=[DataRequired()])

    # Фильтр по типу (все / конкретный)
    file_type = SelectField('Тип файлов', choices=[
        ('all', 'Все типы'),
        ('image', 'Изображения'),
        ('video', 'Видео'),
        ('audio', 'Аудио'),
        ('document', 'Документы'),
        ('archive', 'Архивы'),
        ('other', 'Прочее'),
    ], default='all')

    # Формат архива: zip или tar.gz
    archive_format = SelectField('Формат', choices=[
        ('zip', 'ZIP (.zip)'),
        ('targz', 'TAR.GZ (.tar.gz)'),
    ], default='zip')

    # Удалять ли исходные файлы после архивации
    delete_after = BooleanField('Удалить исходные файлы после архивации')

    submit = SubmitField('Создать архив')
    
class AlbumForm(FlaskForm):
    """Форма создания/редактирования альбома"""
    title = StringField('Название альбома',
                        validators=[DataRequired(), Length(max=200)])
    slug = StringField('URL (slug)',
                       validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Описание', validators=[Optional()])
    is_published = BooleanField('Опубликовать', default=True)
    order = IntegerField('Порядок сортировки', default=0)
    submit = SubmitField('Сохранить')


class AlbumPhotosForm(FlaskForm):
    """Форма массового добавления фото в альбом из файлового менеджера"""
    file_ids = SelectMultipleField('Файлы', coerce=int, validators=[Optional()])
    submit = SubmitField('Добавить выбранные')