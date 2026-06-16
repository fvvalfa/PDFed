from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPainter, QPixmap, QFontDatabase
from PySide6.QtWidgets import QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel, QLineEdit, QSpinBox, QVBoxLayout
import os


class TextInputDialog(QDialog):
    """Диалог для ввода текста с настройками направления, размера и шрифта"""
    def __init__(self, parent=None, initial_text="", initial_font_size=12, initial_vertical=False, 
                 initial_font_family=None, available_fonts=None, settings_manager=None):
        super().__init__(parent)
        self.setWindowTitle("Ввод текста")
        self.setModal(True)
        self.setMinimumWidth(400)
        
        self.available_fonts = available_fonts or []
        self.initial_font_family = initial_font_family
        self.settings_manager = settings_manager

        layout = QVBoxLayout(self)

        # Форма для параметров
        form_layout = QFormLayout()

        # Поле для ввода текста
        self.text_edit = QLineEdit(initial_text)
        self.text_edit.setPlaceholderText("Введите текст...")
        form_layout.addRow("Текст:", self.text_edit)

        # Выбор шрифта
        self.font_combo = QComboBox()
        for font_path, font_name in self.available_fonts:
            self.font_combo.addItem(font_name, font_path)
        
        # Выбираем текущий шрифт
        if initial_font_family:
            index = self.font_combo.findText(initial_font_family)
            if index >= 0:
                self.font_combo.setCurrentIndex(index)
        
        form_layout.addRow("Шрифт:", self.font_combo)

        # Размер шрифта
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setMinimum(6)
        self.font_size_spin.setMaximum(72)
        self.font_size_spin.setValue(initial_font_size)
        form_layout.addRow("Размер шрифта:", self.font_size_spin)

        # Направление текста
        self.vertical_checkbox = QCheckBox("Вертикальный текст")
        self.vertical_checkbox.setChecked(initial_vertical)
        form_layout.addRow("Направление:", self.vertical_checkbox)

        layout.addLayout(form_layout)

        # Предпросмотр
        self.preview_label = QLabel()
        self.preview_label.setStyleSheet("border: 1px solid gray; padding: 10px; min-height: 50px;")
        self.preview_label.setMinimumHeight(100)
        layout.addWidget(QLabel("Предпросмотр:"))
        layout.addWidget(self.preview_label)

        # Кнопки OK/Cancel
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        # Обновляем предпросмотр при изменении параметров
        self.text_edit.textChanged.connect(self.update_preview)
        self.font_size_spin.valueChanged.connect(self.update_preview)
        self.vertical_checkbox.stateChanged.connect(self.update_preview)
        self.font_combo.currentIndexChanged.connect(self.update_preview)

        self.update_preview()

    def update_preview(self):
        """Обновляет предпросмотр текста"""
        text = self.text_edit.text()
        font_size = self.font_size_spin.value()
        is_vertical = self.vertical_checkbox.isChecked()
        font_name = self.font_combo.currentText()

        if not text:
            self.preview_label.setText("(текст не введен)")
            return

        # Создаем QPixmap для предпросмотра
        preview_pixmap = QPixmap(350, 120)
        preview_pixmap.fill(Qt.GlobalColor.white)

        painter = QPainter(preview_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        font = QFont(font_name, font_size)
        painter.setFont(font)

        if is_vertical:
            # Для вертикального текста: поворачиваем и рисуем
            painter.translate(175, 60)  # Центр области
            painter.rotate(-90)
            painter.drawText(0, 0, text)
        else:
            # Горизонтальный текст
            painter.drawText(10, 60, text)

        painter.end()

        self.preview_label.setPixmap(preview_pixmap.scaled(350, 120, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def get_text_data(self):
        """Возвращает данные текста"""
        # Обновляем последние использованные настройки
        if self.settings_manager:
            self.settings_manager.update_last_used(
                self.font_size_spin.value(),
                self.font_combo.currentText(),
                self.font_combo.currentData(),
                self.vertical_checkbox.isChecked()
            )
        
        return {
            'text': self.text_edit.text(),
            'font_size': self.font_size_spin.value(),
            'vertical': self.vertical_checkbox.isChecked(),
            'font_family': self.font_combo.currentText(),
            'font_path': self.font_combo.currentData()
        }