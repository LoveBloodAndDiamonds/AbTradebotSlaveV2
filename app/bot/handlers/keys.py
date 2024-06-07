from aiogram import types
from aiogram.filters import CommandObject
from binance import Client

from app.database import Database, SecretsORM
from app.logic.connectors.bybit_con import AsyncClient
from app.config import logger


async def keys_command_handler(message: types.Message, command: CommandObject, db: Database) -> types.Message:
    """/keys command"""
    secrets: SecretsORM = await db.secrets_repo.get()

    # Удаление ключей в случае, когда юзер ввел их с ошибкой, или их надо изменить
    if command.command == "clear_keys":
        secrets.binance_api_key = None
        secrets.binance_api_secret = None
        secrets.bybit_api_key = None
        secrets.bybit_api_secret = None
        await db.secrets_repo.update(secrets)
        return await message.answer("Ключи успешно удалены")

    # Добавление новых ключей
    if not command.args or command.command == "keys":
        return await message.answer("Чтобы ввести ключ, необходимо вставить его через пробел после команды, например:\n"
                                    "<blockquote>/key_binance AsdfFhgjk</blockquote>\n\n"
                                    "<b>Доступные команды:</b>\n"
                                    "/key_binance\n"
                                    "/secret_binance\n"
                                    "/key_bybit\n"
                                    "/secret_bybit\n\n"
                                    "<b>Удалить все ключи:</b>\n"
                                    "/clear_keys\n\n"
                                    "<b>Введеные ключи:</b>\n"
                                    f"Binance Api Key:\n<tg-spoiler> {secrets.binance_api_key}</tg-spoiler>\n\n"
                                    f"Binance Api Secret:\n<tg-spoiler> {secrets.binance_api_secret}</tg-spoiler>\n\n"
                                    f"Bybit Api Key:\n<tg-spoiler> {secrets.bybit_api_key}</tg-spoiler>\n\n"
                                    f"Bybit Api Secret:\n<tg-spoiler> {secrets.bybit_api_secret}</tg-spoiler>")

    key: str = command.args.strip()

    match command.command:
        case "key_binance":
            secrets.binance_api_key = key
        case "secret_binance":
            secrets.binance_api_secret = key
        case "key_bybit":
            secrets.bybit_api_key = key
        case "secret_bybit":
            secrets.bybit_api_secret = key

    try:
        if command.command in ["key_binance", "secret_binance"]:
            if all([secrets.binance_api_secret, secrets.binance_api_key]):
                client = Client(api_key=secrets.binance_api_key, api_secret=secrets.binance_api_secret)
                permissions = client.get_account_api_permissions()
                if not permissions["enableFutures"]:
                    raise KeyError("В настройках API ключа нужно разрешить торгволю фьючерсами.")
                await message.answer("Ключи прошли проверку.")

        if command.command in ["key_bybit", "secret_bybit"]:
            if all([secrets.bybit_api_key, secrets.bybit_api_secret]):
                client = await AsyncClient.create(api_key=secrets.bybit_api_key, api_secret=secrets.bybit_api_secret)
                key_info: dict = await client.get_api_key_information()
                logger.debug(f"Информация о bybit api key: {key_info}")

                if key_info["retCode"] != 0:
                    raise ConnectionError(str(key_info))

                key_info: dict = key_info["result"]

                assert key_info["readOnly"] == 0, f"Проверка на разрешение записи к апи ключу: {key_info}"
                assert key_info["permissions"]["ContractTrade"] == ["Order", "Position"], \
                    f"Нет разрешений на торговлю фьючерсами"

                await message.answer("✅ Ключи прошли проверку.")
    except Exception as e:
        return await message.answer(f"🛑 Произошла ошибка при проверке API ключей: {e}", parse_mode=None)

    await db.secrets_repo.update(secrets)
    return await message.answer("✅ Ключ обновлен. После введения второго ключа происходит их проверка.")
