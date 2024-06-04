"""
Этот файл отвечает за логику запуска
"""
import asyncio
import platform

import requests

from config import DATABASE_URL, APPLICATION_FOLDER, VERSION
from database import Database, SecretsORM
from bot import start_bot


class _Validator:
    """
    Класс, который валидирует введенные пользователем данные.
    """

    @staticmethod
    def validate_bot_token(bot_token: str) -> None:
        """
        Валидация токена телеграм бота.

        Responce example:
        {'ok': True, 'result': {'id': 5029563988, 'is_bot': True, 'first_name': 'DiamondDumpStats',
                                    'username': 'AYAZpersonal_bot', 'can_join_groups': True,
                                    'can_read_all_group_messages': True, 'supports_inline_queries': False,
                                    'can_connect_to_business': False}}
        :param bot_token:
        :raises ValueError если токен невалидный
        :return:
        """
        responce: requests.Response = requests.get(f"https://api.telegram.org/bot{bot_token}/getMe")
        # bot_info: dict = responce.json()
        if not responce.status_code == 200:
            raise ConnectionError(f"Ошибка при получении данных телеграм бота: {responce.text}")

    @staticmethod
    def valite_license_key(license_key: str) -> None:
        """
        Валидация ключа лицензии.
        :param license_key:
        :raises ValueError если ключ невалидный
        :return:
        """
        try:
            _, host, port = license_key.split(":")
            responce: requests.Response = requests.get(f"http://{host}:{port}/license_key/{license_key}")
            if responce.status_code != 200:
                raise ConnectionError("Ошибка при соединении с главным сервером.")
        except Exception as e:
            raise Exception(f"Ошибка при валидации ключа лицензии: {e}")


async def _gui_case(db: Database, secrets: SecretsORM) -> None:
    """
    Кейс, при котором надо отобразить графический интерфейс.
    Подходит для Windows и MacOS.
    :return:
    """
    import tkinter as tk
    from threading import Thread
    import webbrowser

    async def _on_start_btn():
        try:
            bot_token: str = bot_token_entry.get().strip()
            telegram_id: int = int(telegram_id_entry.get().strip())
            license_key: str = license_key_entry.get().strip()

            _Validator.validate_bot_token(bot_token=bot_token)
            _Validator.valite_license_key(license_key=license_key)

            secrets.bot_token = bot_token
            secrets.admin_telegram_id = telegram_id
            secrets.license_key = license_key

            await db.secrets_repo.update(secrets)

        except Exception as e:
            header.config(text=f"Ошибка: {e}", foreground="red")
        else:
            w.destroy()
            await start_bot()

    w: tk.Tk = tk.Tk()
    w.title(APPLICATION_FOLDER + " v" + VERSION)
    w.geometry("350x450+500+500")

    header = tk.Label(w, text="")
    header.pack()
    tk.Label().pack()

    tk.Label(w, text="Токен телеграм бота", font=("Arial", 17, "bold")).pack()
    link_1 = tk.Label(
        w, text="Токен бота можно получить тут (Ссылка)\n", font=("Arial", 14, "underline"), cursor="hand2")
    link_1.bind("<Button-1>", func=lambda e: webbrowser.open_new("https://t.me/BotFather"))
    link_1.pack()
    bot_token_entry = tk.Entry(w)
    bot_token_entry.insert(0, secrets.bot_token) if secrets.bot_token else None  # noqa
    bot_token_entry.pack()
    tk.Label().pack()

    tk.Label(w, text="Телеграм айди", font=("Arial", 17, "bold")).pack()
    link_2 = tk.Label(
        w, text="Телеграм айди можно получить тут (Ссылка)\n", font=("Arial", 14, "underline"), cursor="hand2")
    link_2.bind("<Button-1>", func=lambda e: webbrowser.open_new("https://t.me/getmyid_bot"))
    link_2.pack()
    telegram_id_entry = tk.Entry(w)
    telegram_id_entry.insert(0, secrets.admin_telegram_id) if secrets.admin_telegram_id else None  # noqa
    telegram_id_entry.pack()
    tk.Label().pack()

    tk.Label(w, text="Ключ лицензии", font=("Arial", 17, "bold")).pack()
    link_3 = tk.Label(
        w, text="Приобрести ключ лицензии можно тут (Ссылка)\n", font=("Arial", 14, "underline"), cursor="hand2")
    link_3.bind("<Button-1>", func=lambda e: webbrowser.open_new("https://t.me/getmyid_bot"))
    link_3.pack()
    license_key_entry = tk.Entry(w)
    license_key_entry.insert(0, secrets.license_key) if secrets.license_key else None  # noqa
    license_key_entry.pack()
    tk.Label().pack()

    tk.Button(w, text="Запуск", command=lambda: Thread(
        daemon=True,
        target=asyncio.run,
        args=(_on_start_btn(),)
    ).start()).pack()

    w.mainloop()


async def _cli_case(db: Database, secrets: SecretsORM) -> None:
    """
    Кейс, при котором не нужно отображать графический интерфейс.
    Подходит для Linux - серверов.
    :return:
    """
    import json

    print(f"Добро пожаловать в {APPLICATION_FOLDER} v{VERSION}!")

    with open(".linux/secrets.json", "r") as f:
        secrets_json: dict = json.load(f)

    _Validator.validate_bot_token(bot_token=secrets_json["bot_token"])
    _Validator.valite_license_key(license_key=secrets_json["license_key"])

    secrets.bot_token = secrets_json["bot_token"]
    secrets.license_key = secrets_json["license_key"]
    secrets.admin_telegram_id = secrets_json["telegram_admin_id"]

    await db.secrets_repo.update(secrets)


async def main() -> None:
    """
    Входная точка программы, определяет каким методом нужно принять инпуты от
    пользователя.
    :return:
    """
    system: str = platform.system()  # Darwin - MacOS, Linux - Linux, Windows - Windows

    # Создаем запись с секретными ключами в базе данных, если ее еще там нет.
    db: Database = await Database.create(database_url=DATABASE_URL)
    secrets: SecretsORM | None = await db.secrets_repo.get()

    if secrets is None:  # If secrets was newer created
        await db.secrets_repo.add(SecretsORM())
        secrets: SecretsORM = await db.secrets_repo.get()

    match system:
        case "Darwin" | "Windows":
            await _gui_case(db, secrets)
        case "Linux":
            await _cli_case(db, secrets)
        case _:
            await _cli_case(db, secrets)


if __name__ == '__main__':
    asyncio.run(main())
