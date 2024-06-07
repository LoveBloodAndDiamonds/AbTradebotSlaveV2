from datetime import datetime

from aiogram import types
from aiogram.filters import CommandObject

from app.logic import Logic


def _parse_command(command: CommandObject) -> list[list]:
    """
    Функция парсит введенную команду с возможностью ввести несколько стратегий в одной команде.
    Возвращает список списков по настройке стратегии вида:
    [[strategy_name: str, risk_usdt: float, trades_count: int | None], ..., ...].
    :param command:
    :return:
    """
    strategies_params: list[list[str, float, int | None]] = []  # noqa

    for line in command.args.split("\n"):

        line: str = line.strip()

        if not line:
            continue

        if len(line.split(" ")) == 3:
            strategy_name, risk_usdt_str, trades_count = line.split(" ")
            trades_count = int(trades_count)

        elif len(line.split(" ")) == 2:
            strategy_name, risk_usdt_str = line.split(" ")
            trades_count = None

        risk_usdt: float = float(risk_usdt_str.replace("$", "").strip())

        strategies_params.append([strategy_name, risk_usdt, trades_count])  # noqa

    return strategies_params


async def trade_command_handler(message: types.Message, command: CommandObject, logic: Logic) -> types.Message | None:
    """/trade command"""
    try:
        license_key_expired_date: datetime = await logic.get_license_key_expired_date()
        if license_key_expired_date < datetime.utcnow():
            raise Exception("Ваша подписка истекла.")
    except Exception as e:
        return await message.answer(f"🛑 Произошла ошибка: {e}")

    if not command.args:
        return await message.answer(
            f"Чтобы запустить стратегию, нужно ввести команду формата:\n"
            "<blockquote>/trade {НазваниеСтратегии} {Риск}$ {КоличествоПозиций}</blockquote>\n\n"
            f"Количество позиций можно не указывать, в таком случае - страетгия будет "
            f"работать, пока Вы ее не остановите.\n\n"
            f"Например:\n"
            f"<blockquote>/trade btc1min 10$ 10</blockquote>\n\n"
            f"Или:\n"
            f"<blockquote>/trade eth5min 10$</blockquote>"
        )

    try:
        strategies_params: list[list] = _parse_command(command)
    except Exception as e:
        return await message.answer(f"🛑 Произошла ошибка при парсинге сообщения: {e}")

    for strategy_name, risk_usdt, trades_count in strategies_params:
        try:
            await logic.add_user_strategy(
                strategy_name=strategy_name,
                risk_usdt=risk_usdt,
                trades_count=trades_count if trades_count else None)
        except Exception as e:
            await message.answer(f"🛑 Ошибка при запуске стратегии: {e}")
        else:
            await message.answer(f"✅ Стратегия {strategy_name} с риском {risk_usdt}$ на "
                                 f"{trades_count if trades_count else '∞'} сделок добавлена.")
