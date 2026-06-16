from TextInputDialog import TextInputDialog


import fitz
import os
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QFont, QFontMetrics, QFontDatabase, QTextDocument
from PySide6.QtWidgets import QDialog, QGraphicsTextItem


class MovableTextItem(QGraphicsTextItem):
    """Перемещаемый текстовый элемент с поддержкой вертикального (повернутого) текста"""
    def __init__(self, text, page_num, text_data, parent_callback, font_size=12, vertical=False, font_family='arial', font_path=''):
        super().__init__(text)
        self.page_num = page_num
        self.text_data = text_data
        self.parent_callback = parent_callback
        self.is_moving = False
        self.drag_offset = None
        self._vertical = vertical
        self._font_size = font_size
        self._font_path = font_path
        
        # Загружаем шрифт если указан путь (с кэшированием)
        self._font_family = font_family
        if font_path and os.path.exists(font_path):
            # === КЭШИРОВАНИЕ ===
            if (hasattr(self.parent_callback, 'font_cache') and 
                font_path in self.parent_callback.font_cache):
                font_id, cached_name = self.parent_callback.font_cache[font_path]
            else:
                font_id = QFontDatabase.addApplicationFont(font_path)
                if font_id != -1 and hasattr(self.parent_callback, 'font_cache'):
                    families = QFontDatabase.applicationFontFamilies(font_id)
                    font_name = families[0] if families else os.path.splitext(os.path.basename(font_path))[0]
                    self.parent_callback.font_cache[font_path] = (font_id, font_name)
            
            if font_id != -1:
                families = QFontDatabase.applicationFontFamilies(font_id)
                if families:
                    self._font_family = families[0]
        
        self._base_font_size = font_size  # Базовый размер шрифта в PDF-координатах
        self.document().setDocumentMargin(0)
        
        # Настройка внешнего вида
        self.update_font_size()

        # Устанавливаем точку вращения 
        self.setTransformPoint(self._vertical)   # исправлена опечатка

        # Применяем поворот если нужно
        if vertical:
            self.setRotation(-90)

        # Включаем возможность перемещения
        self.setFlag(QGraphicsTextItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsTextItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setCursor(Qt.CursorShape.SizeAllCursor)

        # Отключаем редактирование по умолчанию
        self.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)

    def get_text_baseline_point(self, page_height=None, zoom_factor=None):
        """
        Возвращает точку для вставки в PDF.
        """
        if self._vertical:
            # Для вертикального текста используем sceneBoundingRect()
            # Это дает реальные границы элемента после всех трансформаций
            scene_rect = self.sceneBoundingRect()
            
            doc = self.document()
            margin = doc.documentMargin()
            font_metrics = QFontMetrics(self.font())

            # Левый верхний угол повернутого текста
            insert_x = scene_rect.bottomRight().x() - margin - font_metrics.descent() 
            insert_y = scene_rect.bottomLeft().y() - margin 
            
            if zoom_factor:
                pdf_x = insert_x / zoom_factor
                pdf_y = insert_y / zoom_factor
            else:
                pdf_x = insert_x
                pdf_y = insert_y
        else:
            # Горизонтальный текст
            item_pos = self.scenePos()
            doc = self.document()
            margin = doc.documentMargin()
            font_metrics = QFontMetrics(self.font())
            
            baseline_x = item_pos.x() + margin
            baseline_y = item_pos.y() + margin + font_metrics.ascent()
            
            if zoom_factor:
                pdf_x = baseline_x / zoom_factor
                pdf_y = baseline_y / zoom_factor
            else:
                pdf_x = baseline_x
                pdf_y = baseline_y
        
        return fitz.Point(pdf_x, pdf_y)

    def update_font_size(self):
        """Обновляет размер шрифта с учетом текущего зума"""
        if self.parent_callback:
            zoom_factor = self.parent_callback.get_zoom_factor()
            # Размер шрифта на экране = базовый размер * зум
            current_font_size = self._base_font_size * zoom_factor * (72/96)
            font = QFont(self._font_family, current_font_size)
            self.setFont(font)
            
            # Важно: после изменения шрифта нужно обновить boundingRect
            self.adjustSize()
            self.prepareGeometryChange()

    @property
    def vertical(self):
        return self._vertical

    @vertical.setter
    def vertical(self, value):
        if self._vertical != value:
            self._vertical = value
            if value:
                self.setRotation(-90)
            else:
                self.setRotation(0)
        self.adjustSize()
        self.prepareGeometryChange()
       
    def get_visible_rect(self):
        """Возвращает видимый прямоугольник элемента в координатах сцены"""
        if self._vertical:
            rect = self.boundingRect()
            return QRectF(0, 0, rect.height(), rect.width())
        return self.boundingRect()

    def constrain_to_pdf_bounds(self, pos):
        """Ограничивает позицию элемента границами PDF страницы"""
        if not self.parent_callback:
            return pos

        pdf_rect = self.parent_callback.get_pdf_rect()
        if pdf_rect.isEmpty():
            return pos

        # Временно устанавливаем позицию для проверки
        old_pos = self.pos()
        self.setPos(pos)
        
        # Получаем реальные границы после установки позиции
        scene_rect = self.sceneBoundingRect()
        
        # Проверяем выход за границы
        new_x = pos.x()
        new_y = pos.y()
        
        if scene_rect.left() < pdf_rect.left():
            new_x += pdf_rect.left() - scene_rect.left()
        elif scene_rect.right() > pdf_rect.right():
            new_x -= scene_rect.right() - pdf_rect.right()
        
        if scene_rect.top() < pdf_rect.top():
            new_y += pdf_rect.top() - scene_rect.top()
        elif scene_rect.bottom() > pdf_rect.bottom():
            new_y -= scene_rect.bottom() - pdf_rect.bottom()
        
        # Возвращаем исходную позицию
        self.setPos(old_pos)
        
        return QPointF(new_x, new_y)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_moving = True
            # Сохраняем смещение между точкой клика и позицией элемента
            self.drag_offset = self.scenePos() - event.scenePos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.is_moving:
            # Вычисляем новую позицию на основе смещения
            new_pos = event.scenePos() + self.drag_offset

            # Ограничиваем позицию
            new_pos = self.constrain_to_pdf_bounds(new_pos)

            # Устанавливаем новую позицию
            self.setPos(new_pos)

            # Обновляем данные в реальном времени (сохраняем в PDF-координатах)
            if self.text_data and self.parent_callback:
                zoom_factor = self.parent_callback.get_zoom_factor()
                self.text_data['x'] = new_pos.x() / zoom_factor
                self.text_data['y'] = new_pos.y() / zoom_factor

            if self.parent_callback:
                self.parent_callback.on_text_moved(self.page_num, self.text_data)
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.is_moving:
            self.is_moving = False
            self.drag_offset = None
            self.setCursor(Qt.CursorShape.SizeAllCursor)
        super().mouseReleaseEvent(event)
    
    def setPlainText(self, text):
        """Переопределяем setPlainText для автоматического обновления размера"""
        super().setPlainText(text)
        # Принудительно обновляем размер после изменения текста
        self.adjustSize()
        self.prepareGeometryChange()
    
    def setTransformPoint(self, vertical):
        rect = self.boundingRect()
        if not vertical:
            #self.setTransformOriginPoint(rect.topLeft())
            self.setTransformOriginPoint(rect.bottomLeft())
        else:
          
            self.setTransformOriginPoint(rect.topLeft())
            #self.setTransformOriginPoint(self.boundingRect().bottomLeft())
    
    def mouseDoubleClickEvent(self, event):
        """Двойной клик для редактирования текста и параметров"""
        # Получаем доступные шрифты от родителя
        available_fonts = []
        if self.parent_callback and hasattr(self.parent_callback, 'get_available_fonts'):
            available_fonts = self.parent_callback.get_available_fonts()
        
        # Создаем диалог для редактирования текста
        dialog = TextInputDialog(self.parent_callback,
                                self.text_data['text'],
                                self.text_data.get('font_size', 12),
                                self.text_data.get('vertical', False),
                                self.text_data.get('font_family', self._font_family),
                                available_fonts)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_data = dialog.get_text_data()
            if new_data['text']:
                old_vertical = self._vertical

                # Обновляем данные
                self.text_data['text'] = new_data['text']
                self.text_data['font_size'] = new_data['font_size']
                self.text_data['vertical'] = new_data['vertical']
                self.text_data['font_family'] = new_data['font_family']
                self.text_data['font_path'] = new_data['font_path']

                self._base_font_size = new_data['font_size']
                self._font_family = new_data['font_family']
                self._font_path = new_data['font_path']
                
                # === КЭШИРОВАНИЕ ШРИФТА ПРИ РЕДАКТИРОВАНИИ ===
                if self._font_path and os.path.exists(self._font_path):
                    if (hasattr(self.parent_callback, 'font_cache') and 
                        self._font_path in self.parent_callback.font_cache):
                        font_id, _ = self.parent_callback.font_cache[self._font_path]
                    else:
                        font_id = QFontDatabase.addApplicationFont(self._font_path)
                        if font_id != -1 and hasattr(self.parent_callback, 'font_cache'):
                            families = QFontDatabase.applicationFontFamilies(font_id)
                            font_name = families[0] if families else os.path.splitext(os.path.basename(self._font_path))[0]
                            self.parent_callback.font_cache[self._font_path] = (font_id, font_name)

                # Обновляем отображение
                self.update_font_size()
                self.setPlainText(new_data['text'])

                # Обновляем вертикальность
                self._vertical = new_data['vertical']
                self.setTransformPoint(self._vertical)   # исправлено имя метода
                
                if new_data['vertical']:
                    self.setRotation(-90)
                else:
                    self.setRotation(0)

                # Корректировка позиции при смене направления
                if old_vertical != self._vertical:
                    new_pos = self.constrain_to_pdf_bounds(self.scenePos())
                    self.setPos(new_pos)

                    if self.text_data and self.parent_callback:
                        zoom_factor = self.parent_callback.get_zoom_factor()
                        self.text_data['x'] = new_pos.x() / zoom_factor
                        self.text_data['y'] = new_pos.y() / zoom_factor

                if self.parent_callback:
                    self.parent_callback.on_text_edited(self.page_num, self.text_data)

        super().mouseDoubleClickEvent(event)

    def focusOutEvent(self, event):
        """При потере фокуса завершаем редактирование"""
        new_text = self.toPlainText()
        if new_text != self.text_data['text']:
            self.text_data['text'] = new_text
            if self.parent_callback:
                self.parent_callback.on_text_edited(self.page_num, self.text_data)
        self.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self.setCursor(Qt.CursorShape.SizeAllCursor)
        super().focusOutEvent(event)