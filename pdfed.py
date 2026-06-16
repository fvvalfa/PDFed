import sys
import os
from PySide6.QtWidgets import QApplication
from PDFViewer import PDFViewer


def main():
    app = QApplication(sys.argv)
    
    viewer = PDFViewer()
    viewer.showMaximized()
    
    # Проверяем аргументы командной строки
    if len(sys.argv) > 1:
        # Объединяем аргументы, если путь был разбит пробелами
        pdf_path = ' '.join(sys.argv[1:])
        
        # Убираем возможные кавычки из строки
        pdf_path = pdf_path.strip('"').strip("'")
        
        # Проверяем существование файла
        if os.path.exists(pdf_path):
            if pdf_path.lower().endswith('.pdf'):
                viewer.open_pdf_file(pdf_path)
            else:
                print(f"Файл не является PDF: {pdf_path}")
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(viewer, "Ошибка", f"Файл не является PDF:\n{pdf_path}")
        else:
            print(f"Файл не найден: {pdf_path}")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(viewer, "Ошибка", f"Файл не найден:\n{pdf_path}")
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()