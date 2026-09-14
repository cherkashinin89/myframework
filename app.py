# app.py - Основной файл приложения
import os
from datetime import datetime

from flask import (
    Flask, render_template, redirect, url_for, flash, request,
    jsonify, send_from_directory
)
from flask_login import (
    login_user, logout_user, login_required, current_user
)

from config import Config
from extensions import db, login_manager, csrf, migrate
from models import User, Article, Page, MenuItem, UploadedFile, Album, Photo
from forms import (
    LoginForm, UserForm, ArticleForm, PageForm, MenuItemForm,
    UploadFileForm, ArchiveForm, AlbumForm, AlbumPhotosForm
)
from file_utils import (
    get_file_type, guess_mime, make_stored_name,
    human_size, create_archive
)

# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===

def get_page():
    """Возвращает номер страницы из ?page=... (минимум 1)"""
    try:
        return max(1, int(request.args.get('page', 1)))
    except (TypeError, ValueError):
        return 1


# === ФАБРИКА ПРИЛОЖЕНИЯ ===

def create_app(config_class=Config):
    """Создаёт и настраивает экземпляр Flask"""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Инициализация расширений
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)

    # Фильтр Jinja для размеров файлов
    app.jinja_env.filters['human_size_bytes'] = human_size

    # Загрузчик пользователя для Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # === ПУБЛИЧНЫЕ МАРШРУТЫ ===

    @app.route('/')
    def index():
        """Главная страница сайта с пагинацией статей"""
        page = get_page()
        per_page = app.config['PUBLIC_ARTICLES_PER_PAGE']

        pagination = (
            Article.query
            .filter_by(is_published=True)
            .order_by(Article.created_at.desc())
            .paginate(page=page, per_page=per_page, error_out=False)
        )

        header_menu = (
            MenuItem.query
            .filter_by(position='header', parent_id=None)
            .order_by(MenuItem.order)
            .all()
        )
        sidebar_menu = (
            MenuItem.query
            .filter_by(position='sidebar', parent_id=None)
            .order_by(MenuItem.order)
            .all()
        )

        return render_template(
            'index.html',
            pagination=pagination,
            articles=pagination.items,
            header_menu=header_menu,
            sidebar_menu=sidebar_menu
        )

    @app.route('/page/<slug>')
    def show_page(slug):
        """Отображение статической страницы по slug"""
        page = Page.query.filter_by(slug=slug).first_or_404()
        return render_template('page.html', page=page)

    @app.route('/article/<int:id>')
    def show_article(id):
        """Отображение статьи по ID"""
        article = Article.query.get_or_404(id)
        return render_template('article.html', article=article)

    @app.route('/uploads/<path:filename>')
    def uploaded_file(filename):
        """Публичная отдача файлов из uploads/"""
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    # === АУТЕНТИФИКАЦИЯ ===

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        """Страница входа в систему"""
        if current_user.is_authenticated:
            return redirect(url_for('admin_dashboard'))

        form = LoginForm()

        if form.validate_on_submit():
            user = User.query.filter_by(username=form.username.data).first()

            if user and user.check_password(form.password.data):
                login_user(user)
                flash('Вы успешно вошли в систему!', 'success')
                next_page = request.args.get('next')
                return redirect(next_page or url_for('admin_dashboard'))

            flash('Неверное имя пользователя или пароль', 'danger')

        return render_template('login.html', form=form)

    @app.route('/logout')
    @login_required
    def logout():
        """Выход из системы"""
        logout_user()
        flash('Вы вышли из системы', 'info')
        return redirect(url_for('index'))

    # === АДМИН-ПАНЕЛЬ ===

    @app.route('/admin/')
    @login_required
    def admin_dashboard():
        """Главная страница админ-панели"""
        stats = {
            'users': User.query.count(),
            'articles': Article.query.count(),
            'pages': Page.query.count(),
            'menu_items': MenuItem.query.count(),
            'files': UploadedFile.query.count(),
            'albums': Album.query.count(),
        }
        # Последние альбомы для мини-обзора
        recent_albums = (
            Album.query
            .order_by(Album.created_at.desc())
            .limit(4)
            .all()
        )
        
        print(f'[DASHBOARD] recent_albums: {len(recent_albums)} шт.')   # ← отладка
        
        return render_template('admin/dashboard.html',
                               stats=stats,
                               recent_albums=recent_albums)

    # --- Управление пользователями ---

    @app.route('/admin/users/')
    @login_required
    def admin_users():
        """Список пользователей с пагинацией"""
        if not current_user.is_admin:
            flash('Доступ запрещён', 'danger')
            return redirect(url_for('admin_dashboard'))

        page = get_page()
        per_page = app.config['USERS_PER_PAGE']

        pagination = (
            User.query
            .order_by(User.created_at.desc())
            .paginate(page=page, per_page=per_page, error_out=False)
        )

        return render_template(
            'admin/users.html',
            pagination=pagination,
            users=pagination.items
        )

    @app.route('/admin/users/create', methods=['GET', 'POST'])
    @login_required
    def admin_user_create():
        """Создание нового пользователя"""
        if not current_user.is_admin:
            flash('Доступ запрещён', 'danger')
            return redirect(url_for('admin_dashboard'))

        form = UserForm()

        if form.validate_on_submit():
            if User.query.filter_by(username=form.username.data).first():
                flash('Пользователь с таким именем уже существует!', 'danger')
                return render_template(
                    'admin/user_form.html',
                    form=form,
                    title='Создание пользователя'
                )

            if User.query.filter_by(email=form.email.data).first():
                flash('Пользователь с таким email уже существует!', 'danger')
                return render_template(
                    'admin/user_form.html',
                    form=form,
                    title='Создание пользователя'
                )

            if not form.password.data or len(form.password.data) < 6:
                flash('Пароль должен содержать минимум 6 символов!', 'danger')
                return render_template(
                    'admin/user_form.html',
                    form=form,
                    title='Создание пользователя'
                )

            user = User(
                username=form.username.data,
                email=form.email.data,
                is_admin=form.is_admin.data
            )
            user.set_password(form.password.data)

            db.session.add(user)
            db.session.commit()

            flash(f'Пользователь {user.username} создан!', 'success')
            return redirect(url_for('admin_users'))

        return render_template(
            'admin/user_form.html',
            form=form,
            title='Создание пользователя'
        )

    @app.route('/admin/users/<int:id>/edit', methods=['GET', 'POST'])
    @login_required
    def admin_user_edit(id):
        """Редактирование пользователя"""
        if not current_user.is_admin:
            flash('Доступ запрещён', 'danger')
            return redirect(url_for('admin_dashboard'))

        user = User.query.get_or_404(id)
        form = UserForm(obj=user)

        if form.validate_on_submit():
            existing_username = User.query.filter(
                User.username == form.username.data,
                User.id != user.id
            ).first()
            if existing_username:
                flash('Пользователь с таким именем уже существует!', 'danger')
                return render_template(
                    'admin/user_form.html',
                    form=form,
                    title=f'Редактирование: {user.username}',
                    user=user
                )

            existing_email = User.query.filter(
                User.email == form.email.data,
                User.id != user.id
            ).first()
            if existing_email:
                flash('Пользователь с таким email уже существует!', 'danger')
                return render_template(
                    'admin/user_form.html',
                    form=form,
                    title=f'Редактирование: {user.username}',
                    user=user
                )

            user.username = form.username.data
            user.email = form.email.data
            user.is_admin = form.is_admin.data

            if form.password.data:
                if len(form.password.data) < 6:
                    flash('Пароль должен содержать минимум 6 символов!', 'danger')
                    return render_template(
                        'admin/user_form.html',
                        form=form,
                        title=f'Редактирование: {user.username}',
                        user=user
                    )
                user.set_password(form.password.data)

            db.session.commit()
            flash(f'Пользователь «{user.username}» обновлён!', 'success')
            return redirect(url_for('admin_users'))

        return render_template(
            'admin/user_form.html',
            form=form,
            title=f'Редактирование: {user.username}',
            user=user
        )

    @app.route('/admin/users/<int:id>/delete', methods=['POST'])
    @login_required
    def admin_user_delete(id):
        """Удаление пользователя"""
        if not current_user.is_admin:
            flash('Доступ запрещён', 'danger')
            return redirect(url_for('admin_dashboard'))

        user = User.query.get_or_404(id)

        if user.id == current_user.id:
            flash('Нельзя удалить собственную учётную запись!', 'danger')
            return redirect(url_for('admin_users'))

        username = user.username
        db.session.delete(user)
        db.session.commit()

        flash(f'Пользователь «{username}» удалён.', 'info')
        return redirect(url_for('admin_users'))

    # --- Управление статьями ---

    @app.route('/admin/articles/')
    @login_required
    def admin_articles():
        """Список статей с пагинацией"""
        page = get_page()
        per_page = app.config['ARTICLES_PER_PAGE']

        pagination = (
            Article.query
            .order_by(Article.created_at.desc())
            .paginate(page=page, per_page=per_page, error_out=False)
        )

        return render_template(
            'admin/articles.html',
            pagination=pagination,
            articles=pagination.items
        )

    @app.route('/admin/articles/create', methods=['GET', 'POST'])
    @login_required
    def admin_article_create():
        form = ArticleForm()

        if form.validate_on_submit():
            article = Article(
                title=form.title.data,
                content=form.content.data,
                summary=form.summary.data,
                is_published=form.is_published.data
            )
            article.authors.append(current_user)

            # Привязка альбомов
            album_ids = request.form.getlist('album_ids', type=int)
            for aid in album_ids:
                album = Album.query.get(aid)
                if album:
                    article.albums.append(album)

            db.session.add(article)
            db.session.commit()
            flash('Статья создана!', 'success')
            return redirect(url_for('admin_articles'))

        # Список всех альбомов для чекбоксов
        all_albums = Album.query.order_by(Album.title).all()
        return render_template('admin/article_form.html',
                               form=form,
                               all_albums=all_albums,
                               selected_album_ids=[],
                               title='Создание статьи')

    @app.route('/admin/articles/<int:id>/edit', methods=['GET', 'POST'])
    @login_required
    def admin_article_edit(id):
        """Редактирование существующей статьи"""
        article = Article.query.get_or_404(id)
        form = ArticleForm(obj=article)

        if form.validate_on_submit():
            article.title = form.title.data
            article.summary = form.summary.data
            article.content = form.content.data
            article.is_published = form.is_published.data

            # Пересобираем привязки альбомов
            article.albums = []  # очистить
            album_ids = request.form.getlist('album_ids', type=int)
            for aid in album_ids:
                album = Album.query.get(aid)
                if album:
                    article.albums.append(album)

            db.session.commit()
            flash(f'Статья «{article.title}» обновлена!', 'success')
            return redirect(url_for('admin_articles'))

        all_albums = Album.query.order_by(Album.title).all()
        selected_album_ids = [a.id for a in article.albums]
        return render_template('admin/article_form.html',
                               form=form,
                               article=article,
                               all_albums=all_albums,
                               selected_album_ids=selected_album_ids,
                               title=f'Редактирование: {article.title}')

    @app.route('/admin/articles/<int:id>/delete', methods=['POST'])
    @login_required
    def admin_article_delete(id):
        """Удаление статьи"""
        article = Article.query.get_or_404(id)
        article_title = article.title

        db.session.delete(article)
        db.session.commit()

        flash(f'Статья «{article_title}» удалена.', 'info')
        return redirect(url_for('admin_articles'))

    # --- Управление страницами ---

    @app.route('/admin/pages/')
    @login_required
    def admin_pages():
        """Список страниц"""
        pages = Page.query.all()
        return render_template('admin/pages.html', pages=pages)

    @app.route('/admin/pages/create', methods=['GET', 'POST'])
    @login_required
    def admin_page_create():
        """Создание новой страницы"""
        form = PageForm()

        if form.validate_on_submit():
            page = Page(
                title=form.title.data,
                slug=form.slug.data,
                content=form.content.data
            )

            db.session.add(page)
            db.session.commit()

            flash('Страница создана!', 'success')
            return redirect(url_for('admin_pages'))

        return render_template(
            'admin/page_form.html',
            form=form,
            title='Создание страницы'
        )

    @app.route('/admin/pages/<int:id>/edit', methods=['GET', 'POST'])
    @login_required
    def admin_page_edit(id):
        """Редактирование существующей страницы"""
        page = Page.query.get_or_404(id)
        form = PageForm(obj=page)

        if form.validate_on_submit():
            existing = Page.query.filter(
                Page.slug == form.slug.data,
                Page.id != page.id
            ).first()
            if existing:
                flash('Страница с таким URL уже существует!', 'danger')
                return render_template(
                    'admin/page_form.html',
                    form=form,
                    title=f'Редактирование: {page.title}'
                )

            page.title = form.title.data
            page.slug = form.slug.data
            page.content = form.content.data

            db.session.commit()
            flash(f'Страница «{page.title}» обновлена!', 'success')
            return redirect(url_for('admin_pages'))

        return render_template(
            'admin/page_form.html',
            form=form,
            title=f'Редактирование: {page.title}',
            page=page
        )

    @app.route('/admin/pages/<int:id>/delete', methods=['POST'])
    @login_required
    def admin_page_delete(id):
        """Удаление страницы"""
        page = Page.query.get_or_404(id)
        page_title = page.title

        db.session.delete(page)
        db.session.commit()

        flash(f'Страница «{page_title}» удалена.', 'info')
        return redirect(url_for('admin_pages'))

    # --- Управление меню ---

    @app.route('/admin/menu/')
    @login_required
    def admin_menu():
        """Список пунктов меню"""
        menu_items = (
            MenuItem.query
            .order_by(MenuItem.position, MenuItem.order)
            .all()
        )
        return render_template('admin/menu.html', menu_items=menu_items)

    @app.route('/admin/menu/create', methods=['GET', 'POST'])
    @login_required
    def admin_menu_create():
        """Создание пункта меню"""
        form = MenuItemForm()

        parents = (
            MenuItem.query
            .order_by(MenuItem.position, MenuItem.order)
            .all()
        )
        form.parent_id.choices = (
            [(0, '— без родителя —')] +
            [(p.id, f'[{p.position}] {p.title}') for p in parents]
        )

        if form.validate_on_submit():
            menu_item = MenuItem(
                title=form.title.data,
                url=form.url.data,
                order=form.order.data,
                position=form.position.data,
                parent_id=form.parent_id.data if form.parent_id.data else None
            )

            db.session.add(menu_item)
            db.session.commit()

            flash('Пункт меню создан!', 'success')
            return redirect(url_for('admin_menu'))

        return render_template(
            'admin/menu_form.html',
            form=form,
            title='Создание пункта меню'
        )

    @app.route('/admin/menu/<int:id>/edit', methods=['GET', 'POST'])
    @login_required
    def admin_menu_edit(id):
        """Редактирование пункта меню"""
        item = MenuItem.query.get_or_404(id)
        form = MenuItemForm(obj=item)

        parents = (
            MenuItem.query
            .filter(MenuItem.id != item.id)
            .order_by(MenuItem.position, MenuItem.order)
            .all()
        )
        form.parent_id.choices = (
            [(0, '— без родителя —')] +
            [(p.id, f'[{p.position}] {p.title}') for p in parents]
        )

        if form.validate_on_submit():
            item.title = form.title.data
            item.url = form.url.data
            item.position = form.position.data
            item.order = form.order.data
            item.parent_id = form.parent_id.data if form.parent_id.data else None

            db.session.commit()
            flash(f'Пункт меню «{item.title}» обновлён!', 'success')
            return redirect(url_for('admin_menu'))

        if request.method == 'GET':
            form.parent_id.data = item.parent_id or 0

        return render_template(
            'admin/menu_form.html',
            form=form,
            title=f'Редактирование: {item.title}',
            item=item
        )

    @app.route('/admin/menu/<int:id>/delete', methods=['POST'])
    @login_required
    def admin_menu_delete(id):
        """Удаление пункта меню"""
        item = MenuItem.query.get_or_404(id)

        for child in item.children:
            child.parent_id = None

        title = item.title
        db.session.delete(item)
        db.session.commit()

        flash(f'Пункт меню «{title}» удалён.', 'info')
        return redirect(url_for('admin_menu'))

    # --- Файловый менеджер ---

    @app.route('/admin/files/')
    @login_required
    def admin_files():
        """Список файлов с пагинацией, сортировкой и фильтром"""
        page = get_page()
        per_page = app.config['FILES_PER_PAGE']

        sort_by = request.args.get('sort', 'uploaded_at')
        direction = request.args.get('dir', 'desc')
        type_filter = request.args.get('type', 'all')

        allowed_sort = {'original_name', 'file_type', 'size', 'uploaded_at'}
        if sort_by not in allowed_sort:
            sort_by = 'uploaded_at'
        if direction not in ('asc', 'desc'):
            direction = 'desc'

        query = UploadedFile.query
        if type_filter != 'all':
            query = query.filter(UploadedFile.file_type == type_filter)

        column = getattr(UploadedFile, sort_by)
        query = query.order_by(
            column.desc() if direction == 'desc' else column.asc()
        )

        pagination = query.paginate(
            page=page, per_page=per_page, error_out=False
        )

        type_counts = {'all': UploadedFile.query.count()}
        for t in ['image', 'video', 'audio', 'document', 'archive', 'other']:
            type_counts[t] = UploadedFile.query.filter_by(file_type=t).count()

        total_size = (
            db.session.query(db.func.sum(UploadedFile.size)).scalar() or 0
        )

        return render_template(
            'admin/files.html',
            pagination=pagination,
            files=pagination.items,
            sort_by=sort_by,
            direction=direction,
            type_filter=type_filter,
            type_counts=type_counts,
            total_size=total_size
        )

    @app.route('/admin/files/upload', methods=['POST'])
    @login_required
    def admin_file_upload():
        """Загрузка файла через обычную форму"""
        form = UploadFileForm()

        if form.validate_on_submit():
            file = form.file.data
            original_name = file.filename
            ext = os.path.splitext(original_name)[1].lstrip('.').lower()

            stored_name = make_stored_name(original_name)
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], stored_name)
            file.save(save_path)
            size = os.path.getsize(save_path)

            record = UploadedFile(
                original_name=original_name,
                stored_name=stored_name,
                mime_type=guess_mime(original_name),
                file_type=get_file_type(ext),
                size=size,
                extension=ext,
                uploaded_by_id=current_user.id,
                description=form.description.data or None
            )
            db.session.add(record)
            db.session.commit()

            flash(f'Файл «{original_name}» загружен.', 'success')
        else:
            for errors in form.errors.values():
                for err in errors:
                    flash(err, 'danger')

        return redirect(url_for('admin_files'))

    @app.route('/admin/files/<int:id>/download')
    @login_required
    def admin_file_download(id):
        """Скачивание файла"""
        record = UploadedFile.query.get_or_404(id)
        return send_from_directory(
            app.config['UPLOAD_FOLDER'],
            record.stored_name,
            as_attachment=True,
            download_name=record.original_name
        )

    @app.route('/admin/files/<int:id>/delete', methods=['POST'])
    @login_required
    def admin_file_delete(id):
        """Удаление файла"""
        record = UploadedFile.query.get_or_404(id)
        path = os.path.join(app.config['UPLOAD_FOLDER'], record.stored_name)

        if os.path.exists(path):
            os.remove(path)

        name = record.original_name
        db.session.delete(record)
        db.session.commit()

        flash(f'Файл «{name}» удалён.', 'info')
        return redirect(url_for('admin_files'))

    @app.route('/admin/files/archive', methods=['GET', 'POST'])
    @login_required
    def admin_files_archive():
        """Архивация файлов за указанный период"""
        form = ArchiveForm()

        if form.validate_on_submit():
            start = datetime.combine(form.date_from.data, datetime.min.time())
            end = datetime.combine(form.date_to.data, datetime.max.time())

            if start > end:
                flash('Дата начала позже даты окончания.', 'danger')
                return render_template('admin/archive_form.html', form=form)

            query = UploadedFile.query.filter(
                UploadedFile.uploaded_at >= start,
                UploadedFile.uploaded_at <= end
            )
            if form.file_type.data != 'all':
                query = query.filter(UploadedFile.file_type == form.file_type.data)

            files = query.all()

            if not files:
                flash('За указанный период файлов не найдено.', 'warning')
                return render_template('admin/archive_form.html', form=form)

            for f in files:
                f.stored_path = os.path.join(
                    app.config['UPLOAD_FOLDER'], f.stored_name
                )

            base_name = (
                f'archive_{form.date_from.data:%Y%m%d}_'
                f'{form.date_to.data:%Y%m%d}'
            )
            archive_path = create_archive(
                files,
                app.config['ARCHIVE_FOLDER'],
                base_name,
                fmt=form.archive_format.data,
                delete_after=form.delete_after.data
            )

            if form.delete_after.data:
                for f in files:
                    db.session.delete(f)
                db.session.commit()

            flash(
                f'Архив создан: {os.path.basename(archive_path)} '
                f'({len(files)} файлов).',
                'success'
            )

            return send_from_directory(
                app.config['ARCHIVE_FOLDER'],
                os.path.basename(archive_path),
                as_attachment=True
            )

        return render_template('admin/archive_form.html', form=form)

    # === ПУБЛИЧНАЯ ГАЛЕРЕЯ ===

    @app.route('/gallery')
    def gallery_index():
        """Список опубликованных альбомов"""
        page = get_page()
        per_page = app.config.get('ALBUMS_PER_PAGE', 12)

        pagination = (
            Album.query
            .filter_by(is_published=True)
            .order_by(Album.order.asc(), Album.created_at.desc())
            .paginate(page=page, per_page=per_page, error_out=False)
        )

        # Меню — как везде
        header_menu = MenuItem.query.filter_by(position='header', parent_id=None)\
            .order_by(MenuItem.order).all()
        sidebar_menu = MenuItem.query.filter_by(position='sidebar', parent_id=None)\
            .order_by(MenuItem.order).all()

        return render_template('gallery/index.html',
                               pagination=pagination,
                               albums=pagination.items,
                               header_menu=header_menu,
                               sidebar_menu=sidebar_menu)

    @app.route('/gallery/<slug>')
    def gallery_album(slug):
        """Страница альбома с миниатюрами и каруселью"""
        album = Album.query.filter_by(slug=slug, is_published=True).first_or_404()

        photos = album.photos  # уже отсортированы по order

        header_menu = MenuItem.query.filter_by(position='header', parent_id=None)\
            .order_by(MenuItem.order).all()
        sidebar_menu = MenuItem.query.filter_by(position='sidebar', parent_id=None)\
            .order_by(MenuItem.order).all()

        return render_template('gallery/album.html',
                               album=album,
                               photos=photos,
                               header_menu=header_menu,
                               sidebar_menu=sidebar_menu)

    # --- Управление альбомами ---

    @app.route('/admin/albums/')
    @login_required
    def admin_albums():
        """Список альбомов в админке"""
        page = get_page()
        per_page = app.config.get('ALBUMS_PER_PAGE', 12)

        pagination = (
            Album.query
            .order_by(Album.order.asc(), Album.created_at.desc())
            .paginate(page=page, per_page=per_page, error_out=False)
        )

        return render_template('admin/albums.html',
                               pagination=pagination,
                               albums=pagination.items)

    @app.route('/admin/albums/create', methods=['GET', 'POST'])
    @login_required
    def admin_album_create():
        """Создание альбома"""
        form = AlbumForm()

        if form.validate_on_submit():
            # Проверка уникальности slug
            if Album.query.filter_by(slug=form.slug.data).first():
                flash('Альбом с таким slug уже существует!', 'danger')
                return render_template('admin/album_form.html',
                                       form=form, title='Создание альбома')

            album = Album(
                title=form.title.data,
                slug=form.slug.data,
                description=form.description.data,
                is_published=form.is_published.data,
                order=form.order.data or 0,
            )
            db.session.add(album)
            db.session.commit()

            flash(f'Альбом «{album.title}» создан. Добавьте в него фотографии.', 'success')
            return redirect(url_for('admin_album_edit', id=album.id))

        return render_template('admin/album_form.html',
                               form=form, title='Создание альбома')

    @app.route('/admin/albums/<int:id>/edit', methods=['GET', 'POST'])
    @login_required
    def admin_album_edit(id):
        """Редактирование альбома + управление фотографиями"""
        album = Album.query.get_or_404(id)
        form = AlbumForm(obj=album)
        photos_form = AlbumPhotosForm()

        # Список только изображений из файлового менеджера
        image_files = (
            UploadedFile.query
            .filter_by(file_type='image')
            .order_by(UploadedFile.uploaded_at.desc())
            .all()
        )
        photos_form.file_ids.choices = [(f.id, f.original_name) for f in image_files]

        # === ВЕТКА 1: сохранение свойств альбома ===
        if 'save_album' in request.form:
            if not form.validate_on_submit():
                for errors in form.errors.values():
                    for e in errors:
                        flash(e, 'danger')
                return redirect(url_for('admin_album_edit', id=album.id))

            existing = Album.query.filter(
                Album.slug == form.slug.data, Album.id != album.id
            ).first()
            if existing:
                flash('Альбом с таким slug уже существует!', 'danger')
            else:
                album.title = form.title.data
                album.slug = form.slug.data
                album.description = form.description.data
                album.is_published = form.is_published.data
                album.order = form.order.data or 0
                db.session.commit()
                flash('Альбом обновлён.', 'success')
            return redirect(url_for('admin_album_edit', id=album.id))

        # === ВЕТКА 2: добавление фотографий ===
        if 'add_photos' in request.form:
            # CSRF-проверка через photos_form
            if not photos_form.validate_on_submit():
                for errors in photos_form.errors.values():
                    for e in errors:
                        flash(e, 'danger')
                return redirect(url_for('admin_album_edit', id=album.id))

            selected = photos_form.file_ids.data or []
            if not selected:
                flash('Не выбрано ни одного файла.', 'warning')
                return redirect(url_for('admin_album_edit', id=album.id))

            added = 0
            # Текущий максимальный order
            max_order = (
                db.session.query(db.func.max(Photo.order))
                .filter_by(album_id=album.id)
                .scalar()
            ) or 0

            for fid in selected:
                # Не добавлять повторно тот же файл
                if Photo.query.filter_by(album_id=album.id, file_id=fid).first():
                    continue
                max_order += 1
                db.session.add(Photo(
                    album_id=album.id,
                    file_id=fid,
                    order=max_order
                ))
                added += 1

            db.session.commit()

            if added:
                flash(f'Добавлено фотографий: {added}.', 'success')
            else:
                flash('Все выбранные файлы уже есть в альбоме.', 'info')
            return redirect(url_for('admin_album_edit', id=album.id))

        # === GET-запрос или POST без явных кнопок ===
        return render_template('admin/album_form.html',
                               form=form,
                               photos_form=photos_form,
                               album=album,
                               image_files=image_files,
                               title=f'Редактирование: {album.title}')

    @app.route('/admin/albums/<int:id>/delete', methods=['POST'])
    @login_required
    def admin_album_delete(id):
        """Удаление альбома (сами файлы в uploads/ остаются)"""
        album = Album.query.get_or_404(id)
        title = album.title
        db.session.delete(album)
        db.session.commit()
        flash(f'Альбом «{title}» удалён.', 'info')
        return redirect(url_for('admin_albums'))

    @app.route('/admin/albums/<int:album_id>/photos/<int:photo_id>/delete', methods=['POST'])
    @login_required
    def admin_album_photo_delete(album_id, photo_id):
        """Удаление фото из альбома (файл в uploads/ остаётся)"""
        photo = Photo.query.filter_by(id=photo_id, album_id=album_id).first_or_404()
        db.session.delete(photo)
        db.session.commit()
        flash('Фотография удалена из альбома.', 'info')
        return redirect(url_for('admin_album_edit', id=album_id))

    @app.route('/admin/albums/<int:album_id>/cover/<int:photo_id>', methods=['POST'])
    @login_required
    def admin_album_set_cover(album_id, photo_id):
        """Назначение обложки альбома"""
        album = Album.query.get_or_404(album_id)
        photo = Photo.query.filter_by(id=photo_id, album_id=album_id).first_or_404()
        album.cover_photo_id = photo.id
        db.session.commit()
        flash('Обложка обновлена.', 'success')
        return redirect(url_for('admin_album_edit', id=album_id))

    @app.route('/admin/albums/<int:album_id>/reorder', methods=['POST'])
    @login_required
    def admin_album_reorder(album_id):
        """Сохранение нового порядка фото (перетаскивание, JSON)"""
        data = request.get_json(silent=True) or {}
        order_list = data.get('order', [])
        for idx, photo_id in enumerate(order_list):
            photo = Photo.query.filter_by(id=photo_id, album_id=album_id).first()
            if photo:
                photo.order = idx
        db.session.commit()
        return jsonify({'ok': True})

    # --- API для редактора (TinyMCE) ---

    @app.route('/admin/api/files')
    @login_required
    def admin_api_files():
        """JSON-список файлов для модального окна редактора"""
        type_filter = request.args.get('type', 'all')
        query = UploadedFile.query

        if type_filter != 'all':
            query = query.filter(UploadedFile.file_type == type_filter)

        files = query.order_by(UploadedFile.uploaded_at.desc()).all()

        data = [
            {
                'id': f.id,
                'name': f.original_name,
                'url': url_for('admin_file_download', id=f.id),
                'public_url': url_for('uploaded_file', filename=f.stored_name),
                'type': f.file_type,
                'size': f.size_human(),
                'date': f.uploaded_at.strftime('%d.%m.%Y %H:%M'),
            }
            for f in files
        ]

        return jsonify(data)

    @app.route('/admin/api/upload', methods=['POST'])
    @login_required
    def admin_api_upload():
        """AJAX-загрузка файла из редактора"""
        if 'file' not in request.files:
            return jsonify({'error': 'Файл не передан'}), 400

        file = request.files['file']
        if not file.filename:
            return jsonify({'error': 'Пустое имя файла'}), 400

        original_name = file.filename
        ext = os.path.splitext(original_name)[1].lstrip('.').lower()
        stored_name = make_stored_name(original_name)

        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], stored_name)
        file.save(save_path)
        size = os.path.getsize(save_path)

        record = UploadedFile(
            original_name=original_name,
            stored_name=stored_name,
            mime_type=guess_mime(original_name),
            file_type=get_file_type(ext),
            size=size,
            extension=ext,
            uploaded_by_id=current_user.id,
        )
        db.session.add(record)
        db.session.commit()

        return jsonify({
            'id': record.id,
            'name': record.original_name,
            'url': url_for('admin_file_download', id=record.id),
            'public_url': url_for('uploaded_file', filename=record.stored_name),
            'type': record.file_type,
            'size': record.size_human(),
        })

    return app


# === ЗАПУСК ПРИЛОЖЕНИЯ ===

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()

        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        os.makedirs(app.config['ARCHIVE_FOLDER'], exist_ok=True)

        if User.query.count() == 0:
            admin = User(
                username='admin',
                email='admin@example.com',
                is_admin=True
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print('Создан администратор: admin / admin123')

    app.run(debug=True, host='0.0.0.0', port=5000)