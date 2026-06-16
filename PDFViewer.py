from MovableTextItem import MovableTextItem
from PDFGraphicsView import PDFGraphicsView
from TextInputDialog import TextInputDialog
from SettingsManager import SettingsManager
from SettingsDialog import SettingsDialog
from utils import resource_path, get_app_dir

import fitz
import win32print
from PySide6.QtCore import QPointF, QRectF, QTimer, Qt
from PySide6.QtGui import QFontDatabase, QImage, QPageLayout, QPainter, QPixmap, QAction
from PySide6.QtPrintSupport import QPrintPreviewDialog, QPrinter
from PySide6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QGraphicsScene, QGraphicsView, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton, QSlider, QSpinBox, QVBoxLayout, QWidget, QMenu


import os
import tempfile


class PDFViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_document = None
        self.current_page = 0
        self.total_pages = 0
        self.zoom_factor = 1.0
        self.font_cache = {}
        self.text_items = []  # Список текстовых элементов на текущей странице
        self.text_data = {}   # Словарь: page_num -> список текстовых данных
        self.current_file_path = None
        self._font_family_default = 'Arial'
        
        self.print_worker = None

        # Инициализация менеджера настроек
        self.settings_manager = SettingsManager()

        self.init_ui()
        self.create_menu()
    
    def create_menu(self):
        """Создает главное меню приложения"""
        menubar = self.menuBar()
        
        # Меню "Настройки"
        settings_menu = menubar.addMenu("⚙ Настройки")
        
        # Пункт: Настройки текста по умолчанию
        self.defaults_action = QAction("✏ Настройки текста по умолчанию", self)
        self.defaults_action.triggered.connect(self.open_settings_dialog)
        settings_menu.addAction(self.defaults_action)
        
        settings_menu.addSeparator()
        
        # Пункт: Сбросить умолчания
        self.reset_defaults_action = QAction("↺ Сбросить умолчания к стандартным", self)
        self.reset_defaults_action.triggered.connect(self.reset_defaults)
        settings_menu.addAction(self.reset_defaults_action)
        
        # Пункт: Показать текущие умолчания
        self.show_defaults_action = QAction("ℹ Показать текущие умолчания", self)
        self.show_defaults_action.triggered.connect(self.show_current_defaults)
        settings_menu.addAction(self.show_defaults_action)
        
        settings_menu.addSeparator()
        
        # Пункт: Открыть папку с настройками
        self.show_settings_path_action = QAction("📂 Открыть папку с настройками", self)
        self.show_settings_path_action.triggered.connect(self.show_settings_path)
        settings_menu.addAction(self.show_settings_path_action)
        
        # Меню "Справка"
        help_menu = menubar.addMenu("❓ Справка")
        self.about_action = QAction("ℹ О программе", self)
        self.about_action.triggered.connect(self.show_about)
        help_menu.addAction(self.about_action)
    
    def open_settings_dialog(self):
        """Открывает диалог настроек текста по умолчанию"""
        # Получаем текущие настройки умолчаний
        defaults = self.settings_manager.get_default_text_data()
        available_fonts = self.get_available_fonts()
        
        dialog = SettingsDialog(self, defaults, available_fonts)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_settings = dialog.get_settings()
            # Сохраняем новые настройки умолчаний
            self.settings_manager.save_defaults(
                new_settings['font_size'],
                new_settings['font_family'],
                new_settings['font_path'],
                new_settings['vertical']
            )
            self.status_label.setText("Настройки по умолчанию сохранены")
    
    def show_settings_path(self):
        """Открывает папку с файлом настроек"""
        settings_path = self.settings_manager.get_settings_file_path()
        settings_dir = os.path.dirname(settings_path)
        
        msg = QMessageBox(self)
        msg.setWindowTitle("Файл настроек")
        msg.setText(f"Настройки сохраняются в файл:\n\n{settings_path}\n\n"
                    f"Вы можете скопировать этот файл для переноса настроек на другой компьютер.\n"
                    f"Также вы можете открыть его в блокноте для просмотра или ручного редактирования.")
        msg.setIcon(QMessageBox.Icon.Information)
        
        # Добавляем кнопку для открытия папки
        open_folder_btn = msg.addButton("📂 Открыть папку", QMessageBox.ButtonRole.ActionRole)
        ok_btn = msg.addButton("OK", QMessageBox.ButtonRole.AcceptRole)
        
        msg.exec()
        
        if msg.clickedButton() == open_folder_btn:
            # Открываем папку с файлом настроек
            import subprocess
            import platform
            
            if platform.system() == "Windows":
                os.startfile(settings_dir)
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", settings_dir])
            else:  # Linux
                subprocess.run(["xdg-open", settings_dir])
    
    def reset_defaults(self):
        """Сбрасывает настройки умолчаний к стандартным"""
        reply = QMessageBox.question(self, "Сброс умолчаний", 
            "Сбросить все настройки умолчаний к стандартным значениям?\n\n"
            "Стандартные значения:\n"
            "• Шрифт: Arial\n"
            "• Размер: 12\n"
            "• Направление: Горизонтальное",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            self.settings_manager.reset_to_defaults()
            QMessageBox.information(self, "Умолчания сброшены", 
                "Настройки умолчаний сброшены к стандартным значениям.")
    
    def show_current_defaults(self):
        """Показывает текущие настройки умолчаний"""
        defaults = self.settings_manager.get_default_text_data()
        
        info_text = f"""
        <b>Текущие параметры текста по умолчанию:</b>
        
        <table border="0" cellpadding="5">
        <tr><td><b>Шрифт:</b></td><td>{defaults['font_family']}</td></tr>
        <tr><td><b>Размер:</b></td><td>{defaults['font_size']} pt</td></tr>
        <tr><td><b>Направление:</b></td><td>{'Вертикальный' if defaults['vertical'] else 'Горизонтальный'}</td></tr>
        </table>
        
        <i>Эти параметры будут использоваться при добавлении нового текста.</i>
        """
        
        QMessageBox.information(self, "Параметры по умолчанию", info_text)
    
    def show_about(self):
        """Показывает информацию о программе"""
        about_text = f"""
        <b>PDF Просмотрщик с редактированием</b><br>
        <br>
        <b>Версия:</b> 1.0<br>
        <b>Автор:</b> PDF Editor Team<br>
        <br>
        <b>Возможности:</b><br>
        • Просмотр PDF документов<br>
        • Добавление текста на страницы<br>
        • Поддержка вертикального и горизонтального текста<br>
        • Поддержка пользовательских шрифтов<br>
        • Сохранение настроек текста по умолчанию<br>
        • Печать с предпросмотром<br>
        <br>
        <b>Горячие клавиши:</b><br>
        • Ctrl+T - режим добавления текста<br>
        • Delete - удалить выделенный текст<br>
        • Ctrl+колесо мыши - масштабирование<br>
        • Колесо мыши - перелистывание страниц<br>
        """
        
        QMessageBox.about(self, "О программе", about_text)
    
    def get_available_fonts(self):
        """Получает список доступных шрифтов с кэшированием"""
        if hasattr(self, '_cached_fonts') and self._cached_fonts:
            return self._cached_fonts

        available_fonts = []
        font_extensions = ('.ttf', '.otf', '.ttc')
        program_dir = get_app_dir()

        for file in os.listdir(program_dir):
            if file.lower().endswith(font_extensions):
                font_path = os.path.join(program_dir, file)
                if font_path in self.font_cache:
                    font_id, font_name = self.font_cache[font_path]
                else:
                    font_id = QFontDatabase.addApplicationFont(font_path)
                    if font_id != -1:
                        families = QFontDatabase.applicationFontFamilies(font_id)
                        font_name = families[0] if families else os.path.splitext(file)[0]
                        self.font_cache[font_path] = (font_id, font_name)
                    else:
                        continue

                available_fonts.append((font_path, font_name))
                print(f"Шрифт: {font_name} из {file}")

        if not available_fonts:
            available_fonts.append(("", "Arial"))

        self._cached_fonts = available_fonts
        return available_fonts
            
    def init_ui(self):
        self.setWindowTitle("PDF Просмотрщик с редактированием")
        self.setGeometry(100, 100, 1200, 800)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        # Панель инструментов
        toolbar = QHBoxLayout()

        self.open_btn = QPushButton("Открыть PDF")
        self.open_btn.clicked.connect(self.open_pdf)
        toolbar.addWidget(self.open_btn)

        self.prev_btn = QPushButton("◀ Предыдущая")
        self.prev_btn.clicked.connect(self.prev_page)
        self.prev_btn.setEnabled(False)
        toolbar.addWidget(self.prev_btn)

        self.next_btn = QPushButton("Следующая ▶")
        self.next_btn.clicked.connect(self.next_page)
        self.next_btn.setEnabled(False)
        toolbar.addWidget(self.next_btn)

        self.page_label = QLabel("Страница: 0/0")
        toolbar.addWidget(self.page_label)

        self.page_spin = QSpinBox()
        self.page_spin.setMinimum(1)
        self.page_spin.valueChanged.connect(self.go_to_page)
        toolbar.addWidget(QLabel("Перейти к странице:"))
        toolbar.addWidget(self.page_spin)

        toolbar.addWidget(QLabel("Масштаб:"))
        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setMinimum(10)
        self.zoom_slider.setMaximum(300)
        self.zoom_slider.setValue(100)
        self.zoom_slider.valueChanged.connect(self.zoom_changed)
        toolbar.addWidget(self.zoom_slider)

        self.zoom_label = QLabel("100%")
        toolbar.addWidget(self.zoom_label)

        self.print_btn = QPushButton("🖨 Печать")
        self.print_btn.clicked.connect(self.print_dialog)
        self.print_btn.setEnabled(False)
        toolbar.addWidget(self.print_btn)

        self.add_text_btn = QPushButton("✏ Добавить текст (Ctrl+T)")
        self.add_text_btn.clicked.connect(self.enable_text_mode)
        self.add_text_btn.setEnabled(False)
        toolbar.addWidget(self.add_text_btn)

        self.clear_text_btn = QPushButton("🗑 Очистить текст")
        self.clear_text_btn.clicked.connect(self.clear_current_page_text)
        self.clear_text_btn.setEnabled(False)
        toolbar.addWidget(self.clear_text_btn)

        self.info_btn = QPushButton("ℹ Инфо о странице")
        self.info_btn.clicked.connect(self.show_page_info)
        self.info_btn.setEnabled(False)
        toolbar.addWidget(self.info_btn)

        main_layout.addLayout(toolbar)

        self.graphics_view = PDFGraphicsView(self)
        self.graphics_view.setRenderHint(QPainter.Antialiasing)
        self.graphics_view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.graphics_view.setStyleSheet("background-color: #808080;")  # Серый цвет
        main_layout.addWidget(self.graphics_view)

        self.status_label = QLabel("Готов к работе")
        self.status_label.setStyleSheet("background-color: #f0f0f0; padding: 5px;")
        main_layout.addWidget(self.status_label)

        self.scene = QGraphicsScene()
        self.graphics_view.setScene(self.scene)

        self.text_mode = False
        self.setFocusPolicy(Qt.StrongFocus)

    def clear_all_data(self):
        """Очищает все данные о текущем PDF"""
        if self.current_document:
            self.current_document.close()
        self.current_document = None
        self.current_page = 0
        self.total_pages = 0
        self.text_data.clear()
        self.current_file_path = None
        self.text_items.clear()
        self.scene.clear()

    def open_pdf(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Выберите PDF файл", "", "PDF Files (*.pdf)")
        if file_path:
            self.open_pdf_file(file_path)
    
    def open_pdf_file(self, file_path):
        """Открывает PDF файл по указанному пути"""
        try:
            self.clear_all_data()

            self.current_document = fitz.open(file_path)
            self.current_file_path = file_path
            self.total_pages = len(self.current_document)
            self.current_page = 0

            self.load_page()

            self.prev_btn.setEnabled(True)
            self.next_btn.setEnabled(True)
            self.print_btn.setEnabled(True)
            self.add_text_btn.setEnabled(True)
            self.clear_text_btn.setEnabled(True)
            self.info_btn.setEnabled(True)
            self.page_spin.setMaximum(self.total_pages)

            self.status_label.setText(f"Файл загружен: {os.path.basename(file_path)}. Страниц: {self.total_pages}")
            return True
        except Exception as e:
            self.clear_all_data()
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть PDF:\n{str(e)}")
            return False

    def get_page_content_info(self, page):
        """Получает информацию о содержимом страницы"""
        info = {
            'has_images': False,
            'has_vector': False,
            'has_text': False,
            'max_image_dpi': 0,
            'image_count': 0,
            'text_size': 0
        }

        try:
            images = page.get_images(full=True)
            info['image_count'] = len(images)
            info['has_images'] = len(images) > 0

            for img in images:
                try:
                    xref = img[0]
                    base_image = self.current_document.extract_image(xref)
                    if base_image:
                        img_dpi_x = base_image.get('xres', 0)
                        img_dpi_y = base_image.get('yres', 0)
                        if img_dpi_x > 0:
                            info['max_image_dpi'] = max(info['max_image_dpi'], img_dpi_x, img_dpi_y)
                except:
                    pass

            drawings = page.get_drawings()
            info['has_vector'] = len(drawings) > 0

            text = page.get_text()
            info['has_text'] = len(text.strip()) > 0
            info['text_size'] = len(text)

        except Exception as e:
            print(f"Ошибка анализа страницы: {e}")

        return info

    def show_page_info(self):
        if not self.current_document:
            return

        page = self.current_document[self.current_page]
        info = self.get_page_content_info(page)

        text_count = len(self.text_data.get(self.current_page, []))

        info_text = f"""
        <b>Страница {self.current_page + 1} из {self.total_pages}</b>
        
        <b>Содержимое:</b>
        • Текст в PDF: {"Да" if info['has_text'] else "Нет"} ({info['text_size']} символов)
        • Добавлено текстов: {text_count}
        • Изображения: {"Да" if info['has_images'] else "Нет"} ({info['image_count']} шт.)
        • Векторная графика: {"Да" if info['has_vector'] else "Нет"}
        
        <b>Качество изображений:</b>
        • Максимальное DPI: {info['max_image_dpi'] if info['max_image_dpi'] > 0 else "не определено"}
        
        <b>Размер страницы:</b>
        • Ширина: {page.rect.width:.1f} pts ({page.rect.width/72:.2f} дюймов)
        • Высота: {page.rect.height:.1f} pts ({page.rect.height/72:.2f} дюймов)
        """

        QMessageBox.information(self, "Информация о странице", info_text)

    def get_zoom_factor(self):
        """Возвращает текущий коэффициент масштабирования"""
        return self.zoom_factor

    def on_text_moved(self, page_num, text_data):
        """Callback при перемещении текста"""
        self.status_label.setText(f"Текст перемещен на странице {page_num + 1}")

    def on_text_edited(self, page_num, text_data):
        """Callback при редактировании текста"""
        self.status_label.setText(f"Текст изменен на странице {page_num + 1}")

    def load_page(self):
        if not self.current_document:
            return

        self.scene.clear()
        self.text_items.clear()

        page = self.current_document[self.current_page]

        zoom = self.zoom_factor
        matrix = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=matrix)

        img_data = pix.tobytes("ppm")
        qimage = QImage.fromData(img_data)
        pixmap = QPixmap.fromImage(qimage)

        self.scene.addPixmap(pixmap)
        self.scene.setSceneRect(0, 0, pixmap.width(), pixmap.height())

        # Восстанавливаем сохраненные текстовые элементы для этой страницы
        if self.current_page in self.text_data:
            for text_item_data in self.text_data[self.current_page]:
                x = text_item_data['x'] * self.zoom_factor
                y = text_item_data['y'] * self.zoom_factor
                self.create_text_item_on_page(text_item_data['text'],
                                             QPointF(x, y),
                                             text_item_data.get('font_size', 12),
                                             text_item_data)
        for text_item in self.text_items:
            text_item.update_font_size()
        self.page_label.setText(f"Страница: {self.current_page + 1}/{self.total_pages}")
        self.page_spin.blockSignals(True)
        self.page_spin.setValue(self.current_page + 1)
        self.page_spin.blockSignals(False)

    def create_text_item_on_page(self, text, position, font_size=12, text_data=None):
        """Создает перемещаемый текстовый элемент на странице"""
        if text_data is None:
            text_data = {
                'text': text,
                'x': position.x() / self.zoom_factor,
                'y': position.y() / self.zoom_factor,
                'font_size': font_size,
                'vertical': False,
                'font_family': self._font_family_default,
                'font_path': ''
            }

        vertical = text_data.get('vertical', False)
        font_family = text_data.get('font_family', self._font_family_default)
        font_path = text_data.get('font_path', '')
        
        text_item = MovableTextItem(text, self.current_page, text_data, self, 
                                   font_size, vertical, font_family, font_path)
        text_item.setPos(position)
        text_item.adjustSize()

        self.scene.addItem(text_item)
        self.text_items.append(text_item)

        return text_item

    def get_pdf_rect(self):
        """Возвращает прямоугольник области PDF страницы в координатах сцены"""
        if not self.current_document:
            return QRectF(0, 0, 0, 0)

        page = self.current_document[self.current_page]
        zoom = self.zoom_factor
        width = page.rect.width * zoom
        height = page.rect.height * zoom
        return QRectF(0, 0, width, height)

    def add_text_at_position(self, scene_position):
        """Добавляет новый текст в указанной позиции с диалогом настроек"""
        if not self.current_document:
            return

        # Проверяем, что позиция находится в пределах PDF страницы
        pdf_rect = self.get_pdf_rect()
        if not pdf_rect.contains(scene_position):
            QMessageBox.warning(self, "Предупреждение", "Текст можно добавлять только внутри области PDF страницы")
            return

        # Получаем доступные шрифты
        available_fonts = self.get_available_fonts()
        
        # Получаем настройки по умолчанию
        defaults = self.settings_manager.get_default_text_data()
        default_font_family = defaults['font_family']
        default_font_size = defaults['font_size']
        default_vertical = defaults['vertical']
        
        # Показываем диалог ввода текста с настройками
        dialog = TextInputDialog(self, "", default_font_size, default_vertical, 
                                default_font_family, available_fonts)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            text_data = dialog.get_text_data()

            if text_data['text']:
                # Нормализуем координаты (сохраняем в координатах PDF)
                normalized_x = scene_position.x() / self.zoom_factor
                normalized_y = scene_position.y() / self.zoom_factor

                # Создаем данные текста
                text_item_data = {
                    'text': text_data['text'],
                    'x': normalized_x,
                    'y': normalized_y,
                    'font_size': text_data['font_size'],
                    'vertical': text_data['vertical'],
                    'font_family': text_data['font_family'],
                    'font_path': text_data['font_path']
                }

                # Добавляем в структуру данных
                if self.current_page not in self.text_data:
                    self.text_data[self.current_page] = []

                self.text_data[self.current_page].append(text_item_data)

                # Создаем визуальный элемент
                self.create_text_item_on_page(text_data['text'], scene_position,
                                            text_data['font_size'], text_item_data)

                direction = "вертикальный" if text_data['vertical'] else "горизонтальный"
                self.status_label.setText(f"Текст добавлен на страницу {self.current_page + 1}: '{text_data['text'][:50]}' ({direction}, шрифт {text_data['font_family']}, размер {text_data['font_size']})")

    def clear_current_page_text(self):
        """Очищает весь добавленный текст на текущей странице"""
        if self.current_page in self.text_data and self.text_data[self.current_page]:
            reply = QMessageBox.question(self, "Подтверждение",
                                        f"Удалить все добавленные тексты на странице {self.current_page + 1}?",
                                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                # Очищаем данные
                self.text_data[self.current_page] = []
                # Перезагружаем страницу
                self.load_page()
                self.status_label.setText(f"Все тексты удалены со страницы {self.current_page + 1}")

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.load_page()

    def next_page(self):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.load_page()

    def go_to_page(self, page_num):
        if 1 <= page_num <= self.total_pages:
            self.current_page = page_num - 1
            self.load_page()

    def zoom_changed(self, value):
        self.zoom_factor = value / 100.0
        self.zoom_label.setText(f"{value}%")
        self.load_page()

    def enable_text_mode(self):
        self.text_mode = not self.text_mode
        if self.text_mode:
            self.add_text_btn.setStyleSheet("background-color: #4CAF50; color: white;")
            self.status_label.setText("Режим добавления текста: Кликните в любое место страницы для добавления текста")
            self.graphics_view.setCursor(Qt.CursorShape.CrossCursor)
            self.graphics_view.setDragMode(QGraphicsView.DragMode.NoDrag)
        else:
            self.add_text_btn.setStyleSheet("")
            self.status_label.setText("Режим добавления текста выключен")
            self.graphics_view.setCursor(Qt.CursorShape.ArrowCursor)
            self.graphics_view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)

    def keyPressEvent(self, event):
        if event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_T:
            self.enable_text_mode()
        elif event.key() == Qt.Key_Escape and self.text_mode:
            self.enable_text_mode()
        elif event.key() == Qt.Key_Delete:
            # Удаление выделенных текстовых элементов
            selected_items = self.scene.selectedItems()
            for item in selected_items:
                if isinstance(item, MovableTextItem):
                    # Удаляем из данных
                    page_data = self.text_data.get(item.page_num, [])
                    if item.text_data in page_data:
                        page_data.remove(item.text_data)
                    # Удаляем из сцены
                    self.scene.removeItem(item)
                    if item in self.text_items:
                        self.text_items.remove(item)
                    self.status_label.setText(f"Текст удален")
        else:
            super().keyPressEvent(event)

    def print_dialog(self):
        """Диалог выбора страниц и принтера для печати"""
        if not self.current_document:
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Печать PDF")
        dialog.setModal(True)
        dialog.setMinimumWidth(400)

        layout = QFormLayout(dialog)

        # Выбор страниц
        pages_input = QLineEdit()
        pages_input.setPlaceholderText("Пример: 1,3,5-7,9 или 'all' для всех страниц")
        pages_input.setText("all")
        layout.addRow("Страницы для печати:", pages_input)

        # Получаем список принтеров
        printers = self.get_available_printers()
        printer_combo = QComboBox()
        printer_combo.addItems(printers)
        layout.addRow("Выберите принтер:", printer_combo)

        info_label = QLabel(f"Всего страниц в документе: {self.total_pages}")
        info_label.setStyleSheet("color: gray; font-size: 10pt;")
        layout.addRow("", info_label)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                      QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addRow(button_box)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            pages_text = pages_input.text().strip().lower()
            printer_name = printer_combo.currentText()

            pages_to_print = self.parse_pages(pages_text)

            if pages_to_print:
                self.show_print_preview(pages_to_print, printer_name)
            else:
                QMessageBox.warning(self, "Ошибка", "Неверный формат страниц.\nПример: 1,3,5-7,9")

    def get_available_printers(self):
        """Получает список доступных принтеров Windows"""
        printers = []
        try:
            for printer in win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS):
                printers.append(printer[2])
        except Exception as e:
            print(f"Ошибка получения списка принтеров: {e}")
            printers.append("Microsoft Print to PDF")

        if not printers:
            printers.append("Microsoft Print to PDF")
        return printers

    def parse_pages(self, pages_text):
        """Разбирает строку с номерами страниц"""
        if pages_text == 'all':
            return list(range(self.total_pages))

        pages = set()
        try:
            parts = pages_text.split(',')
            for part in parts:
                part = part.strip()
                if '-' in part:
                    start, end = map(int, part.split('-'))
                    for page in range(start - 1, end):
                        if 0 <= page < self.total_pages:
                            pages.add(page)
                else:
                    page = int(part) - 1
                    if 0 <= page < self.total_pages:
                        pages.add(page)
            return sorted(list(pages))
        except:
            return []

    def show_print_preview(self, pages, printer_name):
        """Показывает стандартный диалог предварительного просмотра перед печатью"""
        try:
            # Создаем PDF только с выбранными страницами и добавленным текстом
            temp_pdf = self.create_pdf_with_text(pages)

            if not temp_pdf or not os.path.exists(temp_pdf):
                QMessageBox.warning(self, "Ошибка", "Не удалось создать PDF для печати")
                return

            # Открываем документ для рендеринга
            doc = fitz.open(temp_pdf)

            # Настраиваем принтер
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            printer.setPrinterName(printer_name)
            printer.setPageOrientation(QPageLayout.Orientation.Portrait)
            printer.setFullPage(False)

            # Создаем диалог предварительного просмотра
            preview = QPrintPreviewDialog(printer, self)
            preview.setWindowTitle(f"Предварительный просмотр - {os.path.basename(self.current_file_path)}")
            preview.setWindowFlags(preview.windowFlags() | Qt.WindowType.WindowMaximizeButtonHint)

            def render_preview(printer_obj):
                """Отрисовка страниц для предварительного просмотра"""
                painter = QPainter()

                for idx in range(len(doc)):
                    page = doc[idx]

                    if idx > 0:
                        printer_obj.newPage()

                    if not painter.isActive():
                        painter.begin(printer_obj)

                    # Получаем размер области печати в пикселях
                    page_rect = printer_obj.pageRect(QPrinter.DevicePixel)

                    # Рассчитываем масштаб для размещения страницы на листе
                    scale_x = page_rect.width() / page.rect.width
                    scale_y = page_rect.height() / page.rect.height
                    scale = min(scale_x, scale_y)

                    # Рендерим страницу
                    matrix = fitz.Matrix(scale, scale)
                    pix = page.get_pixmap(matrix=matrix, alpha=False)

                    # Конвертируем в QImage
                    img_data = pix.tobytes("ppm")
                    qimage = QImage.fromData(img_data)

                    # Центрируем на странице
                    x_offset = max(0, (page_rect.width() - qimage.width()) // 2)
                    y_offset = max(0, (page_rect.height() - qimage.height()) // 2)

                    painter.drawImage(x_offset, y_offset, qimage)

                painter.end()

            preview.paintRequested.connect(render_preview)

            # Показываем предпросмотр
            if preview.exec() == QPrintPreviewDialog.Accepted:
                self.status_label.setText(f"Печать завершена на принтер {printer_name}")
                QMessageBox.information(self, "Успех", "Документ отправлен на печать")
            else:
                self.status_label.setText("Печать отменена")

            doc.close()

            # Удаляем временный файл через некоторое время
            QTimer.singleShot(3000, lambda: self.delete_temp_file(temp_pdf))

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть предварительный просмотр:\n{str(e)}")

    def create_pdf_with_text(self, pages=None):
        """Создает временный PDF с добавленным текстом"""
        if not self.current_document:
            return None
        
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        temp_file.close()
        
        try:
            new_doc = fitz.open()
            
            if pages is None:
                pages_to_include = range(self.total_pages)
            else:
                pages_to_include = pages
            
            # Собираем уникальные шрифты для встраивания
            fonts_to_embed = set()
            for page_num in pages_to_include:
                if page_num in self.text_data:
                    for text_item_data in self.text_data[page_num]:
                        font_path = text_item_data.get('font_path', '')
                        if font_path and os.path.exists(font_path):
                            fonts_to_embed.add(font_path)
            
            for page_num in pages_to_include:
                new_doc.insert_pdf(self.current_document, from_page=page_num, to_page=page_num)
                
                if page_num in self.text_data:
                    page = new_doc[page_num]
                    
                    # Встраиваем все нужные шрифты в страницу
                    for font_path in fonts_to_embed:
                        if os.path.exists(font_path):
                            font_name = os.path.splitext(os.path.basename(font_path))[0]
                            page.insert_font(fontname=font_name, fontfile=font_path, 
                                            fontbuffer=None, set_simple=False, encoding=2)
                    
                    page_text_items = [item for item in self.text_items if item.page_num == page_num]
                    
                    for text_item in page_text_items:
                        # Получаем точку в PDF координатах (без инверсии)
                        insert_point = text_item.get_text_baseline_point(None, self.zoom_factor)
                        
                        text = text_item.toPlainText()
                        font_size = text_item._base_font_size
                        vertical = text_item._vertical
                        
                        # Получаем имя шрифта для вставки
                        font_name = text_item._font_family
                        if text_item._font_path and os.path.exists(text_item._font_path):
                            font_name = os.path.splitext(os.path.basename(text_item._font_path))[0]
                        
                        if vertical:
                            page.insert_text(insert_point, text, fontsize=font_size, fontname=font_name, rotate=90)
                        else:
                            page.insert_text(insert_point, text, fontsize=font_size, fontname=font_name)
            
            new_doc.save(temp_file.name)
            new_doc.close()
            return temp_file.name
            
        except Exception as e:
            print(f"Ошибка создания PDF: {e}")
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
            return None

    def delete_temp_file(self, file_path):
        """Удаляет временный файл"""
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
        except Exception as e:
            print(f"Ошибка удаления временного файла: {e}")