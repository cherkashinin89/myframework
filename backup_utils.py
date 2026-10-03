# backup_utils.py - утилиты резервного копирования
import os
import subprocess
import tarfile
import sqlite3
from datetime import datetime


def is_mounted(path):
    """
    Проверяет, является ли путь точкой монтирования.
    Возвращает True, если диск смонтирован и доступен для чтения.
    """
    if not path or not os.path.exists(path):
        return False
    try:
        result = subprocess.run(
            ['mountpoint', '-q', path],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        # mountpoint не установлен — используем os.path.ismount
        return os.path.ismount(path)


def get_disk_info(path):
    """
    Возвращает информацию о диске: всего, занято, свободно (в ГБ).
    Если путь не существует — возвращает None.
    """
    if not path or not os.path.exists(path):
        return None
    try:
        stat = os.statvfs(path)
        total = stat.f_blocks * stat.f_frsize
        free = stat.f_bavail * stat.f_frsize
        used = total - free
        return {
            'path': path,
            'total_gb': round(total / (1024 ** 3), 1),
            'used_gb': round(used / (1024 ** 3), 1),
            'free_gb': round(free / (1024 ** 3), 1),
            'percent': round(used / total * 100, 1) if total else 0,
        }
    except (OSError, ZeroDivisionError):
        return None


def backup_sqlite_consistent(db_path, dest_path):
    """
    Безопасное копирование SQLite через механизм .backup.
    Работает даже при активных записях в базу.
    """
    src = sqlite3.connect(db_path)
    dst = sqlite3.connect(dest_path)
    with dst:
        src.backup(dst)
    dst.close()
    src.close()


def create_full_backup(project_dir, dest_root, subdir='myframework',
                       keep_count=10, progress_callback=None):
    """
    Создаёт полный бэкап проекта во внешний диск.
    
    :param project_dir: путь к проекту (например, /home/admin/apps/myframework)
    :param dest_root: точка монтирования внешнего диска (например, /mnt/backup)
    :param subdir: подпапка на диске (например, myframework)
    :param keep_count: сколько последних архивов хранить
    :param progress_callback: функция для передачи статуса (опционально)
    :return: словарь {'ok': bool, 'archive': str, 'size_mb': float, 'error': str}
    """
    if progress_callback:
        progress_callback('Проверка внешнего диска…')

    if not is_mounted(dest_root):
        return {
            'ok': False,
            'error': f'Внешний диск не смонтирован: {dest_root}',
        }

    # Готовим папку на внешнем диске
    backup_dir = os.path.join(dest_root, subdir)
    os.makedirs(backup_dir, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    archive_name = f'myframework_full_{timestamp}.tar.gz'
    archive_path = os.path.join(backup_dir, archive_name)

    if progress_callback:
        progress_callback('Копирование базы данных…')

    # Создаём консистентную копию SQLite во временном файле
    temp_db = os.path.join(backup_dir, f'.tmp_site_{timestamp}.db')
    db_path = os.path.join(project_dir, 'site.db')
    try:
        if os.path.exists(db_path):
            backup_sqlite_consistent(db_path, temp_db)
    except Exception as e:
        return {'ok': False, 'error': f'Ошибка копирования БД: {e}'}

    if progress_callback:
        progress_callback('Упаковка проекта в архив…')

    # Список того, что НЕ попадает в бэкап
    exclude_names = {
        'venv', '__pycache__', '.git', '.vscode',
        'node_modules', '.pytest_cache',
    }

    def filter_func(tarinfo):
        """Исключает ненужные папки из архива."""
        name = os.path.basename(tarinfo.name)
        if name in exclude_names:
            return None
        # Исключаем сам архив, если он вдруг попал
        if tarinfo.name.endswith('.tar.gz'):
            return None
        return tarinfo

    try:
        with tarfile.open(archive_path, 'w:gz') as tar:
            # 1. База данных (берём консистентную копию)
            if os.path.exists(temp_db):
                tar.add(temp_db, arcname='site.db')

            # 2. Весь остальной проект
            for item in os.listdir(project_dir):
                if item in exclude_names or item == 'site.db':
                    continue
                full_path = os.path.join(project_dir, item)
                tar.add(full_path, arcname=item, filter=filter_func)
    except Exception as e:
        # Удаляем неполный архив
        if os.path.exists(archive_path):
            os.remove(archive_path)
        return {'ok': False, 'error': f'Ошибка упаковки: {e}'}
    finally:
        # Удаляем временную БД
        if os.path.exists(temp_db):
            os.remove(temp_db)

    # === ПРОВЕРКА: файл реально записан и не пустой ===
    if not os.path.exists(archive_path):
        return {'ok': False, 'error': 'Архив не создан'}

    size_bytes = os.path.getsize(archive_path)
    if size_bytes < 1024:
        os.remove(archive_path)
        return {
            'ok': False,
            'error': f'Архив пустой или повреждён ({size_bytes} байт). '
                     f'Проверьте, что диск смонтирован и доступен для записи.'
        }

    # Принудительная синхронизация буферов на диск
    try:
        import subprocess as _sp
        _sp.run(['sync'], timeout=10)
    except Exception:
        pass

    size_mb = round(size_bytes / (1024 ** 2), 1)

    # Считаем размер
    size_mb = round(os.path.getsize(archive_path) / (1024 ** 2), 1)

    if progress_callback:
        progress_callback('Удаление старых бэкапов…')

    # Чистим старые архивы
    try:
        existing = sorted(
            [f for f in os.listdir(backup_dir)
             if f.startswith('myframework_full_') and f.endswith('.tar.gz')],
            reverse=True
        )
        for old in existing[keep_count:]:
            os.remove(os.path.join(backup_dir, old))
    except OSError:
        pass  # ошибка очистки не критична

    return {
        'ok': True,
        'archive': archive_path,
        'archive_name': archive_name,
        'size_mb': size_mb,
    }


def list_backups(dest_root, subdir='myframework'):
    """Возвращает список бэкапов на внешнем диске с размерами и датами."""
    backup_dir = os.path.join(dest_root, subdir)
    if not os.path.isdir(backup_dir):
        return []

    files = []
    for name in os.listdir(backup_dir):
        if not name.endswith('.tar.gz'):
            continue
        full = os.path.join(backup_dir, name)
        try:
            st = os.stat(full)
            files.append({
                'name': name,
                'size_mb': round(st.st_size / (1024 ** 2), 1),
                'mtime': datetime.fromtimestamp(st.st_mtime),
            })
        except OSError:
            continue

    files.sort(key=lambda x: x['mtime'], reverse=True)
    return files

def sync_buffers():
    """
    Принудительно сбрасывает буферы файловой системы на диск.
    Использует /usr/bin/sudo -n sync (по правилам в /etc/usr/bin/sudoers.d/myframework-mount).
    """
    try:
        result = subprocess.run(
            ['/usr/bin/sudo', '-n', 'sync'],
            capture_output=True,
            timeout=15
        )
        return result.returncode == 0
    except Exception:
        return False


def mount_disk(mount_point, device=None):
    """
    Монтирует внешний диск.
    Использует 'mount -a' — монтирование по /etc/fstab.
    Опция device игнорируется (оставлена для совместимости).
    
    :return: {'ok': bool, 'error': str или None}
    """
    if is_mounted(mount_point):
        return {'ok': True, 'error': None, 'message': 'Диск уже смонтирован'}

    if not os.path.exists(mount_point):
        return {'ok': False, 'error': f'Точка монтирования не существует: {mount_point}'}

    try:
        # mount -a монтирует всё по fstab, включая /mnt/backup
        result = subprocess.run(
            ['/usr/bin/sudo', '-n', 'mount', '-a'],
            capture_output=True,
            timeout=30,
            text=True
        )

        if result.returncode != 0:
            error = result.stderr.strip() or 'Неизвестная ошибка mount'
            return {'ok': False, 'error': error}

        # Проверяем, что диск действительно смонтировался
        if not is_mounted(mount_point):
            return {
                'ok': False,
                'error': f'Диск не смонтирован после mount -a. '
                         f'Проверьте /etc/fstab и наличие устройства.'
            }

        return {'ok': True, 'error': None, 'message': 'Диск смонтирован'}
    except subprocess.TimeoutExpired:
        return {'ok': False, 'error': 'Превышено время ожидания mount'}
    except Exception as e:
        return {'ok': False, 'error': f'Неожиданная ошибка mount: {e}'}

    #размонтирование
def unmount_disk(mount_point):
    """
    Безопасно отмонтирует внешний диск:
    1. sync — сбрасывает буферы на диск
    2. umount — отмонтирует
    
    :return: {'ok': bool, 'error': str или None}
    """
    if not is_mounted(mount_point):
        return {'ok': True, 'error': None, 'message': 'Диск уже отмонтирован'}

    # 1. Синхронизация буферов (не критично, если упадёт)
    sync_buffers()

    # 2. Отмонтирование
    try:
        result = subprocess.run(
            ['/usr/bin/sudo', '-n', 'umount', mount_point],
            capture_output=True,
            timeout=30,
            text=True
        )

        if result.returncode != 0:
            error = result.stderr.strip() or 'Неизвестная ошибка umount'
            return {'ok': False, 'error': error}

        return {'ok': True, 'error': None, 'message': 'Диск отмонтирован. Можно безопасно извлечь.'}
    except subprocess.TimeoutExpired:
        return {'ok': False, 'error': 'Превышено время ожидания umount'}
    except Exception as e:
        return {'ok': False, 'error': f'Неожиданная ошибка umount: {e}'}