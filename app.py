"""
OCR Master — Bank Statement Extractor
Run:  python app.py   or   ./run.sh
"""
import sys
from pathlib import Path

# Windows: set Tesseract path before any OCR import
if sys.platform == "win32":
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon

from ui.styles import DARK_THEME
from ui.main_window import MainWindow
from core.storage import init_db


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("OCR Master")
    app.setApplicationVersion("1.0")
    app.setOrganizationName("OCR Master")
    app.setStyleSheet(DARK_THEME)

    # Icon (optional — drop ocr_master.png next to app.py to use it)
    icon_path = Path(__file__).parent / "ocr_master.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    init_db()

    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
