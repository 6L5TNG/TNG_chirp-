# -*- coding: utf-8 -*-
"""
MPDA (Multi-Parallel Differential ASK) Terminal Application Launcher
Entry point for the application.
"""
import sys
import os

# Ensure the application directory is in the path
app_dir = os.path.dirname(os.path.abspath(__file__))
if app_dir not in sys.path:
    sys.path.insert(0, app_dir)


def main():
    """Main entry point for the MPDA terminal application."""
    from mpda_app.main import run_application
    run_application()


if __name__ == "__main__":
    main()
