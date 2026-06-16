import json
import os
from pathlib import Path
from utils import get_app_dir, resource_path

class SettingsManager:
    """Менеджер для хранения настроек по умолчанию для текста"""
    
    def __init__(self):
        # Определяем путь к файлу настроек в папке с программой
        self.app_dir = get_app_dir()
        self.settings_file = os.path.join(self.app_dir, "settings.json")


        # Ключи настроек (только умолчания)
        self.KEY_DEFAULT_FONT_SIZE = "default_font_size"
        self.KEY_DEFAULT_FONT_FAMILY = "default_font_family"
        self.KEY_DEFAULT_FONT_PATH = "default_font_path"
        self.KEY_DEFAULT_VERTICAL = "default_vertical"
        
        # Значения по умолчанию
        self.defaults = {
            self.KEY_DEFAULT_FONT_SIZE: 12,
            self.KEY_DEFAULT_FONT_FAMILY: "Arial",
            self.KEY_DEFAULT_FONT_PATH: "",
            self.KEY_DEFAULT_VERTICAL: False
        }
        
        # Загружаем настройки
        self.settings = {}
        self.load_settings()
    
    def load_settings(self):
        """Загружает настройки из JSON файла"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    self.settings = json.load(f)
                print(f"Настройки загружены из: {self.settings_file}")
            else:
                # Файла нет - создаем с настройками по умолчанию
                print(f"Файл настроек не найден, создаем с значениями по умолчанию: {self.settings_file}")
                self.settings = self.defaults.copy()
                self.save_settings()
        except Exception as e:
            print(f"Ошибка загрузки настроек: {e}")
            self.settings = self.defaults.copy()
    
    def save_settings(self):
        """Сохраняет настройки в JSON файл"""
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)
            print(f"Настройки сохранены в: {self.settings_file}")
        except Exception as e:
            print(f"Ошибка сохранения настроек: {e}")
    def get_default_font_size(self):
        return self.settings.get(self.KEY_DEFAULT_FONT_SIZE, 12)
    
    def set_default_font_size(self, size):
        self.settings[self.KEY_DEFAULT_FONT_SIZE] = size
        self.save_settings()
    
    def get_default_font_family(self):
        return self.settings.get(self.KEY_DEFAULT_FONT_FAMILY, "Arial")
    
    def set_default_font_family(self, family, font_path=""):
        self.settings[self.KEY_DEFAULT_FONT_FAMILY] = family
        if font_path:
            self.set_default_font_path(font_path)
        self.save_settings()
    
    def get_default_font_path(self):
        return self.settings.get(self.KEY_DEFAULT_FONT_PATH, "")
    
    def set_default_font_path(self, path):
        self.settings[self.KEY_DEFAULT_FONT_PATH] = path
        self.save_settings()
    
    def get_default_vertical(self):
        return self.settings.get(self.KEY_DEFAULT_VERTICAL, False)
    
    def set_default_vertical(self, vertical):
        self.settings[self.KEY_DEFAULT_VERTICAL] = vertical
        self.save_settings()
    
    def get_default_text_data(self):
        return {
            'font_size': self.get_default_font_size(),
            'font_family': self.get_default_font_family(),
            'font_path': self.get_default_font_path(),
            'vertical': self.get_default_vertical()
        }
    
    def save_defaults(self, font_size, font_family, font_path, vertical):
        """Сохраняет настройки по умолчанию"""
        self.set_default_font_size(font_size)
        self.set_default_font_family(font_family, font_path)
        self.set_default_vertical(vertical)
    
    def reset_to_defaults(self):
        """Сбрасывает настройки к стандартным"""
        self.settings = self.defaults.copy()
        self.save_settings()
    
    def get_settings_file_path(self):
        return str(self.settings_file)