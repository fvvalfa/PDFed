from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPainter, QPixmap
from PySide6.QtWidgets import QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel, QLineEdit, QSpinBox, QVBoxLayout, QHBoxLayout, QPushButton


class SettingsDialog(QDialog):
    """Диалог для настройки параметров текста по умолчанию"""
    def __init__(self, parent=None, current_settings=None, available_fonts=None):
        super().__init__(parent)
        self.setWindowTitle("Настройки текста по умолчанию")
        self.setModal(True)
        self.setMinimumWidth(450)
        
        self.available_fonts = available_fonts or []
        self.current_settings = current_settings or {}
        
        self.setup_ui()
        self.load_settings()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Основная форма
        form_layout = QFormLayout()
        
        # Выбор шрифта
        self.font_combo = QComboBox()
        for font_path, font_name in self.available_fonts:
            self.font_combo.addItem(font_name, font_path)
        form_layout.addRow("Шрифт по умолчанию:", self.font_combo)
        
        # Размер шрифта
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setMinimum(6)
        self.font_size_spin.setMaximum(72)
        form_layout.addRow("Размер шрифта по умолчанию:", self.font_size_spin)
        
        # Направление текста
        self.vertical_checkbox = QCheckBox("Вертикальный текст")
        form_layout.addRow("Направление по умолчанию:", self.vertical_checkbox)
        
        layout.addLayout(form_layout)
        
        # Предпросмотр
        self.preview_label = QLabel()
        self.preview_label.setStyleSheet("border: 1px solid gray; padding: 10px; min-height: 50px;")
        self.preview_label.setMinimumHeight(100)
        layout.addWidget(QLabel("Предпросмотр:"))
        layout.addWidget(self.preview_label)
        
        # Информационная строка
        info_label = QLabel("Эти настройки будут использоваться при добавлении нового текста")
        info_label.setStyleSheet("color: gray; font-size: 10pt;")
        layout.addWidget(info_label)
        
        # Кнопки
        button_layout = QHBoxLayout()
        
        self.reset_btn = QPushButton("↺ Сбросить к стандартным")
        self.reset_btn.clicked.connect(self.reset_to_standard)
        button_layout.addWidget(self.reset_btn)
        
        button_layout.addStretch()
        
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        button_layout.addWidget(button_box)
        
        layout.addLayout(button_layout)
        
        # Обновление предпросмотра
        self.font_combo.currentIndexChanged.connect(self.update_preview)
        self.font_size_spin.valueChanged.connect(self.update_preview)
        self.vertical_checkbox.stateChanged.connect(self.update_preview)
    
    def load_settings(self):
        """Загружает текущие настройки"""
        font_size = self.current_settings.get('font_size', 12)
        font_family = self.current_settings.get('font_family', 'Arial')
        vertical = self.current_settings.get('vertical', False)
        
        self.font_size_spin.setValue(font_size)
        self.vertical_checkbox.setChecked(vertical)
        
        # Выбираем шрифт в комбобоксе
        index = self.font_combo.findText(font_family)
        if index >= 0:
            self.font_combo.setCurrentIndex(index)
        
        self.update_preview()
    
    def reset_to_standard(self):
        """Сбрасывает к стандартным значениям"""
        self.font_size_spin.setValue(12)
        self.vertical_checkbox.setChecked(False)
        
        index = self.font_combo.findText("Arial")
        if index >= 0:
            self.font_combo.setCurrentIndex(index)
        
        self.update_preview()
    
    def update_preview(self):
        """Обновляет предпросмотр"""
        font_size = self.font_size_spin.value()
        is_vertical = self.vertical_checkbox.isChecked()
        font_name = self.font_combo.currentText()
        
        preview_pixmap = QPixmap(350, 100)
        preview_pixmap.fill(Qt.GlobalColor.white)
        
        painter = QPainter(preview_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        font = QFont(font_name, font_size)
        painter.setFont(font)
        
        sample_text = "Пример текста AaBbYy"
        
        if is_vertical:
            painter.translate(175, 50)
            painter.rotate(-90)
            painter.drawText(0, 0, sample_text)
        else:
            painter.drawText(10, 50, sample_text)
        
        painter.end()
        
        self.preview_label.setPixmap(preview_pixmap.scaled(350, 100, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
    
    def get_settings(self):
        """Возвращает настройки из диалога"""
        return {
            'font_size': self.font_size_spin.value(),
            'font_family': self.font_combo.currentText(),
            'font_path': self.font_combo.currentData(),
            'vertical': self.vertical_checkbox.isChecked()
        }