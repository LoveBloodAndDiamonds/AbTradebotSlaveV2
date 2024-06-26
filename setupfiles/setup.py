"""
This is a setup.py script generated by py2applet

Usage:
    python3 setup.py py2app -A

Необходимо перенесети __main__.py выше, чтобы он не являлся частью пакета, в таком случае
частично-успешно компилируется.

"""

from setuptools import setup

# path ['__pycache__', 'site.py', 'app_icon.ico', '__boot__.py', 'lib', '__error__.sh']

APP_NAME = "AbTradebot1"
APP = ["main.py"]
DATA_FILES = [
    ("app", "app")
]
OPTIONS = {
    "iconfile": "static/app_icon.ico",
    "argv_emulation": True
}

setup(
    app=APP,
    name=APP_NAME,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
