"""
Файл содержит в себе настройки путей к базе данных, логам и общей папке для хранения данных.
"""

import os

# Название общей папки для хранения данных
APPLICATION_FOLDER = "AbTradebot"

# Корень пользователя
ROOT = os.path.expanduser("~")

# Путь до общей папки
FOLDER_PATH = os.path.join(ROOT, APPLICATION_FOLDER)

# Путь до папки с логами
LOGS_FOLDER_PATH = os.path.join(FOLDER_PATH, "logs")

# Создание общей папки для хранения данных
if not os.path.exists(FOLDER_PATH):
    os.makedirs(FOLDER_PATH)

# Создание папки для логов
if not os.path.exists(LOGS_FOLDER_PATH):
    os.makedirs(LOGS_FOLDER_PATH)

# URL базы данных для sqlalchemy
DATABASE_URL: str = f'aiosqlite:///{FOLDER_PATH}/secrets.db'
