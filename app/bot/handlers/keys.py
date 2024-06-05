from aiogram import types
from aiogram.filters import CommandObject
from binance import Client
from pybit.unified_trading import UserHTTP

from app.database import Database, SecretsORM


async def keys_command_handler(message: types.Message, command: CommandObject, db: Database) -> types.Message:
    """/keys command"""
    secrets: SecretsORM = await db.secrets_repo.get()

    if not command.args or command.command == "keys":
        return await message.answer("Чтобы ввести ключ, необходимо вставить его через пробел после команды, например:\n"
                                    "<blockquote>/key_binance AsdfFhgjk</blockquote>\n\n"
                                    "Доступные команды:\n"
                                    "/key_binance\n"
                                    "/secret_binance\n"
                                    "/key_bybit\n"
                                    "/secret_bybit\n\n"
                                    "<b>Введеные ключи:</b>\n"
                                    f"binance api:\n<tg-spoiler>{secrets.binance_api_key}</tg-spoiler>\n\n"
                                    f"binance secret:\n<tg-spoiler>{secrets.binance_api_secret}</tg-spoiler>\n\n"
                                    f"bybit api:\n<tg-spoiler>{secrets.bybit_api_key}</tg-spoiler>\n\n"
                                    f"bybit secret:\n<tg-spoiler>{secrets.bybit_api_secret}</tg-spoiler>")

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
                client = UserHTTP(api_key=secrets.bybit_api_key, api_secret=secrets.bybit_api_secret)
                key_info = client.get_api_key_information()
                if key_info["result"]["readOnly"] != 0:
                    raise KeyError("В настройках API ключа нужно разрешить торговлю фьючерсами.")
                await message.answer("Ключи прошли проверку.")
    except Exception as e:
        return await message.answer(f"Произошла ошибка при валидации API ключей: {e}")

    await db.secrets_repo.update(secrets)
    return await message.answer("Ключ обновлен. После введения второго ключа происходит их валидация.")
