"""PyInstaller-aware loader for the dashboard HTML template."""
import os
import sys


def _template_dir():
    if getattr(sys, "frozen", False):
        base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(sys.executable)))
        return os.path.join(base, "pi_portfolio", "templates")
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")


def load_html_template():
    """Read templates/dashboard.html (bundled inside the .exe when frozen)."""
    path = os.path.join(_template_dir(), "dashboard.html")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()
