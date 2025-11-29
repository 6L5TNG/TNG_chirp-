# -*- coding: utf-8 -*-
"""
MPDA Terminal Application - Main Entry Point
"""
import sys


def run_application():
    """Initialize and run the PyQt6 application."""
    from PyQt6.QtWidgets import QApplication
    from mpda_app.ui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("MPDA Terminal")
    app.setApplicationVersion("1.0.0")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    run_application()
