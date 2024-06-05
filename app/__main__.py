"""
Этот файл отвечает за логику запуска приложения.
"""

import asyncio
import platform
import time

import requests

from app.bot import start_bot
from app.config import DATABASE_URL, APPLICATION_FOLDER, VERSION, log_errors, logger, FOLDER_PATH, LOGS_FOLDER_PATH
from app.database import Database, SecretsORM


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


@log_errors
async def _cli_case(db: Database, secrets: SecretsORM) -> None:
    """
    Кейс, при котором надо отобразить графический интерфейс.
    Подходит для Windows и MacOS.
    :return:
    """
    print(f"""
Добро пожаловать в {APPLICATION_FOLDER} v{VERSION}!

При первом запуске робота необходмо ввести некоторые данные, в будущем эти данные
будут автоматически предзаполнены, и когда программа просит их ввести, если Вы
не хотите их менять - нужно нажать клавишу ENTER.

Все секретные данные хранятся на Вашем компьютере по пути:
{FOLDER_PATH}
Логи хранятся по пути:
{LOGS_FOLDER_PATH}
При закрытии консоли - робот перестанет работать.
В консоли отображаются логи программы.
 
                            [1. Токен бота]
Его можно получить при создании телеграм бота, который будет выступать в качестве
панели управления роботом. Создать телеграм бота можно тут: -> https://t.me/BotFather

                            [2. Телеграм ID]
Телеграм ID нужен, чтобы бот отвечал только на Ваши сообщения, получить его можно
отправив любое сообщение с Вашего аккаунта в этого бота: -> https://t.me/getmyid_bot

                            [3. Ключ лицензии]
Ключ лицензии нужен для взаимодействия с главным сервером, который генерирует сигналы,
приобрести его можно тут: -> https://t.me/Anton_Filipchuk

""")

    # Ввод токена телеграм бота
    while True:
        if not secrets.bot_token:
            bot_input_text: str = "Введите токен бота.\n-> "
        else:
            bot_input_text: str = (f"Введите токен бота.\nВведите пустую строку, чтобы использовать "
                                   f"'{secrets.bot_token}'\n -> ")
        bot_token_input: str = input(bot_input_text)
        bot_token = secrets.bot_token if not bot_token_input.strip() else bot_token_input.strip()

        try:
            _Validator.validate_bot_token(bot_token=bot_token)
            logger.success("Токен телеграм бота успешно прошел проверку.\n")
            break
        except Exception as e:
            logger.error(f"Ошибка при проверке токена бота: {e}\n")
    time.sleep(.05)  # Задержка, чтобы лог успел встать на нужное место

    # Ввод телеграм айди пользователя
    if not secrets.admin_telegram_id:
        telegram_id_input_text: str = "Введите Ваш телеграм айди.\n-> "
    else:
        telegram_id_input_text: str = (f"Введите Ваш телеграм айди\nВведите пустую строку, чтобы использовать "
                                       f"'{secrets.admin_telegram_id}'\n -> ")
    telegram_id_input: str = input(telegram_id_input_text)
    telegram_id = secrets.admin_telegram_id if not telegram_id_input.strip() else telegram_id_input.strip()
    logger.info("Если бот не будет отвечать на Ваши команды - проверьте телеграм айди.\n")
    time.sleep(.05)  # Задержка, чтобы лог успел встать на нужное место

    # Ввод ключа лицензии
    while True:
        if not secrets.license_key:
            license_key_input_text: str = "Введите ключ лицензии.\n-> "
        else:
            license_key_input_text: str = (f"Введите ключ лицензии\nВведите пустую строку, чтобы использовать "
                                           f"'{secrets.license_key}'\n -> ")
        license_key_input: str = input(license_key_input_text)
        license_key = secrets.license_key if not license_key_input.strip() else license_key_input.strip()

        try:
            _Validator.valite_license_key(license_key=license_key)
            logger.success("Ключ лицензии успешно прошел проверку.\n")
            break
        except Exception as e:
            logger.error(f"Ошибка при проверке ключа лицензии: {e}\n")

    # Обновление данных в базе данных.
    secrets.bot_token = bot_token
    secrets.admin_telegram_id = telegram_id
    secrets.license_key = license_key
    await db.secrets_repo.update(secrets)


async def _from_json_case(db: Database, secrets: SecretsORM) -> None:
    """
    Кейс, при котором не нужно отображать графический интерфейс.
    Подходит для Linux - серверов.
    :return:
    """
    import json

    with open(".linux/secrets.json", "r") as f:
        secrets_json: dict = json.load(f)

    _Validator.validate_bot_token(bot_token=secrets_json["bot_token"])
    _Validator.valite_license_key(license_key=secrets_json["license_key"])

    secrets.bot_token = secrets_json["bot_token"]
    secrets.license_key = secrets_json["license_key"]
    secrets.admin_telegram_id = secrets_json["telegram_admin_id"]

    await db.secrets_repo.update(secrets)


@log_errors
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
            await _cli_case(db, secrets)
        case _:
            await _from_json_case(db, secrets)

    await start_bot()


if __name__ == '__main__':
    asyncio.run(main())
