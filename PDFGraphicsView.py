from MovableTextItem import MovableTextItem


from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QMouseEvent, QWheelEvent
from PySide6.QtWidgets import QGraphicsView


class PDFGraphicsView(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.scroll_accumulator = 0
        self.scroll_timer = QTimer()
        self.scroll_timer.setSingleShot(True)
        self.scroll_timer.timeout.connect(self.reset_scroll_accumulator)

    def reset_scroll_accumulator(self):
        """Сбрасывает аккумулятор скролла"""
        self.scroll_accumulator = 0

    def wheelEvent(self, event: QWheelEvent):
        # Проверяем, зажат ли Ctrl для изменения масштаба
        if event.modifiers() & Qt.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                new_value = self.parent.zoom_slider.value() + 10
            else:
                new_value = self.parent.zoom_slider.value() - 10
            self.parent.zoom_slider.setValue(min(300, max(10, new_value)))
        else:
            # Обычный скроллинг - перелистываем страницы с накоплением
            delta = event.angleDelta().y()
            self.scroll_accumulator += delta
            
            # Сбрасываем таймер
            self.scroll_timer.start(500)  # 500 мс бездействия для сброса
            
            # Определяем направление и количество страниц для перелистывания
            pages_to_scroll = abs(self.scroll_accumulator) // 120  # 120 - стандартный шаг колеса
            
            if pages_to_scroll > 0:
                if self.scroll_accumulator > 0:
                    # Скролл вверх - предыдущие страницы
                    new_page = max(0, self.parent.current_page - pages_to_scroll)
                    if new_page != self.parent.current_page:
                        self.parent.current_page = new_page
                        self.parent.load_page()
                        self.scroll_accumulator = 0
                else:
                    # Скролл вниз - следующие страницы
                    new_page = min(self.parent.total_pages - 1, self.parent.current_page + pages_to_scroll)
                    if new_page != self.parent.current_page:
                        self.parent.current_page = new_page
                        self.parent.load_page()
                        self.scroll_accumulator = 0

    def mousePressEvent(self, event: QMouseEvent):
        if self.parent.text_mode and event.button() == Qt.LeftButton:
            # Проверяем, есть ли текстовый элемент под курсором
            scene_pos = self.mapToScene(event.pos())
            items_under_cursor = self.scene().items(scene_pos)

            # Проверяем, есть ли среди элементов MovableTextItem
            has_text_item = any(isinstance(item, MovableTextItem) for item in items_under_cursor)

            if has_text_item:
                # Если есть текст под курсором - передаем событие дальше для перемещения
                super().mousePressEvent(event)
            else:
                # Если текста нет - добавляем новый
                self.parent.add_text_at_position(scene_pos)
        else:
            super().mousePressEvent(event)