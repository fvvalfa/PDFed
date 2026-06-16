import sys
import os

def resource_path(relative_path):
    """Получить абсолютный путь к файлу. Работает и для .py, и для .exe."""
    try:
        # PyInstaller создает временную папку и хранит ее путь в sys._MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # Если мы не в .exe, то используем путь к текущему файлу скрипта
        base_path = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(base_path, relative_path)

def get_app_dir():
    """Возвращает директорию приложения (где находится exe или py файл)"""
    if getattr(sys, 'frozen', False):
        # Запущено как exe
        return os.path.dirname(sys.executable)
    else:
        # Запущено как скрипт
        return os.path.dirname(os.path.abspath(__file__))